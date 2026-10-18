import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { listNotifications } from "../api/notifications";

export function useNotifications(enabled = true) {
  return useQuery({ queryKey: ["notifications"], queryFn: listNotifications, enabled, refetchInterval: 60_000 });
}

export default function NotificationBell() {
  const { data } = useNotifications();
  const unread = data?.unread ?? 0;
  return (
    <Link to="/notifications" className="bell" aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}>
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
        strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
        <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
      </svg>
      {unread > 0 && <span className="cart-count bell-count">{unread > 9 ? "9+" : unread}</span>}
    </Link>
  );
}
