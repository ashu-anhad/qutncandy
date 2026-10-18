import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getInventory } from "../../api/admin";
import { updateVariant } from "../../api/catalog";
import Pagination from "../../components/Pagination.jsx";

const FILTERS = [
  { id: "low", label: "Low stock" },
  { id: "out", label: "Out of stock" },
  { id: "all", label: "All variants" },
];
const PAGE_SIZE = 50;

export default function Inventory() {
  const [params, setParams] = useSearchParams();
  const filter = params.get("filter") || "low";
  const q = params.get("q") || "";
  const page = Number(params.get("page") || 1);
  const [search, setSearch] = useState(q);
  const queryClient = useQueryClient();

  const query = { filter, q, page, page_size: PAGE_SIZE };
  const { data, isLoading, error } = useQuery({
    queryKey: ["admin", "inventory", query],
    queryFn: () => getInventory(query),
    placeholderData: keepPreviousData,
  });
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["admin", "inventory"] });
    queryClient.invalidateQueries({ queryKey: ["admin", "stats"] });
  };

  return (
    <section className="stack">
      <h1>Inventory</h1>
      <div className="tab-row">
        {FILTERS.map((f) => (
          <button key={f.id} className={`tab-pill${f.id === filter ? " active" : ""}`} onClick={() => setParams({ filter: f.id, ...(q && { q }) })}>
            {f.label}
          </button>
        ))}
      </div>
      <form className="row" onSubmit={(e) => { e.preventDefault(); setParams({ filter, ...(search && { q: search }) }); }}>
        <input placeholder="Product, SKU or colour" value={search} onChange={(e) => setSearch(e.target.value)} />
        <button className="secondary" type="submit">Search</button>
      </form>
      {data && filter === "low" && <span className="muted small">Showing variants with 1–{data.low_stock_threshold} left.</span>}
      {error && <p className="error">{error.message}</p>}
      {isLoading && <p className="muted">Loading…</p>}
      {data && (
        <div className="card table-wrap">
          <table className="table">
            <thead>
              <tr><th>Product</th><th>Colour</th><th>Size</th><th>SKU</th><th>Stock</th><th>Set stock</th></tr>
            </thead>
            <tbody>
              {data.items.map((v) => <StockRow key={v.id} v={v} threshold={data.low_stock_threshold} onSaved={refresh} />)}
              {data.items.length === 0 && <tr><td colSpan={6} className="muted">Nothing here. 🎉</td></tr>}
            </tbody>
          </table>
        </div>
      )}
      {data && <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onChange={(n) => setParams({ filter, ...(q && { q }), page: n })} />}
    </section>
  );
}

function StockRow({ v, threshold, onSaved }) {
  const [value, setValue] = useState(String(v.stock));
  const [error, setError] = useState("");
  const dirty = value !== String(v.stock) && value !== "";

  const save = async (e) => {
    e.preventDefault();
    try {
      await updateVariant(v.id, { stock: Number(value) });
      setError("");
      onSaved();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <tr className={v.is_active ? "" : "muted"}>
      <td><Link to={`/admin/products/${v.product_id}`}>{v.product_name}</Link>{!v.is_active && <span className="small"> (hidden)</span>}</td>
      <td>{v.colour}</td>
      <td>{v.size}</td>
      <td className="small">{v.sku}</td>
      <td className={v.stock === 0 ? "stock out" : v.stock <= threshold ? "stock low" : ""}>{v.stock}</td>
      <td>
        <form className="row nowrap" onSubmit={save}>
          <input type="number" min="0" className="narrow-input" value={value} onChange={(e) => setValue(e.target.value)} aria-label={`Stock for ${v.sku}`} />
          <button type="submit" className="small-btn" disabled={!dirty}>Save</button>
          {error && <span className="error small">{error}</span>}
        </form>
      </td>
    </tr>
  );
}
