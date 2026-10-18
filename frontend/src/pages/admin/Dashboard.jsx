import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getStats } from "../../api/admin";
import { listUsers } from "../../api/auth";
import { formatPrice } from "../../lib/format";

export default function Dashboard() {
  const stats = useQuery({ queryKey: ["admin", "stats"], queryFn: getStats, refetchInterval: 60_000 });
  const users = useQuery({ queryKey: ["admin", "users"], queryFn: () => listUsers() });
  const s = stats.data;

  const tiles = s && [
    { label: "Orders to ship", value: s.to_ship, to: "/admin/orders?tab=to-ship", urgent: s.to_ship > 0 },
    { label: "Refunds due", value: s.refunds_required, to: "/admin/orders?tab=refunds", urgent: s.refunds_required > 0 },
    { label: "Low stock", value: s.low_stock, to: "/admin/inventory?filter=low" },
    { label: "Out of stock", value: s.out_of_stock, to: "/admin/inventory?filter=out" },
    { label: "Shipped, not delivered", value: s.shipped, to: "/admin/orders?tab=shipped" },
    { label: "Awaiting payment", value: s.awaiting_payment, to: "/admin/orders?tab=pending" },
  ];

  return (
    <section className="stack">
      <h1>Dashboard</h1>
      {stats.error && <p className="error">{stats.error.message}</p>}
      {s && (
        <>
          <p className="muted">Last 24 hours: <strong>{s.orders_24h}</strong> paid order{s.orders_24h === 1 ? "" : "s"}, <strong>{formatPrice(s.revenue_24h)}</strong> revenue.</p>
          <div className="stat-grid">
            {tiles.map((t) => (
              <Link key={t.label} to={t.to} className={`stat card${t.urgent ? " urgent" : ""}`}>
                <span className="stat-value">{t.value}</span>
                <span className="muted">{t.label}</span>
              </Link>
            ))}
          </div>
        </>
      )}

      <div className="card">
        <h2>Accounts {users.data && <span className="muted">({users.data.total})</span>}</h2>
        {users.error && <p className="error">{users.error.message}</p>}
        {users.data && (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Joined</th></tr></thead>
              <tbody>
                {users.data.items.map((u) => (
                  <tr key={u.id}>
                    <td>{u.name}</td><td>{u.email}</td><td>{u.role}</td>
                    <td>{new Date(u.created_at).toLocaleDateString("en-IN")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
