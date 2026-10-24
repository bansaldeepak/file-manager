import { useState, useEffect, Fragment } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { useThumbnail } from '../hooks/useThumbnail';
import './QuarantineView.css';

export interface QuarantineItem {
  id: number;
  original_path: string;
  quarantine_path: string;
  quarantined_at: string;
  file_size: number;
}

interface Props {
  thumbnailSize: number;
  onRestored: (originalPaths: string[]) => void;
}

function formatBytes(bytes: number): string {
  if (bytes >= 1_000_000_000) return `${(bytes / 1_000_000_000).toFixed(1)} GB`;
  if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toFixed(1)} MB`;
  if (bytes >= 1_000) return `${Math.round(bytes / 1_000)} KB`;
  return `${bytes} B`;
}

function basename(path: string): string {
  return path.split('/').filter(Boolean).pop() ?? path;
}

function PathCrumbs({ path }: { path: string }) {
  const parts = path.split('/').filter(Boolean);
  const show = parts.length > 4 ? ['…', ...parts.slice(-3)] : parts;
  return (
    <span className="qv-crumbs" title={path}>
      {show.map((seg, i) => (
        <Fragment key={i}>
          {i > 0 && <span className="qv-crumbs-sep">›</span>}
          <span className={i === show.length - 1 ? 'qv-crumbs-leaf' : 'qv-crumbs-seg'}>
            {seg}
          </span>
        </Fragment>
      ))}
    </span>
  );
}

function QvCard({
  item, thumbnailSize, isSelected, restoring, onToggle, onRestore,
}: {
  item: QuarantineItem;
  thumbnailSize: number;
  isSelected: boolean;
  restoring: boolean;
  onToggle: (id: number) => void;
  onRestore: (items: QuarantineItem[]) => void;
}) {
  const src = useThumbnail(item.quarantine_path, thumbnailSize * 2);
  return (
    <div
      className={`qv-card${isSelected ? ' qv-card--selected' : ''}`}
      style={{ width: thumbnailSize }}
      onClick={() => onToggle(item.id)}
      role="checkbox"
      aria-checked={isSelected}
      tabIndex={0}
      onKeyDown={e => e.key === ' ' && onToggle(item.id)}
    >
      <div className="qv-card-thumb-wrap" style={{ width: thumbnailSize, height: thumbnailSize }}>
        {src ? (
          <img className="qv-card-thumb" src={src} alt={basename(item.quarantine_path)} draggable={false} />
        ) : (
          <div className="qv-card-thumb qv-card-thumb--loading" />
        )}
        <div className={`qv-card-check${isSelected ? ' qv-card-check--on' : ''}`}>
          {isSelected && '✓'}
        </div>
        <button
          className="qv-card-restore-overlay"
          onClick={e => { e.stopPropagation(); onRestore([item]); }}
          disabled={restoring}
          title="Restore to original location"
        >
          Restore
        </button>
      </div>
      <div className="qv-card-meta">
        <span className="qv-card-name" title={item.original_path}>{basename(item.original_path)}</span>
        <PathCrumbs path={item.original_path.split('/').slice(0, -1).join('/')} />
        <span className="qv-card-size">{formatBytes(item.file_size)}</span>
      </div>
    </div>
  );
}

export function QuarantineView({ thumbnailSize, onRestored }: Props) {
  const [items, setItems] = useState<QuarantineItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [restoring, setRestoring] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const data = await invoke<QuarantineItem[]>('list_quarantine');
      setItems(data);
    } catch (e) {
      console.error('list_quarantine failed:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const toggleItem = (id: number) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selected.size === items.length) setSelected(new Set());
    else setSelected(new Set(items.map(i => i.id)));
  };

  const handleRestore = async (toRestore: QuarantineItem[]) => {
    if (restoring || toRestore.length === 0) return;
    setRestoring(true);
    try {
      await invoke('restore_files', {
        entries: toRestore.map(item => ({
          original: item.original_path,
          quarantine_path: item.quarantine_path,
          journal_id: item.id,
        })),
      });
      const restoredOriginals = toRestore.map(i => i.original_path);
      setItems(prev => prev.filter(i => !toRestore.some(r => r.id === i.id)));
      setSelected(new Set());
      onRestored(restoredOriginals);
    } catch (e) {
      console.error('restore_files failed:', e);
    } finally {
      setRestoring(false);
    }
  };

  const handleDelete = async () => {
    if (deleting || selectedItems.length === 0) return;
    setConfirmDelete(false);
    setDeleting(true);
    try {
      await invoke('delete_permanently', {
        entries: selectedItems.map(item => ({
          quarantine_path: item.quarantine_path,
          journal_id: item.id,
        })),
      });
      setItems(prev => prev.filter(i => !selected.has(i.id)));
      setSelected(new Set());
    } catch (e) {
      console.error('delete_permanently failed:', e);
    } finally {
      setDeleting(false);
    }
  };

  const selectedItems = items.filter(i => selected.has(i.id));
  const selectedBytes = selectedItems.reduce((s, i) => s + i.file_size, 0);
  const totalBytes = items.reduce((s, i) => s + i.file_size, 0);
  const allSelected = items.length > 0 && selected.size === items.length;

  if (loading) {
    return <div className="qv-empty"><p>Loading…</p></div>;
  }

  if (items.length === 0) {
    return (
      <div className="qv-empty">
        <span className="qv-empty-icon">🗑</span>
        <p>Quarantine is empty.</p>
        <p className="qv-empty-sub">Files you quarantine will appear here. You can restore them any time before permanently deleting.</p>
      </div>
    );
  }

  return (
    <div className="qv-root">
      {/* ── header ── */}
      <div className="qv-header">
        <div className="qv-header-info">
          <span className="qv-title">{items.length} quarantined file{items.length !== 1 ? 's' : ''}</span>
          <span className="qv-subtitle">{formatBytes(totalBytes)} · Restore to undo</span>
        </div>
        <div className="qv-header-actions">
          <button className="qv-select-all-btn" onClick={selectAll}>
            {allSelected ? 'Deselect all' : 'Select all'}
          </button>
          {selected.size > 0 && (
            <button
              className="qv-restore-btn"
              onClick={() => handleRestore(selectedItems)}
              disabled={restoring || deleting}
            >
              {restoring ? 'Restoring…' : `Restore ${selected.size} (${formatBytes(selectedBytes)})`}
            </button>
          )}
          {selected.size > 0 && (
            <button
              className="qv-delete-btn"
              onClick={() => setConfirmDelete(true)}
              disabled={restoring || deleting}
            >
              {deleting ? 'Deleting…' : `Delete ${selected.size} permanently`}
            </button>
          )}
        </div>
      </div>

      {/* ── grid ── */}
      <div className="qv-grid">
        {items.map(item => (
          <QvCard
            key={item.id}
            item={item}
            thumbnailSize={thumbnailSize}
            isSelected={selected.has(item.id)}
            restoring={restoring}
            onToggle={toggleItem}
            onRestore={handleRestore}
          />
        ))}
      </div>

      {/* ── delete confirmation ── */}
      {confirmDelete && (
        <div className="qv-confirm-overlay" role="dialog" aria-modal="true">
          <div className="qv-confirm-box">
            <p className="qv-confirm-title">Delete {selected.size} file{selected.size !== 1 ? 's' : ''} permanently?</p>
            <p className="qv-confirm-body">
              {formatBytes(selectedBytes)} will be freed. This cannot be undone.
            </p>
            <div className="qv-confirm-actions">
              <button className="qv-confirm-cancel" onClick={() => setConfirmDelete(false)}>
                Cancel
              </button>
              <button className="qv-confirm-delete" onClick={handleDelete}>
                Delete permanently
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
