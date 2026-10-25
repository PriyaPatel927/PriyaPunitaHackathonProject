import { useEffect, useState } from "react";
import * as PlotlyNS from "plotly.js-dist-min";
import * as FactoryNS from "react-plotly.js/factory";

const Plotly = PlotlyNS.default || PlotlyNS;
const createPlotlyComponent = FactoryNS.default?.default || FactoryNS.default || FactoryNS;
const Plot = createPlotlyComponent(Plotly);

export const RISK_COLORS = { Critical: "#EF4444", High: "#F97316", Moderate: "#FACC15", Safe: "#22C55E" };
export const BURN_COLORS = { Critical: "#EF4444", High: "#EF4444", Moderate: "#FACC15", Low: "#22C55E" };
export const RISK_ORDER = ["Critical", "High", "Moderate", "Safe"];
export const STATUS_COLORS = { Pending: "#F87171", "In Progress": "#38BDF8", Completed: "#22C55E" };

export function Fig({ fig }) {
  if (!fig) return null;
  const h = fig.layout?.height || 350;
  return (
    <Plot data={fig.data} layout={{ ...fig.layout, width: undefined, autosize: true }}
      config={{ displayModeBar: false, responsive: true }} useResizeHandler style={{ width: "100%", height: h }} />
  );
}

export const Badge = ({ label, kind = "risk" }) => {
  const bg = (kind === "burn" ? BURN_COLORS : RISK_COLORS)[label] || "#64748B";
  const fg = bg === "#EF4444" || bg === "#64748B" ? "#FFFFFF" : "#0B1220";
  return <span className="badge" style={{ background: bg, color: fg }}>{label}</span>;
};

export const Kpi = ({ label, value, sub, accent = "#38BDF8" }) => (
  <div className="kpi" style={{ "--accent": accent }}>
    <div className="kpi-label">{label}</div><div className="kpi-value">{value}</div><div className="kpi-sub">{sub}</div>
  </div>
);

export const Kpis = ({ items, cols = 4 }) => (
  <div className={`grid${cols}`}>{items.map((k) => <Kpi key={k.label} {...k} />)}</div>
);

export const Card = ({ title, children, style }) => (
  <div className="card" style={style}><div className="card-title" style={style?.borderLeft ? { color: style.accent } : undefined}>{title}</div><div className="card-text">{children}</div></div>
);

export const Section = ({ title, sub }) => (<><div className="sec-title">{title}</div><div className="sec-sub">{sub}</div></>);
export const Chip = ({ kind = "neutral", children }) => <span className={`chip chip-${kind}`}>{children}</span>;
export const Cols = ({ widths = [1, 1], children }) => (
  <div className="cols" style={{ "--cols": widths.map((w) => `${w}fr`).join(" ") }}>{children}</div>
);
export const Html = ({ html }) => <span dangerouslySetInnerHTML={{ __html: html }} />; // only used for server-escaped markup

export function ActiveStrip({ s }) {
  if (!s) return null;
  return (
    <div className="active-strip">👤 <b style={{ color: "#fff", fontSize: "1.05rem" }}>{s.name}</b>
      &nbsp;<span style={{ color: "#CBD5E1" }}>{s.id} · {s.dept} · Semester {s.sem} · CGPA {Number(s.cgpa).toFixed(2)}</span>
      &nbsp;&nbsp;<Badge label={s.risk} />
      <span style={{ color: "#CBD5E1", fontSize: ".85rem" }}>&nbsp;Change student in the sidebar ◀</span></div>
  );
}

export function Table({ rows, height = 320, colorStatus = false }) {
  if (!rows?.length) return null;
  const cols = Object.keys(rows[0]);
  const stat = { Pending: "#7F1D1D", "In Progress": "#0C4A6E", Completed: "#14532D" };
  return (
    <div className="table-wrap" style={{ "--h": `${height}px` }}>
      <table><thead><tr>{cols.map((c) => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>{rows.map((r, i) => (
          <tr key={i}>{cols.map((c) => (
            <td key={c} style={colorStatus && c === "Status" && stat[r[c]] ? { background: stat[r[c]], color: "#fff", fontWeight: 700 } : undefined}>{String(r[c] ?? "")}</td>
          ))}</tr>))}
        </tbody></table>
    </div>
  );
}

export function useApi(fn, deps, pollMs = 0) {
  const [s, setS] = useState({ data: null, error: null, loading: true });
  useEffect(() => {
    let live = true;
    setS((p) => ({ ...p, loading: true, error: null }));
    fn().then((d) => live && setS({ data: d, error: null, loading: false }))
      .catch((e) => live && setS({ data: null, error: e.message, loading: false }));
    // optional silent refresh (keeps what is on screen, so another person's action shows up without a page reload)
    const timer = pollMs ? setInterval(() => {
      fn().then((d) => live && setS((p) => (JSON.stringify(p.data) === JSON.stringify(d) ? p : { data: d, error: null, loading: false }))).catch(() => {});
    }, pollMs) : null;
    return () => { live = false; if (timer) clearInterval(timer); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return s;
}

export function Async({ s, children }) {
  if (s.error) return <div className="alert alert-err">⚠️ {s.error}</div>;
  if (!s.data) return <div className="spinner">⏳ Loading…</div>;
  return <div className={s.loading ? "dim" : ""}>{children(s.data)}</div>;
}

export const useToast = () => {
  const [t, setT] = useState(null);
  const show = (m) => { setT(m); setTimeout(() => setT(null), 3000); };
  return [t, show];
};
