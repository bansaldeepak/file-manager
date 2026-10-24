import { useState, useRef } from 'react';
import './styles/tokens.css';
import './styles/reset.css';
import { AppShell } from './components/AppShell';
import { EmptyState } from './components/EmptyState';
import type { MediaTab } from './components/TabBar';

interface Folders {
  original?: string;
  copies?: string;
}

function App() {
  const [activeTab, setActiveTab] = useState<MediaTab>('photos');
  const [searchQuery, setSearchQuery] = useState('');
  const searchRef = useRef<HTMLInputElement>(null);
  const [folders, setFolders] = useState<Folders>({});

  const handleDrop = (paths: string[]) => {
    const path = paths[0];
    if (!folders.original) {
      setFolders(f => ({ ...f, original: path }));
    } else {
      setFolders(f => ({ ...f, copies: path }));
    }
  };

  const contactSheet = !folders.original ? (
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
    />
  );
}

export default App;
