import { useLayoutEffect, useRef, useState } from "react";

// Single-series column chart: thin bars (≤24px) with 4px rounded tops on one baseline,
// hairline grid, compact y ticks, and a per-bar tooltip on hover and keyboard focus.
// Values are also shown in the report's table view, so the tooltip never gates data.
const HEIGHT = 240;
const PAD = { top: 12, right: 8, bottom: 28, left: 52 };

function niceStep(max, ticks = 4) {
  const raw = max / ticks;
  const mag = 10 ** Math.floor(Math.log10(raw || 1));
  return [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? 10 * mag;
}

function roundedTop(x, y, w, h) {
  const r = Math.min(4, w / 2, h);
  return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`;
}

export default function BarChart({ data, formatValue, formatTick, renderTooltip, ariaLabel }) {
  const wrap = useRef(null);
  const [width, setWidth] = useState(640);
  const [hover, setHover] = useState(null);

  useLayoutEffect(() => {
    const el = wrap.current;
    setWidth(Math.max(280, el.clientWidth)); // measure before first paint, then track resizes
    const ro = new ResizeObserver(([entry]) => setWidth(Math.max(280, entry.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const max = Math.max(0, ...data.map((d) => d.value));
  const step = niceStep(max || 1);
  const top = Math.max(step, Math.ceil(max / step) * step);
  const ticks = Array.from({ length: Math.round(top / step) + 1 }, (_, i) => i * step);

  const plotW = width - PAD.left - PAD.right;
  const plotH = HEIGHT - PAD.top - PAD.bottom;
  const band = plotW / Math.max(1, data.length);
  const barW = Math.max(2, Math.min(24, band - 2)); // 2px surface gap between neighbours
  const y = (v) => PAD.top + plotH - (v / top) * plotH;
  const labelEvery = Math.ceil(data.length / Math.max(1, Math.floor(plotW / 64)));

  const tip = hover !== null && data[hover];
  const tipX = tip ? PAD.left + band * hover + band / 2 : 0;

  return (
    <div className="bar-chart" ref={wrap}>
      <svg width={width} height={HEIGHT} role="img" aria-label={ariaLabel}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={width - PAD.right} y1={y(t)} y2={y(t)} className="grid" />
            <text x={PAD.left - 8} y={y(t)} dy="0.32em" textAnchor="end" className="tick">{formatTick(t)}</text>
          </g>
        ))}
        {data.map((d, i) => {
          const x = PAD.left + band * i;
          const h = (d.value / top) * plotH;
          return (
            <g key={d.label}>
              {h > 0 && (
                <path d={roundedTop(x + (band - barW) / 2, y(d.value), barW, h)} className={`bar${hover === i ? " active" : ""}`} />
              )}
              {/* Hit target: the whole column slot, not just the painted bar. */}
              <rect
                x={x} y={PAD.top} width={band} height={plotH} fill="transparent" tabIndex={0}
                aria-label={`${d.label}: ${formatValue(d.value)}`}
                onPointerEnter={() => setHover(i)} onPointerLeave={() => setHover(null)}
                onFocus={() => setHover(i)} onBlur={() => setHover(null)}
              />
              {i % labelEvery === 0 && (
                <text x={x + band / 2} y={HEIGHT - 8} textAnchor="middle" className="tick">{d.short ?? d.label}</text>
              )}
            </g>
          );
        })}
      </svg>
      {tip && (
        <div className="chart-tooltip" style={{ left: Math.min(Math.max(tipX, 80), width - 80), top: Math.max(0, y(tip.value) - 8) }}>
          {renderTooltip(tip)}
        </div>
      )}
    </div>
  );
}
