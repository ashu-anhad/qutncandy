import { Link } from "react-router-dom";

// Four-point sparkle from the logo.
export function Sparkle({ size = 12 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 0C12.9 7.5 16.5 11.1 24 12C16.5 12.9 12.9 16.5 12 24C11.1 16.5 7.5 12.9 0 12C7.5 11.1 11.1 7.5 12 0Z" fill="currentColor" />
    </svg>
  );
}

// Gold hairline with a centred sparkle, as under the logo's wordmark.
export function RuleSpark({ className = "" }) {
  return (
    <div className={`rule-spark ${className}`} role="presentation">
      <Sparkle size={10} />
    </div>
  );
}

// "QUTNCANDY" set like the logo: spaced roman capitals with the A in gold.
export function Wordmark() {
  return (
    <span className="wordmark">
      QUTNC<span className="gold">A</span>NDY
    </span>
  );
}

export default function Brand({ to = "/", label = "QutnCandy home" }) {
  return (
    <Link to={to} className="brand" aria-label={label}>
      <img src="/brand/mark.png" alt="" className="brand-mark" width="40" height="40" />
      <Wordmark />
    </Link>
  );
}
