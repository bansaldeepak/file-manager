import { useState, Fragment } from 'react';
import { useThumbnail } from '../hooks/useThumbnail';
import './ContactSheet.css';

export interface FileInfo {
  path: string;
  size: number;
  mtime_ms: number;
  is_keeper: boolean;
  error?: string;
}

export interface GroupInfo {
  group_id: number;
  match_type: 'exact' | 'pixel';
  files: FileInfo[];
}

export type MatchTypeFilter = 'all' | 'exact' | 'pixel';

interface ContactSheetProps {
  groups: GroupInfo[];
  thumbnailSize: number;
  selectedPaths: Set<string>;
  onSelectAll: (add: string[], remove: string[]) => void;
  onSelectGroup: (group: GroupInfo | null) => void;
  selectedGroupId: number | null;
  matchTypeFilter: MatchTypeFilter;
  onMatchTypeFilterChange: (f: MatchTypeFilter) => void;
}

// ── helpers ───────────────────────────────────────────────────────────────────

function formatBytes(bytes: number): string {
  if (bytes >= 1_000_000_000) return `${(bytes / 1_000_000_000).toFixed(1)} GB`;
  if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toFixed(1)} MB`;
  if (bytes >= 1_000) return `${Math.round(bytes / 1_000)} KB`;
  return `${bytes} B`;
}

function basename(path: string): string {
  return path.split('/').filter(Boolean).pop() ?? path;
}

function dirname(path: string): string {
  const parts = path.split('/').filter(Boolean);
  parts.pop();
  return '/' + parts.join('/');
}

// ── breadcrumbs ───────────────────────────────────────────────────────────────

function Breadcrumbs({ path }: { path: string }) {
  const parts = path.split('/').filter(Boolean);
  const show = parts.length > 4 ? ['…', ...parts.slice(-3)] : parts;
  return (
    <span className="breadcrumbs" title={path}>
      {show.map((seg, i) => (
        <Fragment key={i}>
          {i > 0 && <span className="breadcrumbs-sep">›</span>}
          <span className={i === show.length - 1 ? 'breadcrumbs-leaf' : 'breadcrumbs-seg'}>
            {seg}
          </span>
        </Fragment>
      ))}
    </span>
  );
}

// ── filter bar ────────────────────────────────────────────────────────────────

function FilterBar({
  groups,
  value,
  onChange,
}: {
  groups: GroupInfo[];
  value: MatchTypeFilter;
  onChange: (f: MatchTypeFilter) => void;
}) {
  const exactCount = groups.filter(g => g.match_type === 'exact').length;
  const pixelCount = groups.filter(g => g.match_type === 'pixel').length;

  const options: { key: MatchTypeFilter; label: string; count: number }[] = [
    { key: 'all', label: 'All', count: groups.length },
    { key: 'exact', label: 'Exact', count: exactCount },
    { key: 'pixel', label: 'Similar', count: pixelCount },
  ];

  return (
    <div className="filter-bar">
      {options.map(opt => (
        <button
          key={opt.key}
          className={`filter-pill${value === opt.key ? ' filter-pill--active' : ''}`}
          onClick={() => onChange(opt.key)}
          disabled={opt.count === 0}
        >
          {opt.label}
          <span className="filter-pill-count">{opt.count.toLocaleString()}</span>
        </button>
      ))}
    </div>
  );
}

// ── folder grouping ───────────────────────────────────────────────────────────

interface FolderSection {
  folder: string;
  groups: GroupInfo[];
  reclaimableBytes: number;
  isEntirelyDuplicate: boolean;
}

function groupByFolder(groups: GroupInfo[]): FolderSection[] {
  const map = new Map<string, GroupInfo[]>();
  for (const g of groups) {
    const keeper = g.files.find(f => f.is_keeper);
    const folder = keeper ? dirname(keeper.path) : dirname(g.files[0]?.path ?? '');
    const list = map.get(folder) ?? [];
    list.push(g);
    map.set(folder, list);
  }

  const sections: FolderSection[] = [];
  for (const [folder, sectionGroups] of map) {
    const copies = sectionGroups.flatMap(g => g.files.filter(f => !f.is_keeper));
    const reclaimableBytes = copies.reduce((sum, f) => sum + f.size, 0);
    const hasAnyKeeper = sectionGroups.some(g =>
      g.files.some(f => f.is_keeper && dirname(f.path) === folder)
    );
    sections.push({ folder, groups: sectionGroups, reclaimableBytes, isEntirelyDuplicate: !hasAnyKeeper });
  }

  sections.sort((a, b) => {
    if (a.isEntirelyDuplicate !== b.isEntirelyDuplicate) return a.isEntirelyDuplicate ? -1 : 1;
    return b.reclaimableBytes - a.reclaimableBytes;
  });
  return sections;
}

// ── keeper card ───────────────────────────────────────────────────────────────

function KeeperCard({
  group,
  thumbnailSize,
  selectedPaths,
  isSelected,
  onSelect,
}: {
  group: GroupInfo;
  thumbnailSize: number;
  selectedPaths: Set<string>;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const keeper = group.files.find(f => f.is_keeper) ?? group.files[0];
  const copies = group.files.filter(f => !f.is_keeper);
  const copiesSelected = copies.filter(f => selectedPaths.has(f.path)).length;
  const src = useThumbnail(keeper.path, thumbnailSize * 2); // 2× for retina

  return (
    <div
      className={`keeper-card${isSelected ? ' keeper-card--selected' : ''}`}
      style={{ width: thumbnailSize }}
      onClick={onSelect}
      role="button"
      tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && onSelect()}
    >
      <div className="keeper-card-thumb-wrap" style={{ width: thumbnailSize, height: thumbnailSize }}>
        {keeper.error ? (
          <div className="keeper-card-error" style={{ width: thumbnailSize, height: thumbnailSize }}>⚠</div>
        ) : (
          <img
            className="keeper-card-thumb"
            src={src}
            alt={basename(keeper.path)}
            style={{ width: thumbnailSize, height: thumbnailSize }}
            loading="lazy"
            draggable={false}
          />
        )}
        <span className={`keeper-card-badge keeper-card-badge--${group.match_type}`}>
          ×{copies.length} {group.match_type === 'exact' ? 'exact' : 'similar'}
        </span>
        {copiesSelected > 0 && (
          <span className="keeper-card-selected-dot">{copiesSelected}</span>
        )}
      </div>
      <div className="keeper-card-meta">
        <span className="keeper-card-name" title={keeper.path}>{basename(keeper.path)}</span>
        <span className="keeper-card-size">{formatBytes(keeper.size)}</span>
      </div>
    </div>
  );
}

// ── folder section ────────────────────────────────────────────────────────────

function FolderSection({
  section,
  thumbnailSize,
  selectedPaths,
  onSelectAll,
  selectedGroupId,
  onSelectGroup,
}: {
  section: FolderSection;
  thumbnailSize: number;
  selectedPaths: Set<string>;
  onSelectAll: (add: string[], remove: string[]) => void;
  selectedGroupId: number | null;
  onSelectGroup: (group: GroupInfo | null) => void;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const allCopies = section.groups.flatMap(g => g.files.filter(f => !f.is_keeper));
  const allSelected = allCopies.length > 0 && allCopies.every(f => selectedPaths.has(f.path));

  return (
    <div className={`folder-section${section.isEntirelyDuplicate ? ' folder-section--all-dupes' : ''}`}>
      <div className="folder-section-header-row">
        <button
          className="folder-section-collapse-btn"
          onClick={() => setCollapsed(c => !c)}
          aria-expanded={!collapsed}
          aria-label={collapsed ? 'Expand section' : 'Collapse section'}
        >
          {collapsed ? '▶' : '▼'}
        </button>
        <span className="folder-section-icon">📁</span>
        <Breadcrumbs path={section.folder} />
        <span className="folder-section-stats">
          {section.groups.length} group{section.groups.length !== 1 ? 's' : ''}
          {section.reclaimableBytes > 0 && (
            <> · <strong>{formatBytes(section.reclaimableBytes)}</strong></>
          )}
        </span>
        {section.isEntirelyDuplicate && (
          <span className="folder-section-badge">All copies</span>
        )}
        {allCopies.length > 0 && (
          <button
            className="folder-section-select-all"
            onClick={() => {
              const copyPaths = allCopies.map(f => f.path);
              if (allSelected) onSelectAll([], copyPaths);
              else onSelectAll(copyPaths, []);
            }}
          >
            {allSelected ? 'Deselect' : 'Select all copies'}
          </button>
        )}
      </div>

      {!collapsed && (
        <div className="keeper-grid" style={{ padding: 'var(--spacing-md)' }}>
          {section.groups.map(g => (
            <KeeperCard
              key={g.group_id}
              group={g}
              thumbnailSize={thumbnailSize}
              selectedPaths={selectedPaths}
              isSelected={selectedGroupId === g.group_id}
              onSelect={() => onSelectGroup(selectedGroupId === g.group_id ? null : g)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ── main export ───────────────────────────────────────────────────────────────

export function ContactSheet({
  groups,
  thumbnailSize,
  selectedPaths,
  onSelectAll,
  onSelectGroup,
  selectedGroupId,
  matchTypeFilter,
  onMatchTypeFilterChange,
}: ContactSheetProps) {
  const filtered = matchTypeFilter === 'all'
    ? groups
    : groups.filter(g => g.match_type === matchTypeFilter);

  const sections = groupByFolder(filtered);

  return (
    <div className="contact-sheet-root">
      <FilterBar groups={groups} value={matchTypeFilter} onChange={onMatchTypeFilterChange} />
      {sections.length === 0 ? null : (
        <div className="contact-sheet-groups">
          {sections.map(section => (
            <FolderSection
              key={section.folder}
              section={section}
              thumbnailSize={thumbnailSize}
              selectedPaths={selectedPaths}
              onSelectAll={onSelectAll}
              selectedGroupId={selectedGroupId}
              onSelectGroup={onSelectGroup}
            />
          ))}
        </div>
      )}
    </div>
  );
}
