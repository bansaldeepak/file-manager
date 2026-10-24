import { useState, useRef } from 'react';
import './styles/tokens.css';
import './styles/reset.css';
import { AppShell } from './components/AppShell';
import type { MediaTab } from './components/TabBar';

function App() {
  const [activeTab, setActiveTab] = useState<MediaTab>('photos');
  const [searchQuery, setSearchQuery] = useState('');
  const searchRef = useRef<HTMLInputElement>(null);

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
      contactSheet={
        <p style={{ fontFamily: 'var(--font-body)', fontSize: '13px', color: 'var(--color-text-muted)' }}>
          Contact sheet — coming in Stage 3
        </p>
      }
      inspector={
        <p style={{ fontFamily: 'var(--font-body)', fontSize: '13px', color: 'var(--color-text-muted)' }}>
          Inspector — coming in Stage 3
        </p>
      }
    />
  );
}

export default App;
