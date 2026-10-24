import { convertFileSrc } from '@tauri-apps/api/core';
import './ContactSheet.css';

export interface FileInfo {
  path: string;
  size: number;
  is_keeper: boolean;
  error?: string;
}

export interface GroupInfo {
  group_id: number;
  match_type: 'exact' | 'pixel';
  files: FileInfo[];
}

interface ContactSheetProps {
  groups: GroupInfo[];
  thumbnailSize: number;
  selectedPaths: Set<string>;
  onToggleSelect: (path: string) => void;
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

function DuplicateFile({
  file,
  size,
  selected,
  onToggle,
}: {
  file: FileInfo;
  size: number;
  selected: boolean;
  onToggle: () => void;
}) {
  const src = convertFileSrc(file.path);

  return (
    <div
      className="dup-file"
      data-keeper={file.is_keeper}
      data-selected={selected}
      style={{ width: size }}
      onClick={() => !file.is_keeper && onToggle()}
    >
      {file.error ? (
        <div className="dup-thumb dup-thumb--error" style={{ width: size, height: size }}>
          <span>⚠</span>
        </div>
      ) : (
        <img
          className="dup-thumb"
          src={src}
          alt={basename(file.path)}
          style={{ width: size, height: size }}
          loading="lazy"
          draggable={false}
        />
      )}
      <div className="dup-meta">
        {file.is_keeper ? (
          <span className="dup-badge dup-badge--keeper">Keep</span>
        ) : (
          <input
            type="checkbox"
            className="dup-checkbox"
            checked={selected}
            onChange={onToggle}
            onClick={e => e.stopPropagation()}
            aria-label={`Select ${basename(file.path)} for quarantine`}
          />
        )}
        <span className="dup-filename" title={file.path}>{basename(file.path)}</span>
        <span className="dup-size">{formatBytes(file.size)}</span>
      </div>
    </div>
  );
}

export function ContactSheet({
  groups,
  thumbnailSize,
  selectedPaths,
  onToggleSelect,
}: ContactSheetProps) {
  if (groups.length === 0) {
    return null;
  }

  return (
    <div className="contact-sheet-groups">
      {groups.map(group => (
        <div key={group.group_id} className="dup-group">
          <div className="dup-group-header">
            <span className="dup-group-label">
              {group.match_type === 'exact' ? 'Exact duplicate' : 'Pixel-identical'}
            </span>
            <span className="dup-group-count">{group.files.length} files</span>
          </div>
          <div className="dup-group-files">
            {group.files.map(file => (
              <DuplicateFile
                key={file.path}
                file={file}
                size={thumbnailSize}
                selected={selectedPaths.has(file.path)}
                onToggle={() => onToggleSelect(file.path)}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
