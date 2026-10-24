import React, { useState, useRef, useEffect, useMemo } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import './styles/tokens.css';
import './styles/reset.css';
import { ActionBar } from './components/ActionBar';
import { AppShell } from './components/AppShell';
import { Banner } from './components/Banner';
import { ContactSheet, type GroupInfo, type MatchTypeFilter } from './components/ContactSheet';
import { DuplicateInspector } from './components/DuplicateInspector';
import { EmptyState } from './components/EmptyState';
import { QuarantineView } from './components/QuarantineView';
import { Sidebar, type FolderEntry, type FolderRole } from './components/Sidebar';
import type { MediaTab } from './components/TabBar';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';

// ── Rust command shapes ────────────────────────────────────────────────────────

interface MovedEntry {
  original: string;
  quarantine_path: string;
  journal_id: number;
  bytes: number;
}

interface QuarantineCommandResult {
  moved: MovedEntry[];
  errors: { path: string; message: string }[];
  total_bytes: number;
}

interface ScanProgressEvent {
  scanned: number;
  total: number;
  path: string;
}

interface ScanGroupsEvent {
  groups: GroupInfo[];
  scanned: number;
  total: number;
}

type ScanStatus = 'idle' | 'scanning' | 'done' | 'error';

// ── helpers ───────────────────────────────────────────────────────────────────

