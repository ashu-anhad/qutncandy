import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useCart } from "../cart.jsx";
import { formatPrice } from "../lib/format";

export default function Cart() {
  const { cart, isLoading, setQty, remove } = useCart();
  const navigate = useNavigate();
  const [error, setError] = useState("");

  const run = (fn) => fn().then(() => setError("")).catch((e) => setError(e.message));

  if (isLoading && !cart) return <p className="muted">Loading…</p>;
  if (!cart?.items.length) {
    return (
      <section className="center stack empty">
        <h1>Your cart is empty</h1>
        <p className="muted">Find something you love in our handcrafted collection.</p>
        <div><Link to="/products" className="button">Start shopping</Link></div>
      </section>
    );
  }

  const blocked = cart.items.some((i) => !i.available);
  const toFree = cart.free_shipping_min - cart.subtotal;

  return (
    <div className="cart-layout">
      <section className="stack">
        <h1>Your cart <span className="muted">({cart.item_count})</span></h1>
        {error && <p className="error">{error}</p>}
        <ul className="cart-lines">
          {cart.items.map((line) => (
            <li key={line.variant_id} className="cart-line">
              <Link to={`/p/${line.product_slug}`} className="cart-thumb">
                {line.image ? <img src={line.image} alt="" /> : <div className="img-placeholder" />}
              </Link>
              <div className="cart-line-info">
                <Link to={`/p/${line.product_slug}`} className="product-card-name">{line.product_name}</Link>
                <span className="muted small">{line.colour} · {line.size}</span>
                <span className="small">{formatPrice(line.unit_price)}</span>
                {!line.available && (
                  <span className="stock out small">
                    {line.max_qty === 0 ? "No longer available — please remove" : `Only ${line.stock} left — reduce quantity`}
                  </span>
                )}
                <div className="row">
                  <label className="qty">
                    Qty
                    <select value={line.qty} onChange={(e) => run(() => setQty(line.variant_id, Number(e.target.value)))}>
                      {Array.from({ length: Math.max(line.max_qty, line.qty) }, (_, i) => i + 1).map((n) => (
                        <option key={n} value={n} disabled={n > line.max_qty}>{n}</option>
                      ))}
                    </select>
                  </label>
                  <button type="button" className="danger-link" onClick={() => run(() => remove(line.variant_id))}>Remove</button>
                </div>
              </div>
              <strong className="cart-line-total">{formatPrice(line.line_total)}</strong>
            </li>
          ))}
        </ul>
      </section>

      <aside className="card stack summary">
        <h2>Summary</h2>
        <dl className="totals">
          <dt>Subtotal</dt><dd>{formatPrice(cart.subtotal)}</dd>
          <dt>Shipping</dt><dd>{toFree <= 0 ? "Free" : formatPrice(cart.shipping_fee)}</dd>
        </dl>
        <p className="muted small">
          {toFree > 0 ? `Add ${formatPrice(toFree)} more for free shipping.` : "You get free shipping."} Discount codes can be applied at checkout.
        </p>
        <button disabled={blocked} onClick={() => navigate("/checkout")}>Proceed to checkout</button>
        {blocked && <span className="stock out small">Fix the items marked above to continue.</span>}
      </aside>
    </div>
  );
}
