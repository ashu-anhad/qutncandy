import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import * as ordersApi from "../../api/orders";
import { formatDate, formatPrice, toPaise } from "../../lib/format";

const EMPTY = { code: "", type: "percent", value: "", min_order: "", max_discount: "", starts_at: "", ends_at: "", usage_limit: "" };

// <input type="date"> gives "YYYY-MM-DD"; treat it as the start/end of that day in India.
const dayStart = (d) => (d ? `${d}T00:00:00+05:30` : null);
const dayEnd = (d) => (d ? `${d}T23:59:59+05:30` : null);

export default function Discounts() {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({ queryKey: ["admin", "discounts"], queryFn: ordersApi.adminListDiscounts });
  const [form, setForm] = useState(EMPTY);
  const [message, setMessage] = useState("");

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["admin", "discounts"] });
  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const create = async (e) => {
    e.preventDefault();
    setMessage("");
    try {
      await ordersApi.createDiscount({
        code: form.code,
        type: form.type,
        value: form.type === "percent" ? Number(form.value) : toPaise(form.value),
        min_order: toPaise(form.min_order) ?? 0,
        max_discount: form.type === "percent" ? toPaise(form.max_discount) : null,
        starts_at: dayStart(form.starts_at),
        ends_at: dayEnd(form.ends_at),
        usage_limit: form.usage_limit ? Number(form.usage_limit) : null,
      });
      setForm(EMPTY);
      refresh();
    } catch (err) {
      setMessage(err.message);
    }
  };

  const toggle = (d) => ordersApi.updateDiscount(d.id, { is_active: !d.is_active }).then(refresh);
  const remove = async (d) => {
    const msg = d.used_count ? `“${d.code}” has been used, so it will be deactivated instead of deleted.` : `Delete “${d.code}”?`;
    if (confirm(msg)) await ordersApi.deleteDiscount(d.id).then(refresh);
  };

  const describe = (d) =>
    d.type === "percent"
      ? `${d.value}% off${d.max_discount ? `, up to ${formatPrice(d.max_discount)}` : ""}`
      : `${formatPrice(d.value)} off`;
  const validity = (d) =>
    d.starts_at || d.ends_at ? `${d.starts_at ? formatDate(d.starts_at) : "Now"} – ${d.ends_at ? formatDate(d.ends_at) : "no end"}` : "Always";

  return (
    <section className="stack">
      <h1>Discounts</h1>
      <form className="card stack" onSubmit={create}>
        <h2>New discount code</h2>
        <div className="grid-3">
          <label>Code<input value={form.code} onChange={set("code")} required pattern="[A-Za-z0-9_\-]{3,40}" placeholder="EID20" /></label>
          <label>
            Type
            <select value={form.type} onChange={set("type")}>
              <option value="percent">Percentage off</option>
              <option value="flat">Flat amount off</option>
            </select>
          </label>
          <label>
            {form.type === "percent" ? "Percent off" : "Amount off (₹)"}
            <input type="number" min="1" max={form.type === "percent" ? 100 : undefined} value={form.value} onChange={set("value")} required />
          </label>
          <label>Minimum order (₹)<input type="number" min="0" value={form.min_order} onChange={set("min_order")} placeholder="0" /></label>
          {form.type === "percent" && (
            <label>Maximum discount (₹)<input type="number" min="1" value={form.max_discount} onChange={set("max_discount")} placeholder="No cap" /></label>
          )}
          <label>Usage limit<input type="number" min="1" value={form.usage_limit} onChange={set("usage_limit")} placeholder="Unlimited" /></label>
          <label>Starts on<input type="date" value={form.starts_at} onChange={set("starts_at")} /></label>
          <label>Ends on<input type="date" value={form.ends_at} onChange={set("ends_at")} /></label>
        </div>
        {message && <p className="error">{message}</p>}
        <div><button type="submit">Create code</button></div>
      </form>

      {error && <p className="error">{error.message}</p>}
      {isLoading && <p className="muted">Loading…</p>}
      {data && (
        <div className="card table-wrap">
          <table className="table">
            <thead>
              <tr><th>Code</th><th>Offer</th><th>Min. order</th><th>Valid</th><th>Used</th><th>Status</th><th></th></tr>
            </thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.id}>
                  <td><strong>{d.code}</strong></td>
                  <td>{describe(d)}</td>
                  <td>{d.min_order ? formatPrice(d.min_order) : "—"}</td>
                  <td>{validity(d)}</td>
                  <td>{d.used_count}{d.usage_limit ? ` / ${d.usage_limit}` : ""}</td>
                  <td><span className={`pill ${d.is_active ? "pill-ok" : ""}`}>{d.is_active ? "Active" : "Off"}</span></td>
                  <td>
                    <span className="row nowrap">
                      <button className="small-btn secondary" onClick={() => toggle(d)}>{d.is_active ? "Turn off" : "Turn on"}</button>
                      <button className="danger-link" onClick={() => remove(d)}>Delete</button>
                    </span>
                  </td>
                </tr>
              ))}
              {data.length === 0 && <tr><td colSpan={7} className="muted">No discount codes yet.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
