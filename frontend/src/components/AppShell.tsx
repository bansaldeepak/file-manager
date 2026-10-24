import React from 'react';
import { SearchBar } from './SearchBar';
import './AppShell.css';

interface AppShellProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  searchRef?: React.RefObject<HTMLInputElement>;
  sidebar: React.ReactNode;
  contactSheet: React.ReactNode;
  inspector: React.ReactNode;
}

export function AppShell({
  searchQuery,
  onSearchChange,
  searchRef,
  sidebar,
  contactSheet,
  inspector,
}: AppShellProps) {
  return (
    <div className="app-shell">
      <div className="toolbar">
        <div className="toolbar-right">
          <SearchBar value={searchQuery} onChange={onSearchChange} focusRef={searchRef} />
        </div>
      </div>
      <div className="panes">
        <nav className="sidebar">{sidebar}</nav>
        <main className="contact-sheet">{contactSheet}</main>
        <aside className="inspector">{inspector}</aside>
      </div>
    </div>
  );
}
