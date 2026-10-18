import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import * as catalog from "../../api/catalog";
import { categoryTree, toPaise, toRupees } from "../../lib/format";

const EMPTY = { name: "", category_id: "", base_price: "", fabric: "Pure cotton", description: "", is_active: true, slug: "" };

export default function ProductEdit() {
  const { id } = useParams();
  const isNew = id === "new";
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const categories = useQuery({ queryKey: ["categories"], queryFn: catalog.listCategories });
  const product = useQuery({
    queryKey: ["admin", "product", id],
    queryFn: () => catalog.adminGetProduct(id),
    enabled: !isNew,
  });

  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (product.data) {
      const p = product.data;
      setForm({ name: p.name, category_id: String(p.category.id), base_price: toRupees(p.base_price), fabric: p.fabric,
        description: p.description, is_active: p.is_active, slug: p.slug });
    }
  }, [product.data]);

  const set = (field) => (e) => {
    setSaved(false);
    setForm({ ...form, [field]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  };

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["admin", "products"] });
    queryClient.invalidateQueries({ queryKey: ["products"] });
    return product.refetch();
  };

  const save = async (e) => {
    e.preventDefault();
    setError("");
    const payload = {
      name: form.name, category_id: Number(form.category_id), base_price: toPaise(form.base_price),
      fabric: form.fabric, description: form.description, is_active: form.is_active,
    };
    try {
      if (isNew) {
        const created = await catalog.createProduct(payload);
        queryClient.invalidateQueries({ queryKey: ["admin", "products"] });
        navigate(`/admin/products/${created.id}`, { replace: true });
      } else {
        await catalog.updateProduct(id, { ...payload, slug: form.slug });
        await refresh();
        setSaved(true);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const remove = async () => {
    if (!confirm(`Delete “${form.name}”? This removes its variants and images.`)) return;
    try {
      await catalog.deleteProduct(id);
      queryClient.invalidateQueries({ queryKey: ["admin", "products"] });
      navigate("/admin/products");
    } catch (err) {
      setError(err.message);
    }
  };

  if (!isNew && product.isLoading) return <p className="muted">Loading…</p>;
  if (product.error) return <p className="error">{product.error.message}</p>;

  return (
    <section className="stack">
      <Link to="/admin/products" className="muted small">← Products</Link>
      <div className="section-head">
        <h1>{isNew ? "New product" : form.name || "Product"}</h1>
        {!isNew && product.data?.is_active && <Link to={`/p/${product.data.slug}`} target="_blank">View in store ↗</Link>}
      </div>

      <form className="card stack" onSubmit={save}>
        <div className="grid-2">
          <label>Name<input value={form.name} onChange={set("name")} required maxLength={200} /></label>
          <label>
            Category
            <select value={form.category_id} onChange={set("category_id")} required>
              <option value="" disabled>Choose…</option>
              {categoryTree(categories.data).map((root) => (
                <optgroup key={root.id} label={root.name}>
                  <option value={root.id}>{root.name}</option>
                  {root.children.map((c) => <option key={c.id} value={c.id}>{root.name} › {c.name}</option>)}
                </optgroup>
              ))}
            </select>
          </label>
          <label>Base price (₹)<input type="number" min="0" step="1" value={form.base_price} onChange={set("base_price")} required /></label>
          <label>Fabric<input value={form.fabric} onChange={set("fabric")} maxLength={100} /></label>
          {!isNew && <label>URL slug<input value={form.slug} onChange={set("slug")} required maxLength={220} /></label>}
        </div>
        <label>Description<textarea rows={4} value={form.description} onChange={set("description")} /></label>
        <label className="check">
          <input type="checkbox" checked={form.is_active} onChange={set("is_active")} /> Visible in store
        </label>
        {error && <p className="error">{error}</p>}
        <div className="row">
          <button type="submit">{isNew ? "Create product" : "Save changes"}</button>
          {saved && <span className="muted">Saved</span>}
          {!isNew && <button type="button" className="danger-link" onClick={remove}>Delete product</button>}
        </div>
      </form>

      {isNew ? (
        <p className="muted">Create the product first, then add sizes, colours and images.</p>
      ) : (
        product.data && (
          <>
            <Variants product={product.data} onChange={refresh} />
            <Images product={product.data} onChange={refresh} />
          </>
        )
      )}
    </section>
  );
}

function Variants({ product, onChange }) {
  const [bulk, setBulk] = useState({ sizes: "S, M, L, XL", colours: "", stock: "5" });
  const [error, setError] = useState("");

  const addCombos = async (e) => {
    e.preventDefault();
    setError("");
    const split = (s) => s.split(",").map((x) => x.trim()).filter(Boolean);
    const existing = new Set(product.variants.map((v) => `${v.size}|${v.colour.toLowerCase()}`));
    const combos = split(bulk.colours).flatMap((colour) => split(bulk.sizes).map((size) => ({ size, colour })))
      .filter((c) => !existing.has(`${c.size}|${c.colour.toLowerCase()}`));
    if (!combos.length) return setError("All of those size/colour combinations already exist.");
    try {
      for (const c of combos) await catalog.createVariant(product.id, { ...c, stock: Number(bulk.stock || 0) });
      setBulk({ ...bulk, colours: "" });
    } catch (err) {
      setError(err.message);
    }
    onChange();
  };

  return (
    <div className="card stack">
      <h2>Variants <span className="muted">({product.variants.length})</span></h2>
      {product.variants.length > 0 && (
        <div className="table-wrap">
          <table className="table variants-table">
            <thead>
              <tr><th>Colour</th><th>Size</th><th>SKU</th><th>Price override (₹)</th><th>Stock</th><th>Active</th><th></th></tr>
            </thead>
            <tbody>
              {product.variants.map((v) => <VariantRow key={v.id} variant={v} basePrice={product.base_price} onChange={onChange} />)}
            </tbody>
          </table>
        </div>
      )}
      <form className="bulk-add" onSubmit={addCombos}>
        <strong>Add variants</strong>
        <div className="grid-3">
          <label>Colours (comma-separated)<input value={bulk.colours} onChange={(e) => setBulk({ ...bulk, colours: e.target.value })} placeholder="White, Mint" required /></label>
          <label>Sizes (comma-separated)<input value={bulk.sizes} onChange={(e) => setBulk({ ...bulk, sizes: e.target.value })} required /></label>
          <label>Starting stock<input type="number" min="0" value={bulk.stock} onChange={(e) => setBulk({ ...bulk, stock: e.target.value })} /></label>
        </div>
        {error && <p className="error">{error}</p>}
        <div><button type="submit" className="secondary">Add combinations</button></div>
      </form>
    </div>
  );
}

function VariantRow({ variant, basePrice, onChange }) {
  const initial = { sku: variant.sku, price: toRupees(variant.price), stock: String(variant.stock), is_active: variant.is_active };
  const [row, setRow] = useState(initial);
  const [error, setError] = useState("");
  const dirty = JSON.stringify(row) !== JSON.stringify(initial);

  const save = async () => {
    setError("");
    try {
      await catalog.updateVariant(variant.id, { sku: row.sku, price: toPaise(row.price), stock: Number(row.stock), is_active: row.is_active });
      onChange();
    } catch (err) {
      setError(err.message);
    }
  };
  const remove = async () => {
    if (!confirm(`Delete ${variant.colour} / ${variant.size}?`)) return;
    await catalog.deleteVariant(variant.id).catch((err) => setError(err.message));
    onChange();
  };

  return (
    <tr>
      <td>{variant.colour}</td>
      <td>{variant.size}</td>
      <td><input value={row.sku} onChange={(e) => setRow({ ...row, sku: e.target.value })} /></td>
      <td>
        <input type="number" min="0" placeholder={toRupees(basePrice)} value={row.price}
          onChange={(e) => setRow({ ...row, price: e.target.value })} />
      </td>
      <td><input type="number" min="0" className="narrow-input" value={row.stock} onChange={(e) => setRow({ ...row, stock: e.target.value })} /></td>
      <td><input type="checkbox" checked={row.is_active} onChange={(e) => setRow({ ...row, is_active: e.target.checked })} /></td>
      <td>
        <span className="row nowrap">
          <button type="button" className="small-btn" disabled={!dirty} onClick={save}>Save</button>
          <button type="button" className="danger-link" onClick={remove}>Delete</button>
          {error && <span className="error small">{error}</span>}
        </span>
      </td>
    </tr>
  );
}

function Images({ product, onChange }) {
  const [colour, setColour] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const upload = async (e) => {
    const files = [...e.target.files];
    e.target.value = "";
    if (!files.length) return;
    setBusy(true);
    setError("");
    try {
      for (const f of files) await catalog.uploadImage(product.id, f, colour);
    } catch (err) {
      setError(err.message);
    }
    setBusy(false);
    onChange();
  };

  const remove = async (img) => {
    if (!confirm("Delete this image?")) return;
    await catalog.deleteImage(img.id).catch((err) => setError(err.message));
    onChange();
  };

  return (
    <div className="card stack">
      <h2>Images <span className="muted">({product.images.length})</span></h2>
      <div className="image-grid">
        {product.images.map((img) => (
          <figure key={img.id} className="image-tile">
            <img src={img.url} alt="" />
            <figcaption className="row">
              <span className="muted small">{img.colour ?? "All colours"}</span>
              <button type="button" className="danger-link" onClick={() => remove(img)}>Delete</button>
            </figcaption>
          </figure>
        ))}
      </div>
      <div className="row">
        <select value={colour} onChange={(e) => setColour(e.target.value)}>
          <option value="">For all colours</option>
          {product.colours.map((c) => <option key={c} value={c}>For {c}</option>)}
        </select>
        <label className="button secondary file-btn">
          {busy ? "Uploading…" : "Upload images"}
          <input type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={upload} disabled={busy} hidden />
        </label>
        <span className="muted small">JPEG, PNG or WebP, up to 5 MB</span>
      </div>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
