import React from 'react';
import { SearchBar } from './SearchBar';
import { TabBar, type MediaTab } from './TabBar';
import './AppShell.css';

interface AppShellProps {
  activeTab: MediaTab;
  onTabChange: (tab: MediaTab) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  searchRef?: React.RefObject<HTMLInputElement>;
  sidebar: React.ReactNode;
  contactSheet: React.ReactNode;
  inspector: React.ReactNode;
  footer?: React.ReactNode;
}

export function AppShell({
  activeTab,
  onTabChange,
  searchQuery,
  onSearchChange,
  searchRef,
  sidebar,
  contactSheet,
  inspector,
  footer,
}: AppShellProps) {
  return (
    <div className="app-shell">
      <div className="toolbar">
        <TabBar value={activeTab} onChange={onTabChange} />
        <div className="toolbar-spacer" />
        <div className="toolbar-right">
          <SearchBar value={searchQuery} onChange={onSearchChange} focusRef={searchRef} />
        </div>
      </div>
      <div className="panes">
        <nav className="sidebar">{sidebar}</nav>
        <main className="contact-sheet">{contactSheet}</main>
        <aside className="inspector">{inspector}</aside>
      </div>
      {footer && <div className="app-footer">{footer}</div>}
    </div>
  );
}
