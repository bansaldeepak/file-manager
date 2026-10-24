import React from 'react';
import './AppShell.css';

interface AppShellProps {
  toolbar?: React.ReactNode;
  sidebar: React.ReactNode;
  contactSheet: React.ReactNode;
  inspector: React.ReactNode;
}

export function AppShell({ toolbar, sidebar, contactSheet, inspector }: AppShellProps) {
  return (
    <div className="app-shell">
      <div className="toolbar">{toolbar}</div>
      <div className="panes">
        <nav className="sidebar">{sidebar}</nav>
        <main className="contact-sheet">{contactSheet}</main>
        <aside className="inspector">{inspector}</aside>
      </div>
    </div>
  );
}
