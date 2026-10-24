import './ActionBar.css';
import { ZoomSlider } from './ZoomSlider';
import type { MatchTypeFilter } from './ContactSheet';

interface Props {
  selectedCount: number;
  selectedBytes: number;
  savingsBytes: number;
  matchTypeFilter: MatchTypeFilter;
  thumbnailSize: number;
  onThumbnailSizeChange: (v: number) => void;
  onQuarantine: () => void;
  quarantining: boolean;
}

function formatBytes(bytes: number): string {
  if (bytes >= 1_000_000_000) return `${(bytes / 1_000_000_000).toFixed(1)} GB`;
  if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toFixed(1)} MB`;
  if (bytes >= 1_000) return `${Math.round(bytes / 1_000)} KB`;
  return `${bytes} B`;
}

function savingsLabel(bytes: number, filter: MatchTypeFilter): string {
  if (bytes === 0) return '';
  const size = formatBytes(bytes);
  if (filter === 'exact') return `${size} in exact copies`;
  if (filter === 'pixel') return `${size} in similar copies`;
  return `${size} in copies`;
}

export function ActionBar({
  selectedCount,
  selectedBytes,
  savingsBytes,
  matchTypeFilter,
  thumbnailSize,
  onThumbnailSizeChange,
  onQuarantine,
  quarantining,
}: Props) {
  const savings = savingsLabel(savingsBytes, matchTypeFilter);

  return (
    <div className="action-bar">
      <div className="action-bar-left">
        {selectedCount > 0 ? (
          <>
            <span className="action-bar-count">
              {selectedCount} cop{selectedCount !== 1 ? 'ies' : 'y'} selected
              {selectedBytes > 0 && <> · <strong>{formatBytes(selectedBytes)}</strong></>}
            </span>
            <button
              className="action-bar-quarantine-btn"
              onClick={onQuarantine}
              disabled={quarantining}
            >
              {quarantining ? 'Moving…' : `Move to Quarantine`}
            </button>
          </>
        ) : savings ? (
          <span className="action-bar-savings">
            <span className="action-bar-savings-size">{formatBytes(savingsBytes)}</span>
            {' '}recoverable{matchTypeFilter === 'exact' ? ' in exact copies' : matchTypeFilter === 'pixel' ? ' in similar copies' : ''}
          </span>
        ) : (
          <span className="action-bar-hint">Select copies to quarantine them</span>
        )}
      </div>
      <div className="action-bar-right">
        <ZoomSlider value={thumbnailSize} onChange={onThumbnailSizeChange} />
      </div>
    </div>
  );
}
