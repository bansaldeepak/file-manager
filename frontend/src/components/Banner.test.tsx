import { render, fireEvent, act } from '@testing-library/react';
import { Banner } from './Banner';

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

test('renders message', () => {
  const { getByText } = render(
    <Banner message="Moved 3 files (4.3 MB)." onDismiss={() => {}} />
  );
  getByText('Moved 3 files (4.3 MB).');
});

test('calls onDismiss after autoDismissMs + 300ms animation', async () => {
  const onDismiss = vi.fn();
  render(<Banner message="Test" onDismiss={onDismiss} autoDismissMs={5000} />);

  act(() => { vi.advanceTimersByTime(5000); });
  expect(onDismiss).not.toHaveBeenCalled(); // animation still running

  act(() => { vi.advanceTimersByTime(300); });
  expect(onDismiss).toHaveBeenCalledTimes(1);
});

test('calls onUndo when Undo clicked', () => {
  const onUndo = vi.fn();
  const { getByText } = render(
    <Banner message="Test" onUndo={onUndo} onDismiss={() => {}} />
  );
  fireEvent.click(getByText('Undo'));
  expect(onUndo).toHaveBeenCalledTimes(1);
});

test('calls onDismiss when × clicked (after animation)', () => {
  const onDismiss = vi.fn();
  const { getByLabelText } = render(
    <Banner message="Test" onDismiss={onDismiss} />
  );
  fireEvent.click(getByLabelText('Dismiss'));

  act(() => { vi.advanceTimersByTime(300); });
  expect(onDismiss).toHaveBeenCalledTimes(1);
});

test('Undo button is not rendered when onUndo is omitted', () => {
  const { queryByText } = render(
    <Banner message="Test" onDismiss={() => {}} />
  );
  expect(queryByText('Undo')).toBeNull();
});
