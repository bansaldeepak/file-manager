import './Sidebar.css';

export type FolderRole = 'any' | 'original' | 'check';

export interface FolderEntry {
  path: string;
  role: FolderRole;
}

interface ScanState {
  status: 'idle' | 'scanning' | 'done' | 'error';
  progress?: string;
  scanned?: number;
  total?: number;
  lastScanAt?: string | null;
  lastScanDurationMs?: number | null;
}

interface SidebarProps {
  folders: FolderEntry[];
  scanState: ScanState;
  onAddFolder: () => void;
  onRemoveFolder: (path: string) => void;
  onSetRole: (path: string, role: FolderRole) => void;
  onScan: () => void;
  resultCount?: number;
  quarantineCount?: number;
  activeView: 'duplicates' | 'quarantine';
  onViewChange: (view: 'duplicates' | 'quarantine') => void;
}

function basename(path: string): string {
  return path.split('/').filter(Boolean).pop() ?? path;
}

export function Sidebar({
  folders,
  scanState,
  onAddFolder,
  onRemoveFolder,
  onSetRole,
  onScan,
  resultCount,
  quarantineCount,
  activeView,
  onViewChange,
}: SidebarProps) {
  const canScan = folders.length > 0 && scanState.status !== 'scanning';
  const hasRoles = folders.some(f => f.role !== 'any');

  return (
    <div className="sidebar-content">
      {/* ── view nav ── */}
      <nav className="sidebar-nav">
        <button
          className={`sidebar-nav-item${activeView === 'duplicates' ? ' sidebar-nav-item--active' : ''}`}
          onClick={() => onViewChange('duplicates')}
        >
          <span className="sidebar-nav-icon">⊕</span>
          <span>Duplicates</span>
          {resultCount != null && resultCount > 0 && (
            <span className="sidebar-nav-badge">{resultCount}</span>
          )}
        </button>
        <button
          className={`sidebar-nav-item${activeView === 'quarantine' ? ' sidebar-nav-item--active' : ''}${!quarantineCount ? ' sidebar-nav-item--disabled' : ''}`}
          onClick={() => quarantineCount && onViewChange('quarantine')}
          disabled={!quarantineCount}
          title={quarantineCount ? `${quarantineCount} quarantined file${quarantineCount !== 1 ? 's' : ''}` : 'No files quarantined'}
        >
          <span className="sidebar-nav-icon">🗑</span>
          <span>Quarantine</span>
          {!!quarantineCount && (
            <span className="sidebar-nav-badge sidebar-nav-badge--muted">{quarantineCount}</span>
          )}
        </button>
      </nav>

      <section className="sidebar-section">
        <h3 className="sidebar-heading">Folders</h3>
        {folders.length === 0 ? (
          <p className="sidebar-empty">No folders added yet.</p>
        ) : (
          <>
            <div className="folder-roles-legend">
              <span className="folder-roles-legend-item folder-roles-legend-item--orig">O = Original</span>
              <span className="folder-roles-legend-item folder-roles-legend-item--check">C = Check</span>
            </div>
            <ul className="folder-list">
              {folders.map(entry => (
                <li key={entry.path} className="folder-item" title={entry.path}>
                  <span className="folder-name">{basename(entry.path)}</span>
                  <div className="folder-role-group">
                    <button
                      className={`folder-role-btn ${entry.role === 'original' ? 'folder-role-btn--orig-active' : ''}`}
                      onClick={() => onSetRole(entry.path, entry.role === 'original' ? 'any' : 'original')}
                      title="Mark as Original — keepers preferred from this folder"
                    >
                      O
                    </button>
                    <button
                      className={`folder-role-btn ${entry.role === 'check' ? 'folder-role-btn--check-active' : ''}`}
                      onClick={() => onSetRole(entry.path, entry.role === 'check' ? 'any' : 'check')}
                      title="Mark as Check — duplicates here are quarantine candidates"
                    >
                      C
                    </button>
                  </div>
                  <button
                    className="folder-remove"
                    onClick={() => onRemoveFolder(entry.path)}
                    aria-label={`Remove ${basename(entry.path)}`}
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>
            {hasRoles && (
              <p className="sidebar-role-hint">
                Scan applies roles to keeper selection.
              </p>
            )}
          </>
        )}
        <button className="sidebar-btn sidebar-btn--secondary" onClick={onAddFolder}>
          + Add folder
        </button>
      </section>

      <section className="sidebar-section">
        <button
          className="sidebar-btn sidebar-btn--primary"
          onClick={onScan}
          disabled={!canScan}
        >
          {scanState.status === 'scanning' ? 'Scanning…' : 'Scan'}
        </button>
        {scanState.status === 'scanning' && scanState.total && scanState.total > 0 && (
          <progress
            value={scanState.scanned ?? 0}
            max={scanState.total}
            style={{ width: '100%', accentColor: 'var(--color-primary)' }}
          />
        )}
        {scanState.progress && (
          <p className="sidebar-progress">{scanState.progress}</p>
        )}
        {scanState.status === 'done' && resultCount !== undefined && (
          <p className="sidebar-result">
            {resultCount === 0
              ? 'No duplicates found.'
              : `${resultCount} duplicate group${resultCount !== 1 ? 's' : ''} found.`}
          </p>
        )}
        {scanState.status === 'done' && scanState.lastScanAt && (
          <p className="sidebar-result" style={{ opacity: 0.6, fontSize: '11px' }}>
            {scanState.lastScanAt}
            {scanState.lastScanDurationMs != null && (
              <> · {(scanState.lastScanDurationMs / 1000).toFixed(1)}s</>
            )}
          </p>
        )}
        {scanState.status === 'error' && scanState.progress && (
          <p className="sidebar-error">{scanState.progress}</p>
        )}
      </section>
    </div>
  );
}
