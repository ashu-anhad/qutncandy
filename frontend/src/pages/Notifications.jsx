import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { markAllRead, markRead } from "../api/notifications";
import { useNotifications } from "../components/NotificationBell.jsx";
import { formatDateTime } from "../lib/format";

export default function Notifications() {
  const { data, isLoading, error } = useNotifications();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["notifications"] });

  const open = async (n) => {
    if (!n.read_at) await markRead(n.id).then(refresh);
    if (n.link) navigate(n.link);
  };

  return (
    <section className="stack narrow-wide">
      <div className="section-head">
        <h1>Notifications</h1>
        {data?.unread > 0 && <button className="secondary" onClick={() => markAllRead().then(refresh)}>Mark all as read</button>}
      </div>
      {isLoading && <p className="muted">Loading…</p>}
      {error && <p className="error">{error.message}</p>}
      {data?.items.length === 0 && <p className="muted">No notifications yet. Order updates will appear here.</p>}
      <ul className="notification-list">
        {data?.items.map((n) => (
          <li key={n.id}>
            <button type="button" className={`notification card${n.read_at ? "" : " unread"}`} onClick={() => open(n)}>
              <span className="stack-tight">
                <strong>{n.title}</strong>
                <span>{n.body}</span>
                <span className="muted small">{formatDateTime(n.created_at)}</span>
              </span>
              {!n.read_at && <span className="dot" aria-label="Unread" />}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
