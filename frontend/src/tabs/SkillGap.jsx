import { api } from "../api.js";
import { ActiveStrip, Async, Badge, Card, Chip, Cols, Fig, Section, Table, useApi } from "../ui.jsx";

export default function SkillGap({ ctx }) {
  const s = useApi(() => api.skills(ctx.activeId), [ctx.activeId, ctx.rev]);
  return <Async s={s}>{(d) => {
    const nothing = !d.tech_missing.length && !d.flagged.length && !d.watch.length;
    return (<>
      <Section title="Skill Gap Analysis" sub="Current skills vs the skills required for the target role." />
      <ActiveStrip s={ctx.activeStudent} />
      <Cols widths={[1.05, 1]}>
        <div>
          <Card title="🎯 Target role"><span style={{ fontSize: "1.3rem", fontWeight: 800, color: "#fff" }}>{d.target_role}</span> &nbsp;Skill gap: <Badge label={d.gap_level} /> <span style={{ color: "#CBD5E1" }}>score {d.gap_score.toFixed(1)}</span></Card>
          <Card title="✅ Current skills">{d.current.length ? d.current.map((c) => <Chip key={c}>{c}</Chip>) : "None recorded"}</Card>
          <Card title="📋 Required skills (green = have · red = missing)">
            {d.required.length ? d.required.map((r) => <Chip key={r.skill} kind={r.ok ? "ok" : "bad"}>{r.ok ? "✔" : "✖"} {r.skill}</Chip>) : "None"}</Card>
          <Card title="⛔ Missing skills (to learn)">
            {d.tech_missing.length > 0 && <div><b>Technical skills to learn</b><br />{d.tech_missing.map((k) => <Chip key={k} kind="bad">✖ {k}</Chip>)}</div>}
            {d.flagged.length > 0 && <div><b>Readiness gaps flagged for this student</b><br />{d.flagged.map((f) => <Chip key={f.comp} kind="bad">⛔ {f.comp}{f.score != null ? ` · ${f.score.toFixed(0)}/100` : ""}</Chip>)}</div>}
            {d.watch.length > 0 && <div><b>Watch list (score below benchmark)</b><br />{d.watch.map((w) => <Chip key={w.comp} kind="warn">👀 {w.comp} · {w.score.toFixed(0)}/100</Chip>)}</div>}
            {d.learn_first && <div><b>Learn first:</b> {d.learn_first.comp} (score {d.learn_first.score.toFixed(0)})</div>}
            {nothing && <Chip kind="ok">No major gap - all required skills covered</Chip>}
          </Card>
          <Fig fig={d.match_gauge} />
          <div className="caption">{d.n_have} of {d.n_req} required skills covered ({d.pct.toFixed(0)}%) · blended with this student's Technical score ({d.tech_s.toFixed(0)}) and skill-gap score ({d.gap_s.toFixed(1)}).</div>
        </div>
        <Fig fig={d.radar} />
      </Cols>
      <Table rows={d.table} height={260} />
    </>);
  }}</Async>;
}
