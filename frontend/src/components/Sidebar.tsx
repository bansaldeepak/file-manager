import './Sidebar.css';

interface ScanState {
  status: 'idle' | 'scanning' | 'done' | 'error';
  progress?: string;
}

interface SidebarProps {
  folders: string[];
  scanState: ScanState;
  onAddFolder: () => void;
  onRemoveFolder: (path: string) => void;
  onScan: () => void;
  resultCount?: number;
}

function basename(path: string): string {
  return path.split('/').filter(Boolean).pop() ?? path;
}

export function Sidebar({
  folders,
  scanState,
  onAddFolder,
  onRemoveFolder,
  onScan,
  resultCount,
}: SidebarProps) {
  const canScan = folders.length > 0 && scanState.status !== 'scanning';

  return (
    <div className="sidebar-content">
      <section className="sidebar-section">
        <h3 className="sidebar-heading">Folders</h3>
        {folders.length === 0 ? (
          <p className="sidebar-empty">No folders added yet.</p>
        ) : (
          <ul className="folder-list">
            {folders.map(f => (
              <li key={f} className="folder-item" title={f}>
                <span className="folder-name">{basename(f)}</span>
                <button
                  className="folder-remove"
                  onClick={() => onRemoveFolder(f)}
                  aria-label={`Remove ${basename(f)}`}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
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
        {scanState.status === 'error' && scanState.progress && (
          <p className="sidebar-error">{scanState.progress}</p>
        )}
      </section>
    </div>
  );
}
