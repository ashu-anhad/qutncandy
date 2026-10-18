import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { listOrders } from "../../api/admin";
import Pagination from "../../components/Pagination.jsx";
import { ORDER_STATUS, REFUND_STATUS, formatDateTime, formatPrice } from "../../lib/format";

export const TABS = [
  { id: "to-ship", label: "To ship", params: { status: "paid" } },
  { id: "shipped", label: "Shipped", params: { status: "shipped" } },
  { id: "refunds", label: "Refunds due", params: { refund: "required" } },
  { id: "pending", label: "Awaiting payment", params: { status: "pending_payment" } },
  { id: "delivered", label: "Delivered", params: { status: "delivered" } },
  { id: "cancelled", label: "Cancelled", params: { status: "cancelled" } },
  { id: "all", label: "All", params: {} },
];
const PAGE_SIZE = 20;

export default function Orders() {
  const [params, setParams] = useSearchParams();
  const tab = TABS.find((t) => t.id === params.get("tab")) ?? TABS[0];
  const q = params.get("q") || "";
  const page = Number(params.get("page") || 1);
  const [search, setSearch] = useState(q);

  const query = { ...tab.params, q, page, page_size: PAGE_SIZE };
  const { data, isLoading, error } = useQuery({
    queryKey: ["admin", "orders", query],
    queryFn: () => listOrders(query),
    placeholderData: keepPreviousData,
  });

  const go = (changes) => setParams({ tab: tab.id, ...(q && { q }), ...changes });

  return (
    <section className="stack">
      <h1>Orders</h1>
      <div className="tab-row" role="tablist">
        {TABS.map((t) => (
          <button key={t.id} role="tab" aria-selected={t.id === tab.id} className={`tab-pill${t.id === tab.id ? " active" : ""}`}
            onClick={() => setParams({ tab: t.id, ...(q && { q }) })}>
            {t.label}
          </button>
        ))}
      </div>
      <form className="row" onSubmit={(e) => { e.preventDefault(); setParams({ tab: tab.id, ...(search && { q: search }) }); }}>
        <input placeholder="Order number, customer name or email" value={search} onChange={(e) => setSearch(e.target.value)} />
        <button className="secondary" type="submit">Search</button>
      </form>
      {error && <p className="error">{error.message}</p>}
      {isLoading && <p className="muted">Loading…</p>}
      {data && (
        <div className="card table-wrap">
          <table className="table">
            <thead>
              <tr><th>Order</th><th>Placed</th><th>Customer</th><th>Items</th><th>Total</th><th>Status</th></tr>
            </thead>
            <tbody>
              {data.items.map((o) => (
                <tr key={o.number}>
                  <td><Link to={`/admin/orders/${o.number}`}><strong>{o.number}</strong></Link></td>
                  <td className="nowrap">{formatDateTime(o.created_at)}</td>
                  <td>{o.customer_name}<div className="muted small">{o.customer_email}</div></td>
                  <td>{o.item_count}</td>
                  <td>{formatPrice(o.total)}</td>
                  <td>
                    <span className="row nowrap">
                      <span className={`pill status-${o.status}`}>{ORDER_STATUS[o.status]}</span>
                      {o.refund_status && <span className={`pill refund-${o.refund_status}`}>{REFUND_STATUS[o.refund_status]}</span>}
                    </span>
                  </td>
                </tr>
              ))}
              {data.items.length === 0 && <tr><td colSpan={6} className="muted">No orders here.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
      {data && <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onChange={(n) => go({ page: n })} />}
    </section>
  );
}
