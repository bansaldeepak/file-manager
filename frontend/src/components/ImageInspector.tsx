import { useState, useEffect } from 'react';
import { convertFileSrc, invoke } from '@tauri-apps/api/core';
import type { FileInfo } from './ContactSheet';
import './ImageInspector.css';

interface Props {
  file: FileInfo | null;
}

function formatBytes(bytes: number): string {
  if (bytes >= 1_000_000_000) return `${(bytes / 1_000_000_000).toFixed(2)} GB`;
  if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toFixed(2)} MB`;
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

export function ImageInspector({ file }: Props) {
  const [dims, setDims] = useState<{ w: number; h: number } | null>(null);

  useEffect(() => {
    setDims(null);
  }, [file?.path]);

  if (!file) {
    return (
      <div className="inspector-empty">
        <p>Click an image to inspect it.</p>
      </div>
    );
  }

  const src = convertFileSrc(file.path);
  const isImage = /\.(jpg|jpeg|png|heic|heif|webp|tiff|tif|bmp)$/i.test(file.path);

  const handleQuickLook = () => {
    invoke('preview_file', { path: file.path }).catch(console.error);
  };

  return (
    <div className="inspector-content">
      <div className="inspector-preview">
        {isImage ? (
          <img
            src={src}
            alt={basename(file.path)}
            className="inspector-img"
            onLoad={(e) => {
              const img = e.currentTarget;
              setDims({ w: img.naturalWidth, h: img.naturalHeight });
            }}
            draggable={false}
          />
        ) : (
          <div className="inspector-no-preview">No preview</div>
        )}
      </div>

      <div className="inspector-meta">
        <div className="inspector-badge-row">
          <span className={`inspector-badge ${file.is_keeper ? 'inspector-badge--keeper' : 'inspector-badge--copy'}`}>
            {file.is_keeper ? 'Original' : 'Copy'}
          </span>
          {isImage && (
            <button className="inspector-ql-btn" onClick={handleQuickLook} title="Open in Quick Look">
              Quick Look
            </button>
          )}
        </div>

        <dl className="inspector-dl">
          <dt>Name</dt>
          <dd title={file.path}>{basename(file.path)}</dd>

          <dt>Folder</dt>
          <dd className="inspector-path" title={dirname(file.path)}>{dirname(file.path)}</dd>

          <dt>Size</dt>
          <dd>{formatBytes(file.size)}</dd>

          {dims && (
            <>
              <dt>Dimensions</dt>
              <dd>{dims.w} × {dims.h}</dd>
            </>
          )}

          <dt>Modified</dt>
          <dd>{formatDate(file.mtime_ms)}</dd>
        </dl>
      </div>
    </div>
  );
}
