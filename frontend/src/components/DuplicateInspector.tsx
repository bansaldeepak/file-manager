import { useState, useEffect, Fragment } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { useThumbnail } from '../hooks/useThumbnail';
import type { GroupInfo, FileInfo } from './ContactSheet';
import './DuplicateInspector.css';

interface Props {
  group: GroupInfo | null;
  selectedPaths: Set<string>;
  onToggle: (path: string) => void;
}

// ── helpers ───────────────────────────────────────────────────────────────────

function formatBytes(bytes: number): string {
  if (bytes >= 1_000_000_000) return `${(bytes / 1_000_000_000).toFixed(1)} GB`;
  if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toFixed(1)} MB`;
  if (bytes >= 1_000) return `${Math.round(bytes / 1_000)} KB`;
  return `${bytes} B`;
}

function formatDate(ms: number): string {
  if (!ms) return '—';
  return new Date(ms).toLocaleString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function basename(path: string): string {
  return path.split('/').filter(Boolean).pop() ?? path;
}

function dirname(path: string): string {
  const parts = path.split('/').filter(Boolean);
  parts.pop();
  return '/' + parts.join('/');
}

// ── breadcrumb path ───────────────────────────────────────────────────────────

function PathCrumbs({ path }: { path: string }) {
  const parts = path.split('/').filter(Boolean);
  const show = parts.length > 4 ? ['…', ...parts.slice(-3)] : parts;
  return (
    <span className="di-path-crumbs" title={path}>
      {show.map((seg, i) => (
        <Fragment key={i}>
          {i > 0 && <span className="di-path-sep">›</span>}
          <span className={i === show.length - 1 ? 'di-path-leaf' : 'di-path-seg'}>{seg}</span>
        </Fragment>
      ))}
    </span>
  );
}

// ── copy card in carousel ─────────────────────────────────────────────────────

function CopyCard({
  file,
  isChecked,
  isFocused,
  onFocus,
  onToggle,
}: {
  file: FileInfo;
  isChecked: boolean;
  isFocused: boolean;
  onFocus: () => void;
  onToggle: (e: React.MouseEvent) => void;
}) {
  const src = useThumbnail(file.path, 160);
  return (
    <div
      className={`di-copy-card${isFocused ? ' di-copy-card--focused' : ''}`}
      onClick={onFocus}
      role="button"
      tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && onFocus()}
    >
      <div className="di-copy-thumb-wrap">
        <img
          className="di-copy-thumb"
          src={src}
          alt={basename(file.path)}
          draggable={false}
          loading="lazy"
        />
        <button
          className={`di-copy-check${isChecked ? ' di-copy-check--on' : ''}`}
          onClick={onToggle}
          aria-label={isChecked ? 'Deselect for quarantine' : 'Select for quarantine'}
          title={isChecked ? 'Deselect' : 'Select for quarantine'}
        >
          {isChecked ? '✓' : ''}
        </button>
      </div>
      <div className="di-copy-label" title={file.path}>
        {basename(file.path)}
      </div>
    </div>
  );
}

// ── preview image (wraps hook so it can be called unconditionally) ────────────

function PreviewImage({ file, onLoad }: {
  file: FileInfo;
  onLoad: (w: number, h: number) => void;
}) {
  const src = useThumbnail(file.path, 800);
  return (
    <img
      key={file.path}
      className="di-preview-img"
      src={src}
      alt={basename(file.path)}
      draggable={false}
      onLoad={e => {
        const img = e.currentTarget;
        onLoad(img.naturalWidth, img.naturalHeight);
      }}
    />
  );
}

// ── main component ────────────────────────────────────────────────────────────

export function DuplicateInspector({ group, selectedPaths, onToggle }: Props) {
  const [focusedPath, setFocusedPath] = useState<string | null>(null);
  const [dims, setDims] = useState<{ w: number; h: number } | null>(null);

  useEffect(() => {
    setFocusedPath(null);
    setDims(null);
  }, [group?.group_id]);

  if (!group) {
    return (
      <div className="di-empty">
        <span className="di-empty-icon">🖼</span>
        <p>Select a group to inspect.</p>
      </div>
    );
  }

  const keeper = group.files.find(f => f.is_keeper) ?? group.files[0];
  const copies = group.files.filter(f => !f.is_keeper);
  const focusedFile: FileInfo = focusedPath
    ? (group.files.find(f => f.path === focusedPath) ?? keeper)
    : keeper;
  const focusedIsKeeper = focusedFile === keeper || focusedFile.is_keeper;

  const handleQuickLook = () => {
    invoke('preview_file', { path: focusedFile.path }).catch(console.error);
  };

  const copiesSelected = copies.filter(f => selectedPaths.has(f.path)).length;

  return (
    <div className="di-root">

      {/* ── preview ──────────────────────────────── */}
      <div className="di-preview-wrap">
        <PreviewImage
          file={focusedFile}
          onLoad={(w, h) => setDims({ w, h })}
        />
      </div>

      {/* ── badge + quick look ────────────────────── */}
      <div className="di-badge-row">
        <span className={`di-badge ${focusedIsKeeper ? 'di-badge--keeper' : 'di-badge--copy'}`}>
          {focusedIsKeeper ? 'Original' : 'Copy'}
        </span>
        <button className="di-ql-btn" onClick={handleQuickLook}>Quick Look</button>
      </div>

      {/* ── metadata ─────────────────────────────── */}
      <dl className="di-meta">
        <dt>Name</dt>
        <dd title={focusedFile.path}>{basename(focusedFile.path)}</dd>

        <dt>Folder</dt>
        <dd><PathCrumbs path={dirname(focusedFile.path)} /></dd>

        <dt>Size</dt>
        <dd>{formatBytes(focusedFile.size)}</dd>

        {dims && (
          <>
            <dt>Dimensions</dt>
            <dd>{dims.w} × {dims.h}</dd>
          </>
        )}

        <dt>Modified</dt>
        <dd>{formatDate(focusedFile.mtime_ms)}</dd>
      </dl>

      {/* ── copies carousel ──────────────────────── */}
      {copies.length > 0 && (
        <div className="di-copies-section">
          <div className="di-copies-header">
            <span className="di-copies-label">
              {copies.length} {group.match_type === 'exact' ? 'exact' : 'similar'} cop{copies.length !== 1 ? 'ies' : 'y'}
            </span>
            {copiesSelected > 0 && (
              <span className="di-copies-selected">{copiesSelected} selected</span>
            )}
          </div>
          <div className="di-copies-carousel">
            {copies.map(copy => (
              <CopyCard
                key={copy.path}
                file={copy}
                isChecked={selectedPaths.has(copy.path)}
                isFocused={focusedPath === copy.path}
                onFocus={() => {
                  setFocusedPath(prev => prev === copy.path ? null : copy.path);
                  setDims(null);
                }}
                onToggle={e => {
                  e.stopPropagation();
                  onToggle(copy.path);
                }}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
