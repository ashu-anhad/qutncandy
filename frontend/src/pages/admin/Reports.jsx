import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { discountsReport, downloadReport, salesReport, topProductsReport } from "../../api/admin";
import BarChart from "../../components/BarChart.jsx";
import { formatPrice } from "../../lib/format";

const compact = new Intl.NumberFormat("en-IN", { notation: "compact", maximumFractionDigits: 1 });
const tickRupees = (paise) => `₹${compact.format(paise / 100)}`;

// Dates are handled as India calendar days (YYYY-MM-DD).
const isoDay = (d) => new Date(d.getTime() + 5.5 * 3600e3).toISOString().slice(0, 10);
const daysAgo = (n) => isoDay(new Date(Date.now() - n * 86400e3));
const PRESETS = [
  { id: "7", label: "7 days", range: () => [daysAgo(6), daysAgo(0)] },
  { id: "30", label: "30 days", range: () => [daysAgo(29), daysAgo(0)] },
  { id: "90", label: "90 days", range: () => [daysAgo(89), daysAgo(0)] },
  { id: "365", label: "12 months", range: () => [daysAgo(364), daysAgo(0)], group: "month" },
];

const periodLabel = (p, group) =>
  group === "month"
    ? new Date(`${p}-01T00:00:00`).toLocaleDateString("en-IN", { month: "short", year: "numeric" })
    : new Date(`${p}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short" });

export default function Reports() {
  const [preset, setPreset] = useState("30");
  const [[start, end], setRange] = useState(PRESETS[1].range());
  const [group, setGroup] = useState("day");
  const [showTable, setShowTable] = useState(false);
  const [error, setError] = useState("");

  const params = { start, end };
  const sales = useQuery({ queryKey: ["admin", "report", "sales", start, end, group], queryFn: () => salesReport({ ...params, group }) });
  const top = useQuery({ queryKey: ["admin", "report", "top", start, end], queryFn: () => topProductsReport(params) });
  const codes = useQuery({ queryKey: ["admin", "report", "discounts", start, end], queryFn: () => discountsReport(params) });

  const choose = (p) => {
    setPreset(p.id);
    setRange(p.range());
    setGroup(p.group ?? "day");
  };
  const csv = (name, extra = {}) => downloadReport(name, { ...params, ...extra }).catch((e) => setError(e.message));

  const s = sales.data;
  const chartData = s?.rows.map((r) => ({
    label: periodLabel(r.period, s.group), value: r.revenue, orders: r.orders, avg: r.avg_order,
  }));

  return (
    <section className="stack">
      <div className="section-head">
        <h1>Reports</h1>
        <span className="muted small">Sales = paid, shipped and delivered orders (India time)</span>
      </div>

      <div className="filter-bar">
        <div className="tab-row">
          {PRESETS.map((p) => (
            <button key={p.id} className={`tab-pill${preset === p.id ? " active" : ""}`} onClick={() => choose(p)}>{p.label}</button>
          ))}
        </div>
        <label className="inline-field">From<input type="date" value={start} max={end} onChange={(e) => { setPreset(""); setRange([e.target.value, end]); }} /></label>
        <label className="inline-field">To<input type="date" value={end} min={start} onChange={(e) => { setPreset(""); setRange([start, e.target.value]); }} /></label>
        <label className="inline-field">
          Group by
          <select value={group} onChange={(e) => setGroup(e.target.value)}>
            <option value="day">Day</option>
            <option value="month">Month</option>
          </select>
        </label>
      </div>
      {error && <p className="error">{error}</p>}
      {sales.error && <p className="error">{sales.error.message}</p>}

      {s && (
        <>
          <div className="stat-grid">
            <Tile label="Revenue" value={formatPrice(s.totals.revenue)} />
            <Tile label="Orders" value={s.totals.orders.toLocaleString("en-IN")} />
            <Tile label="Average order value" value={formatPrice(s.totals.avg_order)} />
            <Tile label="Discounts given" value={formatPrice(s.totals.discount)} />
          </div>

          <div className="card stack">
            <div className="section-head">
              <div>
                <h2>Revenue by {s.group}</h2>
                <span className="muted small">{periodLabel(s.start, "day")} – {periodLabel(s.end, "day")}</span>
              </div>
              <span className="row">
                <button className="small-btn secondary" onClick={() => setShowTable(!showTable)}>{showTable ? "Hide table" : "Show table"}</button>
                <button className="small-btn secondary" onClick={() => csv("sales", { group })}>Download CSV</button>
              </span>
            </div>
            {s.totals.orders === 0 && <p className="muted">No sales in this period yet.</p>}
            {s.totals.orders > 0 && <BarChart
              data={chartData}
              ariaLabel={`Revenue by ${s.group}`}
              formatValue={formatPrice}
              formatTick={tickRupees}
              renderTooltip={(d) => (
                <>
                  <strong>{d.label}</strong>
                  <span>{formatPrice(d.value)}</span>
                  <span className="muted">{d.orders} order{d.orders === 1 ? "" : "s"}{d.orders ? ` · avg ${formatPrice(d.avg)}` : ""}</span>
                </>
              )}
            />}
            {showTable && (
              <div className="table-wrap">
                <table className="table">
                  <thead><tr><th>{s.group === "month" ? "Month" : "Date"}</th><th>Orders</th><th>Revenue</th><th>Discounts</th><th>Avg order</th></tr></thead>
                  <tbody>
                    {s.rows.slice().reverse().map((r) => (
                      <tr key={r.period}>
                        <td>{periodLabel(r.period, s.group)}</td><td>{r.orders}</td><td>{formatPrice(r.revenue)}</td>
                        <td>{formatPrice(r.discount)}</td><td>{r.orders ? formatPrice(r.avg_order) : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      <div className="grid-2 align-start">
        <div className="card stack">
          <div className="section-head">
            <h2>Top products</h2>
            <button className="small-btn secondary" onClick={() => csv("top-products")}>Download CSV</button>
          </div>
          {top.data?.length === 0 && <p className="muted">No sales in this period yet.</p>}
          {top.data?.length > 0 && (
            <table className="table">
              <thead><tr><th>Product</th><th>Units</th><th>Sales</th></tr></thead>
              <tbody>
                {top.data.map((t) => (
                  <tr key={t.slug + t.product}>
                    <td><Link to={`/p/${t.slug}`} target="_blank">{t.product}</Link></td><td>{t.units}</td><td>{formatPrice(t.sales)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <span className="muted small">Sales are before order-level discounts.</span>
        </div>
        <div className="card stack">
          <div className="section-head">
            <h2>Discount codes</h2>
            <button className="small-btn secondary" onClick={() => csv("discounts")}>Download CSV</button>
          </div>
          {codes.data?.length === 0 && <p className="muted">No codes used in this period.</p>}
          {codes.data?.length > 0 && (
            <table className="table">
              <thead><tr><th>Code</th><th>Orders</th><th>Discount given</th><th>Revenue</th></tr></thead>
              <tbody>
                {codes.data.map((c) => (
                  <tr key={c.code}><td><strong>{c.code}</strong></td><td>{c.orders}</td><td>{formatPrice(c.discount)}</td><td>{formatPrice(c.revenue)}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </section>
  );
}

function Tile({ label, value }) {
  return (
    <div className="card stat report-stat">
      <span className="muted">{label}</span>
      <span className="report-value">{value}</span>
    </div>
  );
}
