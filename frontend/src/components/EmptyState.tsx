import { useState } from 'react';
import './EmptyState.css';

interface DropZoneProps {
  onDrop: (paths: string[]) => void;
  hint?: string;
}

interface EmptyStateProps {
  title: string;
  body?: string;
  action?: { label: string; onClick: () => void };
  dropZone?: DropZoneProps;
}

export function EmptyState({ title, body, action, dropZone }: EmptyStateProps) {
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = dropZone
    ? (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); }
    : undefined;

  const handleDragLeave = dropZone ? () => setIsDragging(false) : undefined;

  const handleDrop = dropZone
    ? (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        // In Tauri 2's webview, File objects have a .path property injected by the shell
        const paths = Array.from(e.dataTransfer.files)
          .map(f => (f as unknown as { path: string }).path)
          .filter(Boolean);
        if (paths.length > 0) dropZone.onDrop(paths);
      }
    : undefined;

  return (
    <div
      className="empty-state"
      data-drop-zone={dropZone ? 'true' : 'false'}
      data-dragging={isDragging ? 'true' : 'false'}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <h2 className="empty-state-title">{title}</h2>
      {body && <p className="empty-state-body">{body}</p>}
      {dropZone?.hint && <p className="empty-state-hint">{dropZone.hint}</p>}
      {action && (
        <button className="empty-state-action" onClick={action.onClick}>
          {action.label}
        </button>
      )}
    </div>
  );
}
