import { Link, NavLink, Outlet } from "react-router-dom";
import { Wordmark } from "./Brand.jsx";

export default function AdminLayout() {
  return (
    <div className="admin">
      <aside className="admin-sidebar">
        <Link to="/admin" className="admin-brand">
          <span className="row"><img src="/brand/mark.png" alt="" width="32" height="32" /><Wordmark /></span>
          <span className="muted small">Admin</span>
        </Link>
        <nav>
          <NavLink to="/admin" end>Dashboard</NavLink>
          <NavLink to="/admin/orders">Orders</NavLink>
          <NavLink to="/admin/products">Products</NavLink>
          <NavLink to="/admin/inventory">Inventory</NavLink>
          <NavLink to="/admin/categories">Categories</NavLink>
          <NavLink to="/admin/discounts">Discounts</NavLink>
          <NavLink to="/admin/reviews">Reviews</NavLink>
          <NavLink to="/admin/reports">Reports</NavLink>
        </nav>
        <Link to="/" className="muted small">← Back to store</Link>
      </aside>
      <main className="admin-content">
        <Outlet />
      </main>
    </div>
  );
}
