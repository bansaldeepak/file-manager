import { useEffect } from 'react';

export interface KeyboardShortcutHandlers {
  onSearch?: () => void;
  onPreview?: () => void;
  onNavigateNext?: () => void;
  onNavigatePrev?: () => void;
  onConfirm?: () => void;
  onCancel?: () => void;
  onSelectAll?: () => void;
  onQuarantine?: () => void;
  onUndo?: () => void;
}

export function useKeyboardShortcuts(handlers: KeyboardShortcutHandlers) {
  useEffect(() => {
    const handle = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const isInput =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable;

      const cmd = e.metaKey || e.ctrlKey;

      // Cmd shortcuts fire even from inputs (browser-convention bindings)
      if (cmd && e.key === 'f') { e.preventDefault(); handlers.onSearch?.(); return; }
      if (cmd && e.key === 'z') { e.preventDefault(); handlers.onUndo?.(); return; }
      if (cmd && e.key === 'a') { e.preventDefault(); handlers.onSelectAll?.(); return; }

      if (isInput) return;

      if (e.key === ' ') { e.preventDefault(); handlers.onPreview?.(); return; }
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { e.preventDefault(); handlers.onNavigateNext?.(); return; }
      if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); handlers.onNavigatePrev?.(); return; }
      if (e.key === 'Enter') { e.preventDefault(); handlers.onConfirm?.(); return; }
      if (e.key === 'Escape') { e.preventDefault(); handlers.onCancel?.(); return; }
      if (e.key === 'a' && !cmd) { handlers.onSelectAll?.(); return; }
      if (e.key === 'Delete' || e.key === 'Backspace') { e.preventDefault(); handlers.onQuarantine?.(); return; }
    };

    window.addEventListener('keydown', handle);
    return () => window.removeEventListener('keydown', handle);
  }, [handlers]);
}
