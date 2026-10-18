import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { listOrders } from "../api/orders";
import Pagination from "../components/Pagination.jsx";
import { ORDER_STATUS, formatDate, formatPrice } from "../lib/format";

export default function Orders() {
  const [page, setPage] = useState(1);
  const { data, isLoading, error } = useQuery({ queryKey: ["orders", page], queryFn: () => listOrders(page) });

  return (
    <section className="stack narrow-wide">
      <h1>My orders</h1>
      {isLoading && <p className="muted">Loading…</p>}
      {error && <p className="error">{error.message}</p>}
      {data?.items.length === 0 && (
        <p className="muted">You haven't placed any orders yet. <Link to="/products">Start shopping</Link></p>
      )}
      <ul className="order-list">
        {data?.items.map((o) => (
          <li key={o.number}>
            <Link to={`/orders/${o.number}`} className="order-row card">
              {o.image ? <img src={o.image} alt="" /> : <div className="img-placeholder" />}
              <span className="stack-tight">
                <strong>{o.number}</strong>
                <span className="muted small">{formatDate(o.created_at)} · {o.item_count} item{o.item_count > 1 ? "s" : ""}</span>
              </span>
              <span className={`pill status-${o.status}`}>{ORDER_STATUS[o.status]}</span>
              <strong>{formatPrice(o.total)}</strong>
            </Link>
          </li>
        ))}
      </ul>
      {data && <Pagination page={page} pageSize={data.page_size} total={data.total} onChange={setPage} />}
    </section>
  );
}
