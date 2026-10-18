import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { adminListProducts } from "../../api/catalog";
import Pagination from "../../components/Pagination.jsx";
import Price from "../../components/Price.jsx";

const PAGE_SIZE = 20;

export default function Products() {
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const params = { q, page, page_size: PAGE_SIZE };
  const { data, isLoading, error } = useQuery({
    queryKey: ["admin", "products", params],
    queryFn: () => adminListProducts(params),
    placeholderData: keepPreviousData,
  });

  return (
    <section className="stack">
      <div className="section-head">
        <h1>Products</h1>
        <Link to="/admin/products/new" className="button">New product</Link>
      </div>
      <form className="row" onSubmit={(e) => { e.preventDefault(); setQ(search); setPage(1); }}>
        <input placeholder="Search products" value={search} onChange={(e) => setSearch(e.target.value)} />
        <button className="secondary" type="submit">Search</button>
      </form>
      {error && <p className="error">{error.message}</p>}
      {isLoading && <p className="muted">Loading…</p>}
      {data && (
        <div className="card table-wrap">
          <table className="table">
            <thead>
              <tr><th></th><th>Name</th><th>Category</th><th>Price</th><th>Stock</th><th>Status</th></tr>
            </thead>
            <tbody>
              {data.items.map((p) => (
                <tr key={p.id}>
                  <td>{p.image && <img src={p.image} alt="" className="thumb-sm" />}</td>
                  <td><Link to={`/admin/products/${p.id}`}>{p.name}</Link></td>
                  <td>{p.category.name}</td>
                  <td><Price min={p.min_price} max={p.max_price} className="" /></td>
                  <td className={p.total_stock === 0 ? "stock out" : ""}>{p.total_stock}</td>
                  <td><span className={`pill ${p.is_active ? "pill-ok" : ""}`}>{p.is_active ? "Active" : "Hidden"}</span></td>
                </tr>
              ))}
              {data.items.length === 0 && <tr><td colSpan={6} className="muted">No products found.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
      {data && <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onChange={setPage} />}
    </section>
  );
}
