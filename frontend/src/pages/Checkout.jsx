import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import * as ordersApi from "../api/orders";
import { useCart } from "../cart.jsx";
import AddressForm, { AddressLines } from "../components/AddressForm.jsx";
import OrderTotals from "../components/OrderTotals.jsx";
import { formatPrice } from "../lib/format";
import { payForOrder } from "../lib/razorpay";

export default function Checkout() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { cart, refresh: refreshCart } = useCart();

  const addresses = useQuery({ queryKey: ["addresses"], queryFn: ordersApi.listAddresses });
  const [addressId, setAddressId] = useState(null);
  const [adding, setAdding] = useState(false);

  const [codeInput, setCodeInput] = useState("");
  const [code, setCode] = useState("");
  // Re-quote whenever the cart changes (e.g. right after a guest cart is merged on login).
  const quote = useQuery({
    queryKey: ["quote", code, cart?.item_count, cart?.subtotal],
    queryFn: () => ordersApi.getQuote(code),
    enabled: !!cart,
    staleTime: 0,
  });

  const [placing, setPlacing] = useState(false);
  const [error, setError] = useState("");

  // Pick the default address once addresses load; open the form if there are none.
  useEffect(() => {
    if (!addresses.data) return;
    if (!addresses.data.length) setAdding(true);
    else if (!addresses.data.some((a) => a.id === addressId)) setAddressId(addresses.data[0].id);
  }, [addresses.data, addressId]);

  const saveAddress = async (data) => {
    const created = await ordersApi.createAddress(data);
    await queryClient.invalidateQueries({ queryKey: ["addresses"] });
    setAddressId(created.id);
    setAdding(false);
  };

  const applyCode = (e) => {
    e.preventDefault();
    setCode(codeInput.trim());
  };

  const place = async () => {
    setPlacing(true);
    setError("");
    let order;
    try {
      order = await ordersApi.placeOrder({ address_id: addressId, discount_code: quote.data?.discount_code || null });
    } catch (err) {
      setError(err.message);
      quote.refetch();
      setPlacing(false);
      return;
    }
    refreshCart();
    queryClient.invalidateQueries({ queryKey: ["orders"] });
    // Go straight to payment. Whatever happens, land on the order page, which can retry.
    try {
      const paid = await payForOrder(order.number);
      queryClient.setQueryData(["order", order.number], paid);
      navigate(`/orders/${order.number}`, { replace: true, state: { justPaid: true } });
    } catch (err) {
      navigate(`/orders/${order.number}`, { replace: true, state: { paymentError: err.message } });
    }
  };

  const q = quote.data;
  if (!q) return quote.error ? <p className="error">{quote.error.message}</p> : <p className="muted">Loading…</p>;
  if (!q.items.length) {
    return (
      <section className="center stack empty">
        <h1>Your cart is empty</h1>
        <div><Link to="/products" className="button">Start shopping</Link></div>
      </section>
    );
  }

  return (
    <div className="cart-layout">
      <section className="stack">
        <h1>Checkout</h1>

        <div className="card stack">
          <h2>1. Delivery address</h2>
          {addresses.data?.length > 0 && (
            <div className="address-options">
              {addresses.data.map((a) => (
                <label key={a.id} className={`address-option${a.id === addressId ? " selected" : ""}`}>
                  <input type="radio" name="address" checked={a.id === addressId} onChange={() => setAddressId(a.id)} />
                  <AddressLines address={a} />
                </label>
              ))}
            </div>
          )}
          {adding ? (
            <AddressForm onSubmit={saveAddress} onCancel={addresses.data?.length ? () => setAdding(false) : undefined}
              submitLabel="Use this address" />
          ) : (
            <div><button type="button" className="secondary" onClick={() => setAdding(true)}>Add a new address</button></div>
          )}
        </div>

        <div className="card stack">
          <h2>2. Discount code</h2>
          <form className="row" onSubmit={applyCode}>
            <input value={codeInput} onChange={(e) => setCodeInput(e.target.value)} placeholder="Enter code" maxLength={40} />
            <button type="submit" className="secondary">Apply</button>
            {q?.discount_code && (
              <button type="button" className="danger-link" onClick={() => { setCode(""); setCodeInput(""); }}>Remove</button>
            )}
          </form>
          {q?.discount_code && <span className="stock ok small">Code {q.discount_code} applied — you save {formatPrice(q.discount)}</span>}
          {q?.discount_error && <span className="stock out small">{q.discount_error}</span>}
        </div>
      </section>

      <aside className="card stack summary">
        <h2>Order summary</h2>
        <ul className="mini-lines">
          {q?.items.map((line) => (
            <li key={line.variant_id}>
              {line.image && <img src={line.image} alt="" />}
              <span className="stack-tight">
                <span>{line.product_name}</span>
                <span className="muted small">{line.colour} · {line.size} · Qty {line.qty}</span>
              </span>
              <span>{formatPrice(line.line_total)}</span>
            </li>
          ))}
        </ul>
        {q && <OrderTotals subtotal={q.subtotal} discount={q.discount} discountCode={q.discount_code} shipping={q.shipping_fee} total={q.total} />}
        {q?.problems.map((p) => <p key={p} className="error">{p}</p>)}
        {error && <p className="error">{error}</p>}
        <button disabled={!q?.can_place || !addressId || adding || placing} onClick={place}>
          {placing ? "Opening payment…" : `Place order & pay${q ? ` · ${formatPrice(q.total)}` : ""}`}
        </button>
        <span className="muted small">Pay securely with UPI, cards, netbanking or wallets via Razorpay. Items are held for 15 minutes while you pay.</span>
        <Link to="/cart" className="small">← Back to cart</Link>
      </aside>
    </div>
  );
}