function formatBytes(bytes: number): string {
  if (bytes >= 1_000_000_000) return `${(bytes / 1_000_000_000).toFixed(1)} GB`;
  if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toFixed(1)} MB`;
  if (bytes >= 1_000) return `${Math.round(bytes / 1_000)} KB`;
  return `${bytes} B`;
}

// ── component ─────────────────────────────────────────────────────────────────

function App() {
  const [activeTab, setActiveTab] = useState<MediaTab>('photos');
  const [searchQuery, setSearchQuery] = useState('');
  const searchRef = useRef<HTMLInputElement>(null) as React.RefObject<HTMLInputElement>;
  const [thumbnailSize, setThumbnailSize] = useState(160);

  const [folders, setFolders] = useState<FolderEntry[]>([]);
  const [scanStatus, setScanStatus] = useState<ScanStatus>('idle');
  const [scanProgress, setScanProgress] = useState<string>('');
  const [scanScanned, setScanScanned] = useState(0);
  const [scanTotal, setScanTotal] = useState(0);
  const [groups, setGroups] = useState<GroupInfo[]>([]);
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set());
  const [selectedGroup, setSelectedGroup] = useState<GroupInfo | null>(null);
  const [matchTypeFilter, setMatchTypeFilter] = useState<MatchTypeFilter>('all');
  const [lastScanAt, setLastScanAt] = useState<string | null>(null);
  const [lastScanDurationMs, setLastScanDurationMs] = useState<number | null>(null);
  const [activeView, setActiveView] = useState<'duplicates' | 'quarantine'>('duplicates');
  const [quarantineCount, setQuarantineCount] = useState(0);

  // Quarantine undo state — bannerVisible is separate so dismiss doesn't kill undo
  const [quarantining, setQuarantining] = useState(false);
  const [pendingUndo, setPendingUndo] = useState<{
    moved: MovedEntry[];
    preGroups: GroupInfo[];
    preSelected: Set<string>;
    totalBytes: number;
  } | null>(null);
  const [bannerVisible, setBannerVisible] = useState(false);

  // Persist folders whenever they change
  useEffect(() => {
    if (folders.length > 0) {
      invoke('save_folders', { folders }).catch(() => {});
    }
  }, [folders]);

  const handleSetRole = (path: string, role: FolderRole) => {
    setFolders(prev => prev.map(f => f.path === path ? { ...f, role } : f));
  };

  // Load cached results from previous scan on mount
  useEffect(() => {
    const load = async () => {
      const savedFolders = await invoke<FolderEntry[]>('load_folders').catch(() => [] as FolderEntry[]);
      if (savedFolders.length > 0) setFolders(savedFolders);

      // Load quarantine count so the sidebar badge is correct from the start
      invoke<{ id: number }[]>('list_quarantine')
        .then(items => setQuarantineCount(items.length))
        .catch(() => {});

      const result = await invoke<{
        groups: GroupInfo[];
        total_files: number;
        skipped: number;
        scanned_at: string | null;
        scan_duration_ms: number | null;
      } | null>('load_cached').catch(() => null);

      if (result && result.groups.length > 0) {
        setGroups(result.groups);
        setLastScanAt(result.scanned_at);
        setLastScanDurationMs(result.scan_duration_ms);
        setScanStatus('done');
        const skippedNote = result.skipped > 0 ? ` · ${result.skipped} skipped` : '';
        setScanProgress(`${result.total_files.toLocaleString()} files (cached)${skippedNote}`);
        return;
      }

      const pythonDbPath = './dedupe_cache.sqlite3';
      const imported = await invoke<number>('import_python_cache', { pythonDbPath }).catch(() => 0);
      if (imported > 0) {
        const fresh = await invoke<{
          groups: GroupInfo[];
          total_files: number;
          skipped: number;
          scanned_at: string | null;
        } | null>('load_cached').catch(() => null);
        if (fresh && fresh.groups.length > 0) {
          setGroups(fresh.groups);
          setLastScanAt(fresh.scanned_at);
          setScanStatus('done');
          setScanProgress(`${fresh.total_files.toLocaleString()} files (imported from previous scan)`);
        }
      }
    };
    load();
  }, []);

  // ── scan ────────────────────────────────────────────────────────────────────

  const handleScan = async () => {
    if (folders.length === 0 || scanStatus === 'scanning') return;
    const folderPaths = folders.map(f => f.path);
    const originalFolders = folders.filter(f => f.role === 'original').map(f => f.path);
    setScanStatus('scanning');
    setScanProgress('Walking folders…');
    setScanScanned(0);
    setScanTotal(0);
    setGroups([]);
    setSelectedPaths(new Set());
    setSelectedGroup(null);
    setPendingUndo(null);

    const unlistenProgress = await listen<ScanProgressEvent>('scan-progress', ev => {
      const { total } = ev.payload;
      if (total > 0) {
        setScanTotal(total);
        setScanProgress(`Found ${total.toLocaleString()} files, hashing…`);
      }
    });

    const unlistenGroups = await listen<ScanGroupsEvent>('scan-groups', ev => {
      const { groups, scanned, total } = ev.payload;
      setGroups(groups);
      setScanScanned(scanned);
      setScanTotal(total);
      const pct = total > 0 ? Math.round((scanned / total) * 100) : 0;
      setScanProgress(`${scanned.toLocaleString()} / ${total.toLocaleString()} (${pct}%)`);
    });

    try {
      const result = await invoke<{ total_files: number; skipped: number; duration_ms: number; cache_hits: number }>(
        'scan_folders',
        { paths: folderPaths, originalFolders }
      );
      const durationSec = (result.duration_ms / 1000).toFixed(1);
      const cacheNote = result.cache_hits > 0 ? ` · ${result.cache_hits.toLocaleString()} from cache` : '';
      const skippedNote = result.skipped > 0 ? ` · ${result.skipped} skipped` : '';
      setLastScanDurationMs(result.duration_ms);
      setLastScanAt(new Date().toLocaleString());
      setScanProgress(`${result.total_files.toLocaleString()} files · ${durationSec}s${cacheNote}${skippedNote}`);
      setScanStatus('done');

      // Pre-generate thumbnails in background so scroll is instant
      setGroups(prev => {
        const allPaths = prev.flatMap(g => g.files.map(f => f.path));
        if (allPaths.length > 0) {
          invoke('prefetch_thumbnails', { paths: allPaths }).catch(() => {});
        }
        return prev;
      });
    } catch (e) {
      setScanProgress(String(e));
      setScanStatus('error');
    } finally {
      unlistenProgress();
      unlistenGroups();
    }
  };

  // ── selection ────────────────────────────────────────────────────────────────

  const handleToggleSelect = (path: string) => {
    setSelectedPaths(prev => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const handleSelectAll = (add: string[], remove: string[]) => {
    setSelectedPaths(prev => {
      const next = new Set(prev);
      for (const p of add) next.add(p);
      for (const p of remove) next.delete(p);
      return next;
    });
  };

  // ── quarantine ───────────────────────────────────────────────────────────────

  const handleQuarantine = async () => {
    if (selectedPaths.size === 0 || quarantining) return;
    setQuarantining(true);

    const pathsToMove = [...selectedPaths];
    const preGroups = groups;
    const preSelected = new Set(selectedPaths);

    try {
      const result = await invoke<QuarantineCommandResult>('quarantine_files', {
        paths: pathsToMove,
      });

      if (result.moved.length === 0) {
        const errMsg = result.errors[0]?.message ?? 'Unknown error';
        setScanProgress(`Quarantine failed: ${errMsg}`);
        return;
      }

      // Remove moved files from groups; drop groups that lost all copies
      const movedSet = new Set(result.moved.map(m => m.original));
      const updatedGroups = preGroups
        .map(g => ({
          ...g,
          files: g.files.filter(f => f.is_keeper || !movedSet.has(f.path)),
        }))
        .filter(g => {
          const copies = g.files.filter(f => !f.is_keeper);
          return copies.length > 0;
        });

      setGroups(updatedGroups);

      // Deselect moved paths
      setSelectedPaths(prev => {
        const next = new Set(prev);
        for (const m of result.moved) next.delete(m.original);
        return next;
      });

      // Update selectedGroup if it lost all its copies
      setSelectedGroup(prev => {
        if (!prev) return null;
        const updated = updatedGroups.find(g => g.group_id === prev.group_id);
        return updated ?? null;
      });

      // Store undo payload and show banner
      setPendingUndo({
        moved: result.moved,
        preGroups,
        preSelected,
        totalBytes: result.total_bytes,
      });
      setBannerVisible(true);
      setQuarantineCount(c => c + result.moved.length);

    } catch (e) {
      setScanProgress(`Quarantine error: ${String(e)}`);
    } finally {
      setQuarantining(false);
    }
  };

  // ── undo ────────────────────────────────────────────────────────────────────

  const handleUndo = async () => {
    if (!pendingUndo) return;
    const { moved, preGroups, preSelected } = pendingUndo;

    try {
      await invoke('restore_files', {
        entries: moved.map(m => ({
          original: m.original,
          quarantine_path: m.quarantine_path,
          journal_id: m.journal_id,
        })),
      });

      // Restore pre-quarantine state
      setGroups(preGroups);
      setSelectedPaths(preSelected);
      setQuarantineCount(c => Math.max(0, c - moved.length));
      setPendingUndo(null);
      setBannerVisible(false);
    } catch (e) {
      console.error('restore failed:', e);
    }
  };

  // ── derived state ────────────────────────────────────────────────────────────

  const selectedBytes = useMemo(() => {
    let total = 0;
    for (const g of groups) {
      for (const f of g.files) {
        if (!f.is_keeper && selectedPaths.has(f.path)) total += f.size;
      }
    }
    return total;
  }, [groups, selectedPaths]);

  const filteredGroups = groups.filter(g => {
    if (activeTab === 'photos') {
      return g.files.some(f => /\.(jpg|jpeg|png|heic|heif|webp|tiff|tif|bmp)$/i.test(f.path));
    }
    if (activeTab === 'videos') {
      return g.files.some(f => /\.(mp4|mov|avi|mkv|m4v)$/i.test(f.path));
    }
    return true;
  });

  const visibleGroups = searchQuery
    ? filteredGroups.filter(g =>
        g.files.some(f => f.path.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    : filteredGroups;

  // Savings shown in the action bar: total size of non-keeper files in the
  // currently visible match-type-filtered set (mirrors what ContactSheet shows).
  const savingsBytes = useMemo(() => {
    const byType = matchTypeFilter === 'all'
      ? visibleGroups
      : visibleGroups.filter(g => g.match_type === matchTypeFilter);
    return byType.reduce((sum, g) =>
      sum + g.files.filter(f => !f.is_keeper).reduce((s, f) => s + f.size, 0), 0
    );
  }, [visibleGroups, matchTypeFilter]);

  // ── keyboard shortcuts ───────────────────────────────────────────────────────

  useKeyboardShortcuts({
    onSearch: () => searchRef.current?.focus(),
    onCancel: () => {
      if (document.activeElement === searchRef.current) {
        setSearchQuery('');
        searchRef.current?.blur();
      }
    },
    onUndo: pendingUndo ? handleUndo : undefined,
    onSelectAll: () => {
      handleSelectAll(
        groups.flatMap(g => g.files).filter(f => !f.is_keeper).map(f => f.path),
        []
      );
    },
    onPreview: () => {},
  });

  // ── quarantine view ──────────────────────────────────────────────────────────

  const quarantineSheet = (
    <QuarantineView
      thumbnailSize={thumbnailSize}
      onRestored={restoredPaths => {
        setQuarantineCount(c => Math.max(0, c - restoredPaths.length));
      }}
    />
  );

  // ── contact sheet ────────────────────────────────────────────────────────────

  const contactSheet = (() => {
    if (scanStatus === 'idle' && groups.length === 0) {
      return (
        <EmptyState
          title="Add folders to get started"
          body="Add one or more folders in the sidebar, then click Scan to find duplicates."
        />
      );
    }
    if (scanStatus === 'scanning' && groups.length === 0) {
      return (
        <EmptyState
          title="Scanning…"
          body={scanProgress || 'Looking for duplicates…'}
        />
      );
    }
    if (scanStatus === 'error') {
      return (
        <EmptyState
          title="Scan failed"
          body={scanProgress}
          action={{ label: 'Try again', onClick: handleScan }}
        />
      );
    }
    if (scanStatus === 'done' && visibleGroups.length === 0) {
      return (
        <EmptyState
          title="No duplicates found"
          body={
            searchQuery
              ? `No results for "${searchQuery}"`
              : `Scanned ${folders.map(f => f.path).join(', ')}. All files are unique.`
          }
          action={searchQuery ? { label: 'Clear search', onClick: () => setSearchQuery('') } : undefined}
        />
      );
    }
    return (
      <>
        {bannerVisible && pendingUndo && (
          <Banner
            message={`Moved ${pendingUndo.moved.length} file${pendingUndo.moved.length !== 1 ? 's' : ''} to Quarantine (${formatBytes(pendingUndo.totalBytes)}).`}
            onUndo={handleUndo}
            onDismiss={() => setBannerVisible(false)}
          />
        )}
        <ContactSheet
          groups={visibleGroups}
          thumbnailSize={thumbnailSize}
          selectedPaths={selectedPaths}
          onSelectAll={handleSelectAll}
          onSelectGroup={setSelectedGroup}
          selectedGroupId={selectedGroup?.group_id ?? null}
          matchTypeFilter={matchTypeFilter}
          onMatchTypeFilterChange={setMatchTypeFilter}
        />
      </>
    );
  })();

  // ── render ───────────────────────────────────────────────────────────────────

  return (
    <AppShell
      activeTab={activeTab}
      onTabChange={setActiveTab}
      searchQuery={searchQuery}
      onSearchChange={setSearchQuery}
      searchRef={searchRef}
      sidebar={
        <Sidebar
          folders={folders}
          scanState={{ status: scanStatus, progress: scanProgress, scanned: scanScanned, total: scanTotal, lastScanAt, lastScanDurationMs }}
          onAddFolder={handleAddFolder}
          onRemoveFolder={handleRemoveFolder}
          onSetRole={handleSetRole}
          onScan={handleScan}
          resultCount={groups.length}
          quarantineCount={quarantineCount}
          activeView={activeView}
          onViewChange={v => { setActiveView(v); setSelectedGroup(null); }}
        />
      }
      contactSheet={activeView === 'quarantine' ? quarantineSheet : contactSheet}
      inspector={
        activeView === 'quarantine' ? null : (
          <DuplicateInspector
            group={selectedGroup}
            selectedPaths={selectedPaths}
            onToggle={handleToggleSelect}
          />
        )
      }
      inspectorOpen={activeView !== 'quarantine' && selectedGroup !== null}
      footer={
        <ActionBar
          selectedCount={selectedPaths.size}
          selectedBytes={selectedBytes}
          savingsBytes={savingsBytes}
          matchTypeFilter={matchTypeFilter}
          thumbnailSize={thumbnailSize}
          onThumbnailSizeChange={setThumbnailSize}
          onQuarantine={handleQuarantine}
          quarantining={quarantining}
        />
      }
    />
  );

  function handleAddFolder() {
    invoke<string | null>('pick_folder').then(path => {
      if (path && !folders.some(f => f.path === path)) {
        setFolders(prev => [...prev, { path, role: 'any' }]);
      }
    }).catch(console.error);
  }

  function handleRemoveFolder(path: string) {
    setFolders(prev => prev.filter(f => f.path !== path));
  }
}

export default App;
