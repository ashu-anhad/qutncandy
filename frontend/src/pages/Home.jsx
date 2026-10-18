import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { listCategories, listProducts } from "../api/catalog";
import { RuleSpark } from "../components/Brand.jsx";
import ProductCard from "../components/ProductCard.jsx";
import { categoryTree } from "../lib/format";

export default function Home() {
  const categories = useQuery({ queryKey: ["categories"], queryFn: listCategories });
  const latest = useQuery({ queryKey: ["products", { sort: "newest", page_size: 8 }], queryFn: () => listProducts({ page_size: 8 }) });

  return (
    <>
      <section className="hero">
        <div>
          <span className="eyebrow">Wear your confidence</span>
          <h1>Handcrafted chikankari, in pure cotton</h1>
          <RuleSpark className="left" />
          <p className="muted">Kurtas, sarees and dupattas, hand-embroidered by artisans in Lucknow.</p>
          <Link to="/products" className="button">Shop the collection</Link>
        </div>
        <img src="/brand/logo-full.png" alt="QutnCandy — Wear your confidence" className="hero-logo" width="1026" height="804" />
      </section>

      {categories.data && (
        <section className="section">
          <h2>Shop by category</h2>
          <div className="category-tiles">
            {categoryTree(categories.data).flatMap((root) =>
              (root.children.length ? root.children : [root]).map((c) => (
                <Link key={c.id} to={`/c/${c.slug}`} className="category-tile">
                  <span className="muted small">{root.id !== c.id ? root.name : ""}</span>
                  <span>{c.name}</span>
                </Link>
              ))
            )}
          </div>
        </section>
      )}

      <section className="section">
        <div className="section-head">
          <h2>New arrivals</h2>
          <Link to="/products">View all</Link>
        </div>
        {latest.isLoading && <p className="muted">Loading…</p>}
        {latest.error && <p className="error">{latest.error.message}</p>}
        <div className="product-grid">
          {latest.data?.items.map((p) => <ProductCard key={p.id} product={p} />)}
        </div>
      </section>
    </>
  );
}
