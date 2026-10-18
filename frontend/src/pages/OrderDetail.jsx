import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { cancelOrder, getOrder } from "../api/orders";
import { AddressLines } from "../components/AddressForm.jsx";
import OrderTotals from "../components/OrderTotals.jsx";
import { ORDER_STATUS, REFUND_STATUS, formatDateTime, formatPrice } from "../lib/format";
import { PaymentDismissed, payForOrder } from "../lib/razorpay";

export default function OrderDetail() {
  const { number } = useParams();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { data: order, isLoading, error, refetch } = useQuery({ queryKey: ["order", number], queryFn: () => getOrder(number) });
  const [message, setMessage] = useState(location.state?.paymentError ?? "");
  const [paying, setPaying] = useState(false);
  const [windowClosed, setWindowClosed] = useState(false);
  const justPaid = location.state?.justPaid;

  const update = (data) => {
    queryClient.setQueryData(["order", number], data);
    queryClient.invalidateQueries({ queryKey: ["orders"] });
  };

  const pay = async () => {
    setPaying(true);
    setMessage("");
    try {
      update(await payForOrder(number));
    } catch (err) {
      setMessage(err instanceof PaymentDismissed ? "" : err.message);
      refetch();
    } finally {
      setPaying(false);
    }
  };

  const cancel = async () => {
    if (!confirm("Cancel this order?")) return;
    try {
      update(await cancelOrder(number));
    } catch (err) {
      setMessage(err.message);
    }
  };

  if (isLoading) return <p className="muted">Loading…</p>;
  if (error) return <p className="error">{error.message}</p>;

  return (
    <section className="stack narrow-wide">
      <Link to="/orders" className="muted small">← My orders</Link>
      <div className="section-head">
        <div>
          <h1>Order {order.number}</h1>
          <span className="muted small">Placed {formatDateTime(order.created_at)}</span>
        </div>
        <span className={`pill status-${order.status}`}>{ORDER_STATUS[order.status]}</span>
      </div>

      {order.status !== "cancelled" && order.status !== "pending_payment" && <Progress order={order} />}

      {order.status === "shipped" && (
        <div className="notice notice-ok stack">
          <strong>Your order is on its way.</strong>
          <span>Courier: {order.courier} · Tracking number: <strong>{order.tracking_no}</strong></span>
        </div>
      )}

      {order.refund_status && (
        <div className={`notice stack${order.refund_status === "refunded" ? " notice-ok" : ""}`}>
          <strong>{order.refund_status === "refunded" ? "Your refund has been issued." : "A refund is on its way."}</strong>
          <span>
            {order.refund_status === "refunded"
              ? "It can take 5–7 working days to show in your account."
              : `We'll refund ${formatPrice(order.total)} to your original payment method within 5–7 working days.`}
          </span>
        </div>
      )}

      {order.status === "paid" && (
        <div className="notice notice-ok stack">
          <strong>{justPaid ? "Thank you! Your payment was successful." : "Payment received."}</strong>
          <span>We're preparing your order and will let you know when it ships.</span>
        </div>
      )}

      {order.status === "pending_payment" && (
        <div className="notice stack">
          <strong>Complete your payment to confirm this order.</strong>
          <Countdown until={order.expires_at} onExpire={() => { setWindowClosed(true); setTimeout(refetch, 2000); }} />
          {message && <p className="error">{message}</p>}
          {!windowClosed && (
            <div className="row">
              <button onClick={pay} disabled={paying}>{paying ? "Opening payment…" : `Pay ${formatPrice(order.total)}`}</button>
              <button className="secondary" onClick={cancel} disabled={paying}>Cancel order</button>
            </div>
          )}
        </div>
      )}

      <div className="card stack">
        <h2>Items</h2>
        <ul className="mini-lines">
          {order.items.map((item) => (
            <li key={item.sku}>
              {item.image && <img src={item.image} alt="" />}
              <span className="stack-tight">
                {item.product_id ? <Link to={`/p/${item.product_slug}`}>{item.product_name}</Link> : <span>{item.product_name}</span>}
                <span className="muted small">{item.colour} · {item.size} · {formatPrice(item.unit_price)} × {item.qty}</span>
                {order.status === "delivered" && item.product_id && (
                  <Link to={`/p/${item.product_slug}#reviews`} className="small">Write a review</Link>
                )}
              </span>
              <span>{formatPrice(item.line_total)}</span>
            </li>
          ))}
        </ul>
        <OrderTotals subtotal={order.subtotal} discount={order.discount} discountCode={order.discount_code}
          shipping={order.shipping_fee} total={order.total} />
      </div>

      <div className="grid-2">
        <div className="card stack">
          <h2>Delivery address</h2>
          <AddressLines address={order.address} />
        </div>
        <div className="card stack">
          <h2>History</h2>
          <ol className="timeline">
            {order.events.map((e, i) => (
              <li key={i}>
                <strong>{e.note?.startsWith("Refund issued") ? REFUND_STATUS.refunded : ORDER_STATUS[e.status]}</strong>
                <span className="muted small">{formatDateTime(e.created_at)}{e.note ? ` · ${e.note}` : ""}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}

const STEPS = ["paid", "shipped", "delivered"];

function Progress({ order }) {
  const reached = (status) => order.events.find((e) => e.status === status);
  const current = STEPS.indexOf(order.status);
  const steps = [{ status: "placed", label: "Order placed", at: order.created_at }].concat(
    STEPS.map((s) => ({ status: s, label: ORDER_STATUS[s], at: reached(s)?.created_at }))
  );
  return (
    <ol className="progress" aria-label="Order progress">
      {steps.map((step, i) => {
        const done = i === 0 || i - 1 <= current;
        return (
          <li key={step.status} className={done ? "done" : ""} aria-current={i - 1 === current ? "step" : undefined}>
            <span className="progress-dot" />
            <span className="progress-label">{step.label}</span>
            {done && step.at && <span className="muted small">{formatDateTime(step.at)}</span>}
          </li>
        );
      })}
    </ol>
  );
}

function Countdown({ until, onExpire }) {
  const remaining = () => Math.max(0, Math.floor((new Date(until) - Date.now()) / 1000));
  const [seconds, setSeconds] = useState(remaining);

  useEffect(() => {
    const id = setInterval(() => {
      const s = remaining();
      setSeconds(s);
      if (s === 0) {
        clearInterval(id);
        onExpire();
      }
    }, 1000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [until]);

  if (seconds === 0) return <span className="stock out">The payment window has closed.</span>;
  const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
  const ss = String(seconds % 60).padStart(2, "0");
  return <span>Your items are reserved for <strong>{mm}:{ss}</strong>. Unpaid orders are cancelled automatically.</span>;
}
