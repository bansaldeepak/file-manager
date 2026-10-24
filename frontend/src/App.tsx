import { useState, useRef } from 'react';
import './styles/tokens.css';
import './styles/reset.css';
import { AppShell } from './components/AppShell';
import { Banner } from './components/Banner';
import { EmptyState } from './components/EmptyState';
import type { MediaTab } from './components/TabBar';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';
import { ZoomSlider } from './components/ZoomSlider';

interface Folders {
  original?: string;
  copies?: string;
}

interface QuarantineResult {
  fileCount: number;
  totalBytes: number;
}

function formatBytes(bytes: number): string {
  if (bytes >= 1_000_000_000) return `${(bytes / 1_000_000_000).toFixed(1)} GB`;
  if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toFixed(1)} MB`;
  if (bytes >= 1_000) return `${(bytes / 1_000).toFixed(0)} KB`;
  return `${bytes} B`;
}

function App() {
  const [activeTab, setActiveTab] = useState<MediaTab>('photos');
  const [searchQuery, setSearchQuery] = useState('');
  const searchRef = useRef<HTMLInputElement>(null);
  const [thumbnailSize, setThumbnailSize] = useState(160);
  const [folders, setFolders] = useState<Folders>({});
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
    onPreview: () => console.log('preview — T-013 spike will wire this'),
  });

  const handleDrop = (paths: string[]) => {
    const path = paths[0];
    if (!folders.original) {
      setFolders(f => ({ ...f, original: path }));
    } else {
      setFolders(f => ({ ...f, copies: path }));
    }
  };

  const innerSheet = !folders.original ? (
    <EmptyState
      title="Drop a folder to get started"
      body="Drop your originals folder here, then your copies folder, to find duplicates."
      dropZone={{ onDrop: handleDrop, hint: 'or choose a folder in the sidebar' }}
    />
  ) : !folders.copies ? (
    <EmptyState
      title="Now drop your copies folder"
      body={`Originals: ${folders.original}`}
      dropZone={{ onDrop: handleDrop }}
    />
  ) : (
    <EmptyState
      title="No duplicates found"
      body={`Scanned ${folders.original} and ${folders.copies}. All files are unique.`}
      action={{ label: 'Choose different folders', onClick: () => setFolders({}) }}
    />
  );

  const contactSheet = (
    <>
      {lastQuarantine && (
        <Banner
          message={`Moved ${lastQuarantine.fileCount} file${lastQuarantine.fileCount !== 1 ? 's' : ''} (${formatBytes(lastQuarantine.totalBytes)}).`}
          onUndo={handleUndo}
          onDismiss={() => setLastQuarantine(null)}
        />
      )}
      {innerSheet}
    </>
  );

  return (
    <AppShell
      activeTab={activeTab}
      onTabChange={setActiveTab}
      searchQuery={searchQuery}
      onSearchChange={setSearchQuery}
      searchRef={searchRef}
      sidebar={
        <p style={{ fontFamily: 'var(--font-body)', fontSize: '13px', color: 'var(--color-text-muted)' }}>
          Folder nav — coming in T-015+
        </p>
      }
      contactSheet={contactSheet}
      inspector={
        <p style={{ fontFamily: 'var(--font-body)', fontSize: '13px', color: 'var(--color-text-muted)' }}>
          Inspector — coming in Stage 3
        </p>
      }
      footer={<ZoomSlider value={thumbnailSize} onChange={setThumbnailSize} />}
    />
  );
}

export default App;
