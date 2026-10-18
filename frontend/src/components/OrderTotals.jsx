import { formatPrice } from "../lib/format";

export default function OrderTotals({ subtotal, discount, discountCode, shipping, total }) {
  return (
    <dl className="totals">
      <dt>Subtotal</dt><dd>{formatPrice(subtotal)}</dd>
      {discount > 0 && <><dt>Discount{discountCode ? ` (${discountCode})` : ""}</dt><dd className="saving">−{formatPrice(discount)}</dd></>}
      <dt>Shipping</dt><dd>{shipping === 0 ? "Free" : formatPrice(shipping)}</dd>
      <dt className="total">Total</dt><dd className="total">{formatPrice(total)}</dd>
    </dl>
  );
}
