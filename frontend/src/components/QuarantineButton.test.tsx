import { render, fireEvent, act } from '@testing-library/react';
import { QuarantineButton } from './QuarantineButton';

test('prevents double-fire on rapid clicks', async () => {
  let callCount = 0;
  const slowConfirm = () =>
    new Promise<void>(resolve => {
      callCount++;
      setTimeout(resolve, 100);
    });

  const { getByRole } = render(<QuarantineButton onConfirm={slowConfirm} />);
  const button = getByRole('button');

  fireEvent.click(button);
  fireEvent.click(button);

  await act(() => new Promise(r => setTimeout(r, 200)));

  expect(callCount).toBe(1);
});

test('re-enables after operation completes', async () => {
  const confirm = vi.fn().mockResolvedValue(undefined);
  const { getByRole } = render(<QuarantineButton onConfirm={confirm} />);
  const button = getByRole('button');

  await act(async () => {
    fireEvent.click(button);
  });

  expect(button).not.toBeDisabled();
});

test('re-enables after operation errors', async () => {
  const confirm = vi.fn().mockRejectedValue(new Error('quarantine failed'));
  const { getByRole } = render(<QuarantineButton onConfirm={confirm} />);
  const button = getByRole('button');

  await act(async () => {
    fireEvent.click(button);
  });

  expect(button).not.toBeDisabled();
});

test('shows Moving label and spinner while pending', async () => {
  let resolve: () => void;
  const slowConfirm = () => new Promise<void>(r => { resolve = r; });

  const { getByRole, getByText } = render(<QuarantineButton onConfirm={slowConfirm} />);
  const button = getByRole('button');

  await act(async () => { fireEvent.click(button); });

  expect(button).toBeDisabled();
  expect(button).toHaveAttribute('aria-busy', 'true');
  getByText('Moving…');

  await act(async () => { resolve!(); });

  expect(button).not.toBeDisabled();
});
