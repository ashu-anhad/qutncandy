import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import * as catalog from "../../api/catalog";
import { categoryTree } from "../../lib/format";

export default function Categories() {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({ queryKey: ["categories"], queryFn: catalog.listCategories });
  const [form, setForm] = useState({ name: "", parent_id: "" });
  const [message, setMessage] = useState("");

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["categories"] });
  const run = async (fn) => {
    setMessage("");
    try {
      await fn();
      refresh();
    } catch (err) {
      setMessage(err.message);
    }
  };

  const add = (e) => {
    e.preventDefault();
    run(async () => {
      await catalog.createCategory({ name: form.name, parent_id: form.parent_id ? Number(form.parent_id) : null });
      setForm({ name: "", parent_id: form.parent_id });
    });
  };
  const rename = (c) => {
    const name = prompt("Rename category", c.name);
    if (name && name !== c.name) run(() => catalog.updateCategory(c.id, { name }));
  };
  const remove = (c) => confirm(`Delete “${c.name}”?`) && run(() => catalog.deleteCategory(c.id));

  const tree = categoryTree(data);

  return (
    <section className="stack narrow-wide">
      <h1>Categories</h1>
      {error && <p className="error">{error.message}</p>}
      {message && <p className="error">{message}</p>}
      <form className="card row" onSubmit={add}>
        <input placeholder="New category name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        <select value={form.parent_id} onChange={(e) => setForm({ ...form, parent_id: e.target.value })}>
          <option value="">Top level</option>
          {tree.map((r) => <option key={r.id} value={r.id}>Inside {r.name}</option>)}
        </select>
        <button type="submit">Add</button>
      </form>
      {isLoading && <p className="muted">Loading…</p>}
      <div className="card">
        <ul className="cat-list">
          {tree.map((root) => (
            <li key={root.id}>
              <CategoryLine c={root} onRename={rename} onDelete={remove} />
              {root.children.length > 0 && (
                <ul>
                  {root.children.map((c) => <li key={c.id}><CategoryLine c={c} onRename={rename} onDelete={remove} /></li>)}
                </ul>
              )}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function CategoryLine({ c, onRename, onDelete }) {
  return (
    <div className="cat-line">
      <span>{c.name} <span className="muted small">/{c.slug}</span></span>
      <span className="row">
        <button type="button" className="small-btn secondary" onClick={() => onRename(c)}>Rename</button>
        <button type="button" className="danger-link" onClick={() => onDelete(c)}>Delete</button>
      </span>
    </div>
  );
}
