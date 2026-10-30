import React, { useRef } from 'react';
import './SearchBar.css';

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  focusRef?: React.RefObject<HTMLInputElement>;
}

export function SearchBar({ value, onChange, focusRef }: SearchBarProps) {
  const localRef = useRef<HTMLInputElement>(null);
  const inputRef = focusRef ?? localRef;

  return (
    <div className="search-bar">
      <svg className="search-icon" width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
        <circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.5" fill="none" />
        <line x1="9.5" y1="9.5" x2="13" y2="13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
      <input
        ref={inputRef}
        type="search"
        placeholder="Search"
        value={value}
        onChange={e => onChange(e.target.value)}
        className="search-input"
        aria-label="Search files"
      />
      {value && (
        <button className="search-clear" onClick={() => onChange('')} aria-label="Clear search">
          ×
        </button>
      )}
    </div>
  );
}
