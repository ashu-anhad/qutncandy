import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getOrder, orderAction } from "../../api/admin";
import { AddressLines } from "../../components/AddressForm.jsx";
import OrderTotals from "../../components/OrderTotals.jsx";
import { ORDER_STATUS, REFUND_STATUS, formatDateTime, formatPrice } from "../../lib/format";

export default function OrderView() {
  const { number } = useParams();
  const queryClient = useQueryClient();
  const { data: order, isLoading, error } = useQuery({ queryKey: ["admin", "order", number], queryFn: () => getOrder(number) });
  const [actionError, setActionError] = useState("");

  const run = async (action, body) => {
    setActionError("");
    try {
      queryClient.setQueryData(["admin", "order", number], await orderAction(number, action, body));
      queryClient.invalidateQueries({ queryKey: ["admin", "orders"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "stats"] });
      return true;
    } catch (err) {
      setActionError(err.message);
      return false;
    }
  };

  if (isLoading) return <p className="muted">Loading…</p>;
  if (error) return <p className="error">{error.message}</p>;

  return (
    <section className="stack">
      <Link to="/admin/orders" className="muted small">← Orders</Link>
      <div className="section-head">
        <div>
          <h1>Order {order.number}</h1>
          <span className="muted small">Placed {formatDateTime(order.created_at)}</span>
        </div>
        <span className="row">
          <span className={`pill status-${order.status}`}>{ORDER_STATUS[order.status]}</span>
          {order.refund_status && <span className={`pill refund-${order.refund_status}`}>{REFUND_STATUS[order.refund_status]}</span>}
        </span>
      </div>

      {actionError && <p className="error">{actionError}</p>}
      <Actions order={order} run={run} />

      <div className="admin-order-grid">
        <div className="card stack">
          <h2>Items</h2>
          <ul className="mini-lines">
            {order.items.map((item) => (
              <li key={item.sku}>
                {item.image && <img src={item.image} alt="" />}
                <span className="stack-tight">
                  <span>{item.product_name}</span>
                  <span className="muted small">{item.colour} · {item.size} · SKU {item.sku} · {formatPrice(item.unit_price)} × {item.qty}</span>
                </span>
                <span>{formatPrice(item.line_total)}</span>
              </li>
            ))}
          </ul>
          <OrderTotals subtotal={order.subtotal} discount={order.discount} discountCode={order.discount_code}
            shipping={order.shipping_fee} total={order.total} />
        </div>

        <div className="stack">
          <div className="card stack">
            <h2>Customer</h2>
            <div className="address-lines">
              <strong>{order.customer.name}</strong>
              <span>{order.customer.email}</span>
            </div>
            <h3 className="subhead">Ship to</h3>
            <AddressLines address={order.address} />
          </div>
          <div className="card stack">
            <h2>Payment</h2>
            <dl className="kv">
              <dt>Razorpay order</dt><dd>{order.razorpay_order_id ?? "—"}</dd>
              <dt>Payment ID</dt><dd>{order.razorpay_payment_id ?? "—"}</dd>
              {order.courier && <><dt>Courier</dt><dd>{order.courier}</dd><dt>Tracking no.</dt><dd>{order.tracking_no}</dd></>}
            </dl>
          </div>
          <div className="card stack">
            <h2>History</h2>
            <ol className="timeline">
              {order.events.map((e, i) => (
                <li key={i}>
                  <strong>{ORDER_STATUS[e.status]}</strong>
                  <span className="muted small">{formatDateTime(e.created_at)}{e.note ? ` · ${e.note}` : ""}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>
    </section>
  );
}

function Actions({ order, run }) {
  const [ship, setShip] = useState({ courier: "", tracking_no: "" });
  const [refundRef, setRefundRef] = useState("");

  const cancel = () => {
    const reason = prompt(
      order.status === "paid"
        ? "Cancel this paid order? Stock goes back and it moves to 'Refunds due'. Reason (shown in history):"
        : "Cancel this order? Reason (shown in history):"
    );
    if (reason !== null) run("cancel", { note: reason });
  };

  const canCancel = order.status === "paid" || order.status === "pending_payment";
  if (order.status !== "paid" && order.status !== "shipped" && order.refund_status !== "required" && !canCancel) return null;

  return (
    <div className="card stack actions-card">
      <h2>Next step</h2>
      {order.status === "paid" && (
        <form className="row" onSubmit={(e) => { e.preventDefault(); run("ship", ship); }}>
          <input placeholder="Courier (e.g. Delhivery)" value={ship.courier} onChange={(e) => setShip({ ...ship, courier: e.target.value })} required maxLength={100} />
          <input placeholder="Tracking number" value={ship.tracking_no} onChange={(e) => setShip({ ...ship, tracking_no: e.target.value })} required maxLength={100} />
          <button type="submit">Mark as shipped</button>
        </form>
      )}
      {order.status === "shipped" && (
        <div><button onClick={() => confirm("Mark this order as delivered?") && run("deliver")}>Mark as delivered</button></div>
      )}
      {order.refund_status === "required" && (
        <form className="stack" onSubmit={(e) => { e.preventDefault(); run("refunded", { note: refundRef }); }}>
          <span className="muted small">
            Refund {formatPrice(order.total)} for payment <strong>{order.razorpay_payment_id}</strong> in the Razorpay dashboard, then record it here.
          </span>
          <div className="row">
            <input placeholder="Refund ID (e.g. rfnd_…), optional" value={refundRef} onChange={(e) => setRefundRef(e.target.value)} maxLength={400} />
            <button type="submit">Mark as refunded</button>
          </div>
        </form>
      )}
      {canCancel && <div><button className="danger-link" onClick={cancel}>Cancel order</button></div>}
    </div>
  );
}
