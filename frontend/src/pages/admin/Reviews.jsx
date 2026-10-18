import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { adminListReviews, deleteReview, moderateReview } from "../../api/reviews";
import Pagination from "../../components/Pagination.jsx";
import Stars from "../../components/Stars.jsx";
import { formatDateTime } from "../../lib/format";

const TABS = [
  { id: "pending", label: "Waiting for approval" },
  { id: "approved", label: "Approved" },
  { id: "rejected", label: "Rejected" },
];

export default function Reviews() {
  const [params, setParams] = useSearchParams();
  const status = params.get("status") || "pending";
  const page = Number(params.get("page") || 1);
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "reviews", status, page],
    queryFn: () => adminListReviews(status, page),
    placeholderData: keepPreviousData,
  });

  const act = async (fn) => {
    setError("");
    try {
      await fn();
      queryClient.invalidateQueries({ queryKey: ["admin", "reviews"] });
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <section className="stack">
      <h1>Reviews</h1>
      <div className="tab-row">
        {TABS.map((t) => (
          <button key={t.id} className={`tab-pill${t.id === status ? " active" : ""}`} onClick={() => setParams({ status: t.id })}>{t.label}</button>
        ))}
      </div>
      {error && <p className="error">{error}</p>}
      {isLoading && <p className="muted">Loading…</p>}
      {data?.items.length === 0 && <p className="muted">No reviews here.</p>}
      <ul className="admin-review-list">
        {data?.items.map((r) => (
          <li key={r.id} className="card stack">
            <div className="section-head">
              <span className="row"><Stars value={r.rating} /> {r.title && <strong>{r.title}</strong>}</span>
              <span className="muted small">{formatDateTime(r.created_at)}</span>
            </div>
            {r.comment ? <p className="review-comment">{r.comment}</p> : <span className="muted small">No written comment.</span>}
            <span className="small">
              <Link to={`/p/${r.product_slug}`} target="_blank">{r.product_name}</Link>
              <span className="muted"> · by {r.customer_name} ({r.customer_email ?? "no email"}) · verified purchase</span>
            </span>
            <div className="row">
              {r.status !== "approved" && <button className="small-btn" onClick={() => act(() => moderateReview(r.id, "approve"))}>Approve</button>}
              {r.status !== "rejected" && <button className="small-btn secondary" onClick={() => act(() => moderateReview(r.id, "reject"))}>Reject</button>}
              <button className="danger-link" onClick={() => confirm("Delete this review permanently?") && act(() => deleteReview(r.id))}>Delete</button>
            </div>
          </li>
        ))}
      </ul>
      {data && <Pagination page={page} pageSize={data.page_size} total={data.total} onChange={(n) => setParams({ status, page: n })} />}
    </section>
  );
}
