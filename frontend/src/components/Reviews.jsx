import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { listReviews, myReview, writeReview } from "../api/reviews";
import { useAuth } from "../auth.jsx";
import { formatDate } from "../lib/format";
import Pagination from "./Pagination.jsx";
import Stars, { StarInput } from "./Stars.jsx";

export default function Reviews({ slug }) {
  const { user } = useAuth();
  const location = useLocation();
  const [page, setPage] = useState(1);
  const { data } = useQuery({ queryKey: ["reviews", slug, page], queryFn: () => listReviews(slug, page) });
  const mine = useQuery({ queryKey: ["my-review", slug], queryFn: () => myReview(slug), enabled: !!user });

  return (
    <section className="reviews" id="reviews">
      <h2>Customer reviews</h2>
      {data && data.total > 0 ? (
        <div className="review-summary">
          <div className="stack-tight">
            <span className="review-avg">{data.avg_rating.toFixed(1)}</span>
            <Stars value={data.avg_rating} size={18} />
            <span className="muted small">{data.total} review{data.total > 1 ? "s" : ""}</span>
          </div>
          <ul className="review-bars" aria-label="Rating breakdown">
            {Object.entries(data.distribution).sort(([a], [b]) => b - a).map(([stars, count]) => (
              <li key={stars}>
                <span className="small">{stars}★</span>
                <span className="bar"><span style={{ width: `${(count / data.total) * 100}%` }} /></span>
                <span className="muted small">{count}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="muted">No reviews yet.</p>
      )}

      {!user && <p className="muted small"><Link to={`/login?next=${encodeURIComponent(location.pathname)}`}>Log in</Link> to review a product you've received.</p>}
      {mine.data && (mine.data.can_review || mine.data.review) && <ReviewForm slug={slug} existing={mine.data.review} />}

      <ul className="review-list">
        {data?.items.map((r) => (
          <li key={r.id}>
            <div className="row">
              <Stars value={r.rating} />
              {r.title && <strong>{r.title}</strong>}
            </div>
            {r.comment && <p>{r.comment}</p>}
            <span className="muted small">{r.author} · Verified buyer · {formatDate(r.created_at)}</span>
          </li>
        ))}
      </ul>
      {data && <Pagination page={page} pageSize={data.page_size} total={data.total} onChange={setPage} />}
    </section>
  );
}

const STATUS_NOTE = {
  pending: "Thanks! Your review will appear once it's been checked.",
  approved: "Your review is live.",
  rejected: "Your review wasn't published. You can edit and resubmit it.",
};

function ReviewForm({ slug, existing }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(!existing);
  const [form, setForm] = useState({ rating: 0, title: "", comment: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (existing) setForm({ rating: existing.rating, title: existing.title, comment: existing.comment });
  }, [existing]);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.rating) return setError("Choose a star rating.");
    setBusy(true);
    setError("");
    try {
      queryClient.setQueryData(["my-review", slug], await writeReview(slug, form));
      queryClient.invalidateQueries({ queryKey: ["reviews", slug] });
      queryClient.invalidateQueries({ queryKey: ["product", slug] });
      setEditing(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  if (!editing) {
    return (
      <div className="card stack your-review">
        <div className="row"><strong>Your review</strong><Stars value={existing.rating} /></div>
        <span className="muted small">{STATUS_NOTE[existing.status]}</span>
        <div><button className="small-btn secondary" onClick={() => setEditing(true)}>Edit review</button></div>
      </div>
    );
  }

  return (
    <form className="card stack your-review" onSubmit={submit}>
      <strong>{existing ? "Edit your review" : "Write a review"}</strong>
      <StarInput value={form.rating} onChange={(rating) => setForm({ ...form, rating })} />
      <label>Title (optional)<input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} maxLength={120} /></label>
      <label>Your review (optional)<textarea rows={3} value={form.comment} onChange={(e) => setForm({ ...form, comment: e.target.value })} maxLength={2000} placeholder="Fit, fabric, embroidery…" /></label>
      {error && <p className="error">{error}</p>}
      <div className="row">
        <button type="submit" disabled={busy}>{busy ? "Submitting…" : "Submit review"}</button>
        {existing && <button type="button" className="secondary" onClick={() => setEditing(false)}>Cancel</button>}
      </div>
    </form>
  );
}
