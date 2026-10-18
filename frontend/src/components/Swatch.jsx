import { colourHex } from "../lib/format";

export default function Swatch({ colour, size = 14, selected = false, onClick, disabled = false }) {
  const style = { width: size, height: size, background: colourHex(colour) };
  if (!onClick) return <span className="swatch" style={style} title={colour} aria-label={colour} />;
  return (
    <button
      type="button"
      className={`swatch swatch-btn${selected ? " selected" : ""}`}
      style={style}
      title={colour}
      aria-label={colour}
      aria-pressed={selected}
      disabled={disabled}
      onClick={onClick}
    />
  );
}
