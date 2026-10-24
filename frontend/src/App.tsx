import { useState, useRef } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import './styles/tokens.css';
import './styles/reset.css';
import { AppShell } from './components/AppShell';
import { Banner } from './components/Banner';
import { ContactSheet, type GroupInfo } from './components/ContactSheet';
import { EmptyState } from './components/EmptyState';
import { Sidebar } from './components/Sidebar';
import type { MediaTab } from './components/TabBar';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';
import { ZoomSlider } from './components/ZoomSlider';

interface QuarantineResult {
  fileCount: number;
  totalBytes: number;
}

interface ScanProgressEvent {
  scanned: number;
  total: number;
  path: string;
}

type ScanStatus = 'idle' | 'scanning' | 'done' | 'error';

interface ScanGroupsEvent {
  groups: GroupInfo[];
  scanned: number;
  total: number;
}

function formatBytes(bytes: number): string {
  if (bytes >= 1_000_000_000) return `${(bytes / 1_000_000_000).toFixed(1)} GB`;
  if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toFixed(1)} MB`;
  if (bytes >= 1_000) return `${Math.round(bytes / 1_000)} KB`;
  return `${bytes} B`;
}

function App() {
  const [activeTab, setActiveTab] = useState<MediaTab>('photos');
  const [searchQuery, setSearchQuery] = useState('');
  const searchRef = useRef<HTMLInputElement>(null);
  const [thumbnailSize, setThumbnailSize] = useState(160);

  const [folders, setFolders] = useState<string[]>([]);
  const [scanStatus, setScanStatus] = useState<ScanStatus>('idle');
  const [scanProgress, setScanProgress] = useState<string>('');
  const [scanScanned, setScanScanned] = useState(0);
  const [scanTotal, setScanTotal] = useState(0);
  const [groups, setGroups] = useState<GroupInfo[]>([]);
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set());
  const [lastQuarantine, setLastQuarantine] = useState<QuarantineResult | null>(null);

  const handleUndo = () => {
    console.log('undo quarantine — restore command wired in Stage 4');
    setLastQuarantine(null);
  };

  useKeyboardShortcuts({
    onSearch: () => searchRef.current?.focus(),
    onCancel: () => {
      if (document.activeElement === searchRef.current) {
        setSearchQuery('');
        searchRef.current?.blur();
      }
    },
    onUndo: lastQuarantine ? handleUndo : undefined,
    onSelectAll: () => {
      const copies = groups
        .flatMap(g => g.files)
        .filter(f => !f.is_keeper)
        .map(f => f.path);
      setSelectedPaths(new Set(copies));
    },
    onPreview: () => console.log('preview — T-013 qlmanage wired in next pass'),
  });

  const handleAddFolder = async () => {
    try {
      const path = await invoke<string | null>('pick_folder');
      if (path && !folders.includes(path)) {
        setFolders(f => [...f, path]);
      }
    } catch (e) {
      console.error('pick_folder failed:', e);
    }
  };

  const handleRemoveFolder = (path: string) => {
    setFolders(f => f.filter(p => p !== path));
  };

  const handleScan = async () => {
    if (folders.length === 0 || scanStatus === 'scanning') return;
    setScanStatus('scanning');
    setScanProgress('Walking folders…');
    setScanScanned(0);
    setScanTotal(0);
    setGroups([]);
    setSelectedPaths(new Set());

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
      const result = await invoke<{ total_files: number; skipped: number }>(
        'scan_folders',
        { paths: folders }
      );
      const skippedNote = result.skipped > 0 ? ` · ${result.skipped} skipped` : '';
      setScanProgress(`${result.total_files.toLocaleString()} files scanned${skippedNote}`);
      setScanStatus('done');
    } catch (e) {
      setScanProgress(String(e));
      setScanStatus('error');
    } finally {
      unlistenProgress();
      unlistenGroups();
    }
  };

  const handleToggleSelect = (path: string) => {
    setSelectedPaths(prev => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  // Filter groups by active tab
  const filteredGroups = groups.filter(g => {
    if (activeTab === 'photos') {
      return g.files.some(f => /\.(jpg|jpeg|png|heic|heif|webp|tiff|tif|bmp)$/i.test(f.path));
    }
    if (activeTab === 'videos') {
      return g.files.some(f => /\.(mp4|mov|avi|mkv|m4v)$/i.test(f.path));
    }
    return true;
  });

  // Filter groups by search query
  const visibleGroups = searchQuery
    ? filteredGroups.filter(g =>
        g.files.some(f => f.path.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    : filteredGroups;

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
              : `Scanned ${folders.join(', ')}. All files are unique.`
          }
          action={searchQuery ? { label: 'Clear search', onClick: () => setSearchQuery('') } : undefined}
        />
      );
    }
    return (
      <>
        {lastQuarantine && (
          <Banner
            message={`Moved ${lastQuarantine.fileCount} file${lastQuarantine.fileCount !== 1 ? 's' : ''} (${formatBytes(lastQuarantine.totalBytes)}).`}
            onUndo={handleUndo}
            onDismiss={() => setLastQuarantine(null)}
          />
        )}
        <ContactSheet
          groups={visibleGroups}
          thumbnailSize={thumbnailSize}
          selectedPaths={selectedPaths}
          onToggleSelect={handleToggleSelect}
        />
      </>
    );
  })();

  const selectedCount = selectedPaths.size;

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
          scanState={{ status: scanStatus, progress: scanProgress, scanned: scanScanned, total: scanTotal }}
          onAddFolder={handleAddFolder}
          onRemoveFolder={handleRemoveFolder}
          onScan={handleScan}
          resultCount={groups.length}
        />
      }
      contactSheet={contactSheet}
      inspector={
        <div style={{ padding: 'var(--spacing-md)', fontFamily: 'var(--font-body)', fontSize: '13px', color: 'var(--color-text-muted)' }}>
          {selectedCount > 0 ? (
            <p>{selectedCount} file{selectedCount !== 1 ? 's' : ''} selected for quarantine.<br /><br />Quarantine action coming in Stage 4.</p>
          ) : (
            <p>Select copies in the contact sheet to quarantine them.</p>
          )}
        </div>
      }
      footer={<ZoomSlider value={thumbnailSize} onChange={setThumbnailSize} />}
    />
  );
}

export default App;
