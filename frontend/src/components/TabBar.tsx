import './TabBar.css';

export type MediaTab = 'photos' | 'videos' | 'all';

interface TabBarProps {
  value: MediaTab;
  onChange: (tab: MediaTab) => void;
}

const TABS: { value: MediaTab; label: string }[] = [
  { value: 'photos', label: 'Photos' },
  { value: 'videos', label: 'Videos' },
  { value: 'all', label: 'All' },
];

export function TabBar({ value, onChange }: TabBarProps) {
  return (
    <div className="tab-bar" role="tablist" aria-label="Media type filter">
      {TABS.map(tab => (
        <button
          key={tab.value}
          role="tab"
          aria-selected={value === tab.value}
          className="tab-button"
          data-active={value === tab.value}
          onClick={() => onChange(tab.value)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
