import { useState } from 'react';
import './QuarantineButton.css';

interface QuarantineButtonProps {
  onConfirm: () => Promise<void>;
  disabled?: boolean;
  label?: string;
}

export function QuarantineButton({ onConfirm, disabled, label = 'Quarantine' }: QuarantineButtonProps) {
  const [pending, setPending] = useState(false);

  const handleClick = async () => {
    if (pending || disabled) return;
    setPending(true);
    try {
      await onConfirm();
    } catch {
      // caller owns error display; button re-enables via finally regardless
    } finally {
      setPending(false);
    }
  };

  return (
    <button
      className="quarantine-button"
      onClick={handleClick}
      disabled={pending || disabled}
      aria-busy={pending}
      aria-label={pending ? 'Quarantining…' : label}
    >
      {pending && <span className="quarantine-button-spinner" aria-hidden="true" />}
      {pending ? 'Moving…' : label}
    </button>
  );
}
