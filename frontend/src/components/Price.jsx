import { formatPrice } from "../lib/format";

export default function Price({ min, max, className = "price" }) {
  if (min == null) return null;
  return <span className={className}>{min === max || max == null ? formatPrice(min) : `${formatPrice(min)} – ${formatPrice(max)}`}</span>;
}
