// Read-only star rating. `value` can be fractional (e.g. 4.5).
export default function Stars({ value = 0, size = 14, label }) {
  const pct = Math.max(0, Math.min(100, (value / 5) * 100));
  return (
    <span className="stars" style={{ fontSize: size }} role="img" aria-label={label ?? `${value.toFixed(1)} out of 5 stars`}>
      <span className="stars-bg" aria-hidden="true">★★★★★</span>
      <span className="stars-fg" style={{ width: `${pct}%` }} aria-hidden="true">★★★★★</span>
    </span>
  );
}

export function StarInput({ value, onChange }) {
  return (
    <span className="star-input" role="radiogroup" aria-label="Rating">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          role="radio"
          aria-checked={value === n}
          aria-label={`${n} star${n > 1 ? "s" : ""}`}
          className={n <= value ? "on" : ""}
          onClick={() => onChange(n)}
        >
          ★
        </button>
      ))}
    </span>
  );
}
