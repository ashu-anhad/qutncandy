import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { getFilters, listCategories, listProducts } from "../api/catalog";
import Pagination from "../components/Pagination.jsx";
import ProductCard from "../components/ProductCard.jsx";
import Swatch from "../components/Swatch.jsx";
import { categoryTree } from "../lib/format";

const PAGE_SIZE = 24;
const PRICE_BANDS = [
  { id: "u1500", label: "Under ₹1,500", max: 150000 },
  { id: "1500-3000", label: "₹1,500 – ₹3,000", min: 150000, max: 300000 },
  { id: "3000-5000", label: "₹3,000 – ₹5,000", min: 300000, max: 500000 },
  { id: "o5000", label: "Above ₹5,000", min: 500000 },
];
const SORTS = [
  { id: "newest", label: "Newest" },
  { id: "price_asc", label: "Price: low to high" },
  { id: "price_desc", label: "Price: high to low" },
  { id: "rating", label: "Top rated" },
];

export default function ProductList() {
  const { slug } = useParams();
  const [params, setParams] = useSearchParams();
  // Filters start open on desktop and collapsed on phones.
  const [filtersOpen] = useState(() => window.matchMedia("(min-width: 861px)").matches);

  const q = params.get("q") || "";
  const sizes = params.getAll("size");
  const colours = params.getAll("colour");
  const band = PRICE_BANDS.find((b) => b.id === params.get("price"));
  const sort = params.get("sort") || "newest";
  const page = Number(params.get("page") || 1);

  const query = {
    q, category: slug, size: sizes, colour: colours, sort, page, page_size: PAGE_SIZE,
    min_price: band?.min, max_price: band?.max,
  };
  const products = useQuery({ queryKey: ["products", query], queryFn: () => listProducts(query), placeholderData: keepPreviousData });
  const filters = useQuery({ queryKey: ["filters"], queryFn: getFilters });
  const categories = useQuery({ queryKey: ["categories"], queryFn: listCategories });

  const current = categories.data?.find((c) => c.slug === slug);
  const title = q ? `Results for “${q}”` : current?.name ?? "All products";

  // Every filter change resets to page 1.
  const update = (mutate) => {
    const next = new URLSearchParams(params);
    mutate(next);
    next.delete("page");
    setParams(next);
  };
  const toggle = (key, value) =>
    update((p) => {
      const values = p.getAll(key);
      p.delete(key);
      (values.includes(value) ? values.filter((v) => v !== value) : [...values, value]).forEach((v) => p.append(key, v));
    });
  const setPage = (n) => {
    const next = new URLSearchParams(params);
    next.set("page", n);
    setParams(next);
    window.scrollTo(0, 0);
  };
  const hasFilters = sizes.length || colours.length || band || q;

  return (
    <div className="listing">
      <aside className="filters">
        <details open={filtersOpen}>
          <summary>Filters</summary>
          <div className="filter-group">
            <h3>Category</h3>
            <Link to={{ pathname: "/products", search: q ? `?q=${encodeURIComponent(q)}` : "" }} className={!slug ? "active" : ""}>All</Link>
            {categoryTree(categories.data).map((root) => (
              <div key={root.id} className="filter-tree">
                <Link to={`/c/${root.slug}`} className={slug === root.slug ? "active" : ""}>{root.name}</Link>
                {root.children.map((c) => (
                  <Link key={c.id} to={`/c/${c.slug}`} className={`child${slug === c.slug ? " active" : ""}`}>{c.name}</Link>
                ))}
              </div>
            ))}
          </div>

          <div className="filter-group">
            <h3>Price</h3>
            {PRICE_BANDS.map((b) => (
              <label key={b.id} className="check">
                <input
                  type="radio"
                  name="price"
                  checked={band?.id === b.id}
                  onChange={() => update((p) => p.set("price", b.id))}
                />
                {b.label}
              </label>
            ))}
          </div>

          {filters.data && (
            <>
              <div className="filter-group">
                <h3>Size</h3>
                <div className="chips">
                  {filters.data.sizes.map((s) => (
                    <button key={s} type="button" className={`chip${sizes.includes(s) ? " selected" : ""}`} onClick={() => toggle("size", s)}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
              <div className="filter-group">
                <h3>Colour</h3>
                {filters.data.colours.map((c) => (
                  <label key={c} className="check">
                    <input type="checkbox" checked={colours.includes(c)} onChange={() => toggle("colour", c)} />
                    <Swatch colour={c} /> {c}
                  </label>
                ))}
              </div>
            </>
          )}
          {hasFilters ? (
            <button className="secondary" onClick={() => setParams(sort !== "newest" ? { sort } : {})}>Clear filters</button>
          ) : null}
        </details>
      </aside>

      <section className="listing-main">
        <div className="section-head">
          <div>
            <h1>{title}</h1>
            {products.data && <span className="muted small">{products.data.total} products</span>}
          </div>
          <label className="sort">
            Sort
            <select value={sort} onChange={(e) => update((p) => p.set("sort", e.target.value))}>
              {SORTS.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
            </select>
          </label>
        </div>

        {products.error && <p className="error">{products.error.message}</p>}
        {products.isLoading && <p className="muted">Loading…</p>}
        {products.data?.items.length === 0 && <p className="muted">No products match these filters.</p>}
        <div className="product-grid">
          {products.data?.items.map((p) => <ProductCard key={p.id} product={p} />)}
        </div>
        {products.data && <Pagination page={page} pageSize={PAGE_SIZE} total={products.data.total} onChange={setPage} />}
      </section>
    </div>
  );
}
