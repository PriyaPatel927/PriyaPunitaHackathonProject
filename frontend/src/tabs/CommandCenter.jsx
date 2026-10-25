import { api } from "../api.js";
import { Async, Card, Cols, Fig, Kpis, Section, Table, useApi } from "../ui.jsx";

function Matrix({ items }) {
  return (
    <div className="grid3">
      {items.map((m) => (
        <div key={m.title}>
          <div className="seg" style={{ "--accent": m.color }}>
            <div className="seg-title">{m.title}</div>
            <div className="seg-count">{m.count.toLocaleString()}</div>
            <div className="seg-desc">{m.pct}% of this view · Avg score {m.avg_score} · Avg CGPA {m.avg_cgpa}</div>
            <div className="seg-desc">{m.desc}</div>
          </div>
          {m.count > 0 && (
            <details><summary>View {m.count.toLocaleString()} students</summary><Table rows={m.students} height={320} /></details>
          )}
        </div>
      ))}
    </div>
  );
}

const Context = ({ d }) => (<>
  <Section title="🔍 Selected student in context" sub="Changes whenever you pick another student in the sidebar." />
  <Fig fig={d.figs.context} />
</>);

function StudentView({ d }) {
  return (<>
    <Section title={d.title} sub={d.subtitle} />
    <Kpis items={d.kpis} />
    <div style={{ height: 12 }} />
    <Cols><Fig fig={d.figs.context} /><Fig fig={d.figs.hist} /></Cols>
    <Cols widths={[1, 1.2]}>
      <Fig fig={d.figs.pie} />
      <div>
        <Card title="🧬 My behavioural segment">
          <span style={{ fontSize: "1.3rem", fontWeight: 800, color: "#fff" }}>{d.persona.name}</span><br />
          {d.persona.same.toLocaleString()} students in {d.persona.dept} share this persona.<br /><br />
          Next best action: <b>{d.persona.action}</b><br /><span style={{ color: "#CBD5E1" }}>Owner: {d.persona.owner}</span>
        </Card>
        <Card title="🔒 Privacy">You only see your own record plus anonymous department-level numbers. Other students' details are never shown.</Card>
      </div>
    </Cols>
  </>);
}

function PlacementLists({ lists }) {
  const items = [
    { key: "ready", title: "🏆 Placement Ready - most likely to get job offers", desc: "Placement risk = Safe, ranked by readiness (average of aptitude, coding, mock interview, technical and soft skills)." },
    { key: "caseload", title: "🚨 Placement Caseload - needs support", desc: "Placement risk = High or Critical, weakest readiness first." },
    { key: "all", title: "👥 All students", desc: "Everyone in the selected scope, best placement risk first." },
  ];
  return (<div>{items.map((i) => (
    <details key={i.key} open={i.key === "ready"}>
      <summary><b>{i.title}</b> · {lists[i.key].length.toLocaleString()} students</summary>
      <div className="caption">{i.desc}</div>
      {lists[i.key].length ? <Table rows={lists[i.key]} height={360} /> : <div className="alert alert-info">No students in this view.</div>}
    </details>))}</div>);
}

function PlacementView({ d }) {
  return (<>
    <Section title={d.title} sub={d.subtitle} />
    <Kpis items={d.kpis} />
    <div style={{ height: 12 }} />
    <Cols widths={[1, 1.4]}><Fig fig={d.figs.pie} /><Fig fig={d.figs.dept} /></Cols>
    <Cols><Fig fig={d.figs.role} /><Fig fig={d.figs.comp} /></Cols>
    <Fig fig={d.figs.scores} />
    <Section title="🎯 Placement Students" sub="Same students, three views - all lists are scrollable and follow the department you selected." />
    <PlacementLists lists={d.lists} />
    <Section title="🧬 AI Cohort Matrix - placement caseload" sub="Behavioural segments inside your caseload." />
    <Matrix items={d.matrix} />
    <Context d={d} />
  </>);
}

function StaffView({ d }) {
  return (<>
    <Section title={d.title} sub={d.subtitle} />
    <Kpis items={d.kpis} />
    <div style={{ height: 12 }} />
    <Cols widths={[1, 1.4]}><Fig fig={d.figs.pie} /><Fig fig={d.figs.bar} /></Cols>
    <Section title="🧬 AI Cohort Matrix" sub="Students grouped by Behavioral_Persona so you can target the right support at scale." />
    <Matrix items={d.matrix} />
    <Context d={d} />
  </>);
}

export default function CommandCenter({ ctx }) {
  const s = useApi(() => api_(ctx), [ctx.activeId, ctx.dept, ctx.role, ctx.rev]);
  return (
    <Async s={s}>{(d) => d.variant === "student" ? <StudentView d={d} /> : d.variant === "placement" ? <PlacementView d={d} /> : <StaffView d={d} />}</Async>
  );
}
const api_ = (ctx) => api.commandCenter(ctx.activeId, ctx.isStudent ? undefined : ctx.dept);
