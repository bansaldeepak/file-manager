import './ZoomSlider.css';

interface ZoomSliderProps {
  value: number;
  onChange: (size: number) => void;
}

export function ZoomSlider({ value, onChange }: ZoomSliderProps) {
  return (
    <div className="zoom-slider">
      <span className="zoom-icon zoom-small" aria-hidden="true">⊞</span>
      <input
        type="range"
        min={100}
        max={300}
        step={10}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="zoom-range"
        aria-label="Thumbnail size"
        aria-valuemin={100}
        aria-valuemax={300}
        aria-valuenow={value}
        aria-valuetext={`${value}px`}
      />
      <span className="zoom-icon zoom-large" aria-hidden="true">⊞</span>
    </div>
  );
}
