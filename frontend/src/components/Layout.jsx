import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { useCart } from "../cart.jsx";
import Brand, { RuleSpark } from "./Brand.jsx";
import NotificationBell from "./NotificationBell.jsx";

export default function Layout() {
  const { user } = useAuth();
  const { count } = useCart();
  const navigate = useNavigate();
  const [q, setQ] = useState("");

  const search = (e) => {
    e.preventDefault();
    navigate(q.trim() ? `/products?q=${encodeURIComponent(q.trim())}` : "/products");
  };

  return (
    <div className="page">
      <header className="site-header">
        <div className="container header-inner">
          <Brand />
          <form className="header-search" onSubmit={search} role="search">
            <input type="search" placeholder="Search kurtas, sarees…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search products" />
          </form>
          <nav className="nav">
            <NavLink to="/products">Shop</NavLink>
            {user?.role === "admin" && <NavLink to="/admin">Admin</NavLink>}
            {user ? <NavLink to="/account">{user.name.split(" ")[0]}</NavLink> : <NavLink to="/login">Login</NavLink>}
            {user && <NotificationBell />}
            <NavLink to="/cart" className="cart-link" aria-label={`Cart, ${count} items`}>
              Cart{count > 0 && <span className="cart-count">{count}</span>}
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="container content">
        <Outlet />
      </main>
      <footer className="site-footer">
        <div className="container footer-inner">
          <img src="/brand/mark.png" alt="" className="footer-mark" width="56" height="56" />
          <RuleSpark />
          <span className="tagline">Wear your confidence</span>
          <span className="muted small">Handcrafted Lucknowi chikankari in pure cotton · © {new Date().getFullYear()} QutnCandy</span>
        </div>
      </footer>
    </div>
  );
}
