import { useEffect, useState } from 'react';
import './Banner.css';

interface BannerProps {
  message: string;
  onUndo?: () => void;
  onDismiss: () => void;
  autoDismissMs?: number;
}

export function Banner({ message, onUndo, onDismiss, autoDismissMs = 5000 }: BannerProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    requestAnimationFrame(() => setVisible(true));

    const timer = setTimeout(() => {
      setVisible(false);
      setTimeout(onDismiss, 300);
    }, autoDismissMs);

    return () => clearTimeout(timer);
  }, [autoDismissMs, onDismiss]);

  const dismiss = () => {
    setVisible(false);
    setTimeout(onDismiss, 300);
  };

  return (
    <div className="banner" data-visible={visible} role="status" aria-live="polite">
      <span className="banner-message">{message}</span>
      {onUndo && (
        <button className="banner-undo" onClick={onUndo}>
          Undo
        </button>
      )}
      <button className="banner-close" onClick={dismiss} aria-label="Dismiss">
        ×
      </button>
    </div>
  );
}
