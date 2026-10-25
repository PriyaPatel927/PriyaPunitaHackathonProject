import { api } from "../api.js";
import { ActiveStrip, Async, Card, Cols, Fig, Html, Kpis, Section, useApi } from "../ui.jsx";

export default function Wellness({ ctx }) {
  const restricted = ctx.role === "Placement Officer";
  const s = useApi(() => (restricted ? Promise.resolve({ restricted: true }) : api.wellness(ctx.activeId)), [ctx.activeId, ctx.rev, restricted]);
  return <Async s={s}>{(d) => {
    if (d.restricted) return (<>
      <Section title="Mental Health & Wellness" sub="Restricted" />
      <Card title="🔒 Restricted for Placement Officers">Wellness and stress data is confidential. It is visible only to Administrators, Faculty / Mentors and the student themselves.</Card>
    </>);
    return (<>
      <Section title="Mental Health & Wellness" sub="Academic Burnout / Stress Risk Index, LMS engagement and attendance drops." />
      <ActiveStrip s={ctx.activeStudent} />
      <Kpis items={d.kpis} />
      <div style={{ height: 12 }} />
      <div className="grid3"><Fig fig={d.figs.gauge} /><Fig fig={d.figs.attendance} /><Fig fig={d.figs.lms} /></div>
      <div className="card" style={{ borderLeft: `8px solid ${d.plan.color}` }}>
        <div className="card-title" style={{ color: d.plan.color }}>Dynamic wellness action plan</div>
        <div className="card-text"><div style={{ fontSize: "1.2rem", fontWeight: 800, color: "#fff", marginBottom: 6 }}>{d.plan.title}</div>
          {d.plan.steps.map((x) => <div key={x}>• {x}</div>)}</div>
      </div>
      <Card title="🔎 Detected wellness signals">{d.signals.map((x, i) => <div key={i}><Html html={x} /></div>)}</Card>
    </>);
  }}</Async>;
}
