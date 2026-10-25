import { api } from "../api.js";
import { Async, Badge, Card, Cols, Fig, Kpi, Section, useApi } from "../ui.jsx";

export default function Student360({ ctx }) {
  const s = useApi(() => api.student360(ctx.activeId), [ctx.activeId, ctx.rev], 5000);
  const markRead = async (id) => { await api.markRead(id); ctx.bump(); };
  return <Async s={s}>{(d) => {
    const S = d.student, c = d.cohort, msgs = d.inbox, unread = msgs.filter((m) => !m.read), latest = msgs[msgs.length - 1];
    const RC = { Critical: "#EF4444", High: "#F97316", Moderate: "#FACC15", Safe: "#22C55E" };
    const col = (v, avg) => (v >= avg ? "#22C55E" : "#F97316");
    return (<>
      <Section title={`Student 360 - ${S.Student_Name}`} sub={`${S.Student_ID} · ${S.Department} · Semester ${S.Semester} · ${S.Gender}`} />
      {latest ? (
        <div className={unread.length ? "inbox-new" : "inbox-empty"}>
          <div style={{ fontSize: "1.15rem", fontWeight: 800, color: "#fff" }}>
            {unread.length ? `📬 ${unread.length} NEW message${unread.length !== 1 ? "s" : ""} from your faculty` : "📭 Inbox - all messages read"}</div>
          <div style={{ color: "#E2E8F0", fontSize: ".85rem", marginTop: 4 }}>From: {latest.from} · {latest.time} · Subject: {latest.subject}</div>
          <div className="mail">{latest.body}</div>
        </div>
      ) : (
        <div className="inbox-empty">📭 <b>Inbox</b> - no messages yet. Messages sent by faculty from the AI Copilot tab will appear here instantly.</div>
      )}
      {unread.length > 0 && <div className="btn-row"><button className="btn" onClick={() => markRead(S.Student_ID)}>✔ Mark messages as read</button></div>}
      {msgs.length > 1 && (
        <details><summary>Earlier messages ({msgs.length - 1})</summary>
          {[...msgs.slice(0, -1)].reverse().map((m, i) => (<div key={i}><div className="card-title">{m.time} · {m.from}</div><div className="mail">{m.body}</div></div>))}
        </details>
      )}
      <div className="grid5">
        <Kpi label="Success Score" value={S.Success_Score.toFixed(1)} sub={`cohort avg ${c.success.toFixed(1)}`} accent="#A78BFA" />
        <Kpi label="CGPA" value={S.CGPA.toFixed(2)} sub={`cohort avg ${c.cgpa.toFixed(2)} · ${(S.CGPA - c.cgpa >= 0 ? "+" : "")}${(S.CGPA - c.cgpa).toFixed(2)}`} accent="#38BDF8" />
        <Kpi label="Academic Risk" value={S.Academic_Risk} sub={`Backlogs: ${S.Backlogs}`} accent={RC[S.Academic_Risk] || "#64748B"} />
        <Kpi label="Placement Risk" value={S.Placement_Risk} sub={`Target: ${S.Target_Role}`} accent={RC[S.Placement_Risk] || "#64748B"} />
        <Kpi label="Attendance" value={`${S.Attendance_Pct.toFixed(1)}%`} sub={`drop ${S.Attendance_Drop_Pct.toFixed(1)} pts`} accent={S.Attendance_Pct >= 75 ? "#22C55E" : "#F97316"} />
      </div>
      <div style={{ height: 12 }} />
      <Cols widths={[1, 1.6]}>
        <div><Fig fig={d.gauge} /><div className="caption">White line = cohort average ({c.success.toFixed(1)}). This student is {(S.Success_Score - c.success >= 0 ? "+" : "")}{(S.Success_Score - c.success).toFixed(1)} vs average.</div></div>
        <div>
          <Card title="Risk flags">Overall <Badge label={S.Overall_Risk} /> Academic <Badge label={S.Academic_Risk} /> Placement <Badge label={S.Placement_Risk} /> Burnout <Badge label={S.Academic_Burnout_Stress_Risk} kind="burn" /></Card>
          <Card title="⚠️ WHY AT RISK?">{S.AI_Risk_Explanation}<br /><span style={{ color: "#CBD5E1", fontSize: ".9rem" }}>Persona: <b>{S.Behavioral_Persona}</b> · Priority: <b>{S.Intervention_Priority}</b></span></Card>
          <Card title="🎯 NEXT BEST ACTION"><b>{S.Recommended_Action_Plan}</b><br /><span style={{ color: "#CBD5E1" }}>Owner: <b style={{ color: "#fff" }}>{S.Recommended_Faculty_Role}</b> · Estimated recovery: {S.Estimated_Recovery_Time_Weeks} weeks · Status: <b style={{ color: "#fff" }}>{d.status}</b></span></Card>
        </div>
      </Cols>
      <hr />
      <Section title="💼 Placement snapshot" sub={<>Placement readiness for target role: <b>{S.Target_Role}</b></>} />
      <div className="grid4">
        <Kpi label="Placement Risk" value={S.Placement_Risk} sub="owner: Placement Cell" accent={RC[S.Placement_Risk] || "#64748B"} />
        <Kpi label="Coding Score" value={S.Coding_Score.toFixed(1)} sub={`cohort avg ${c.coding.toFixed(1)}`} accent={col(S.Coding_Score, c.coding)} />
        <Kpi label="Aptitude Score" value={S.Aptitude_Score.toFixed(1)} sub={`cohort avg ${c.aptitude.toFixed(1)}`} accent={col(S.Aptitude_Score, c.aptitude)} />
        <Kpi label="Mock Interview" value={S.Mock_Interview_Score.toFixed(1)} sub={`cohort avg ${c.mock.toFixed(1)}`} accent={col(S.Mock_Interview_Score, c.mock)} />
      </div>
      <div style={{ height: 10 }} />
      <Card title="Placement readiness">
        Skill gap level <Badge label={S.Skill_Gap_Level} /> <span style={{ color: "#CBD5E1" }}>score {S.Skill_Gap_Score.toFixed(1)}</span> · Technical skill {S.Technical_Skill_Score.toFixed(0)} · Soft skill {S.Soft_Skill_Score.toFixed(0)}<br />
        {d.gaps.length ? <>Focus areas: <b>{d.gaps.join(", ")}</b>. Placement Cell should schedule targeted practice.</> : "No major placement gap - ready for campus drives."}
      </Card>
    </>);
  }}</Async>;
}
