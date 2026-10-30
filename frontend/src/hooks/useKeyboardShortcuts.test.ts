import { renderHook } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, test, expect, vi, beforeEach } from 'vitest';
import { useKeyboardShortcuts } from './useKeyboardShortcuts';

describe('useKeyboardShortcuts', () => {
  beforeEach(() => {
    // Reset DOM focus to body before each test
    document.body.focus();
  });

  test('Cmd+F calls onSearch', async () => {
    const onSearch = vi.fn();
    renderHook(() => useKeyboardShortcuts({ onSearch }));
    await userEvent.keyboard('{Meta>}f{/Meta}');
    expect(onSearch).toHaveBeenCalledTimes(1);
  });

  test('Space calls onPreview when focus is not in an input', async () => {
    const onPreview = vi.fn();
    renderHook(() => useKeyboardShortcuts({ onPreview }));
    await userEvent.keyboard(' ');
    expect(onPreview).toHaveBeenCalledTimes(1);
  });

  test('Space does NOT call onPreview when an input is focused', async () => {
    const onPreview = vi.fn();
    renderHook(() => useKeyboardShortcuts({ onPreview }));
    const input = document.createElement('input');
    document.body.appendChild(input);
    input.focus();
    await userEvent.keyboard(' ');
    expect(onPreview).not.toHaveBeenCalled();
    document.body.removeChild(input);
  });

  test('Cmd+F calls onSearch even when an input is focused', async () => {
    const onSearch = vi.fn();
    renderHook(() => useKeyboardShortcuts({ onSearch }));
    const input = document.createElement('input');
    document.body.appendChild(input);
    input.focus();
    await userEvent.keyboard('{Meta>}f{/Meta}');
    expect(onSearch).toHaveBeenCalledTimes(1);
    document.body.removeChild(input);
  });

  test('Escape calls onCancel', async () => {
    const onCancel = vi.fn();
    renderHook(() => useKeyboardShortcuts({ onCancel }));
    await userEvent.keyboard('{Escape}');
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  test('Delete calls onQuarantine', async () => {
    const onQuarantine = vi.fn();
    renderHook(() => useKeyboardShortcuts({ onQuarantine }));
    await userEvent.keyboard('{Delete}');
    expect(onQuarantine).toHaveBeenCalledTimes(1);
  });
});
