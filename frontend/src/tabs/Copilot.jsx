import { useState } from "react";
import { api } from "../api.js";
import { ActiveStrip, Async, Card, Fig, Kpi, STATUS_COLORS, Section, Table, useApi } from "../ui.jsx";

function Tracker({ ctx }) {
  const [mode, setMode] = useState(ctx.isStudent ? "My workflow" : "Active P1-P2 workflows");
  const s = useApi(() => api.tracker(ctx.activeId, mode, ctx.isStudent ? undefined : ctx.dept), [ctx.activeId, ctx.dept, ctx.role, ctx.rev, mode], 4000);
  return <Async s={s}>{(t) => (<>
    <div className="caption">Scope: {t.scope_text}</div>
    <div className="grid3">{["Pending", "In Progress", "Completed"].map((k) => <Kpi key={k} label={k} value={t.counts[k]} sub="" accent={STATUS_COLORS[k]} />)}</div>
    <div style={{ display: "flex", gap: 16, flexWrap: "wrap", margin: "10px 0" }}>
      {t.modes.map((m) => (
        <label key={m} className="radio"><input type="radio" checked={t.mode === m} onChange={() => setMode(m)} /> {m}</label>))}
    </div>
    {t.rows.length ? <Table rows={t.rows} height={470} colorStatus /> : <div className="alert alert-info">Nothing here yet - send an email on the left and the workflow appears instantly.</div>}
  </>)}</Async>;
}

function Body({ d, ctx }) {
  const [body, setBody] = useState(d.draft);
  const [flash, setFlash] = useState(null);
  const [busy, setBusy] = useState(false);
  const run = async (fn, after) => {
    setBusy(true);
    try { const r = await fn(); after?.(r); ctx.bump(); } catch (e) { setFlash({ err: true, m: e.message }); } finally { setBusy(false); }
  };
  const id = d.student_id, b = d.buddy;
  return (<>
    {flash && <div className={`alert ${flash.err ? "alert-err" : "alert-ok"}`}>{flash.m}</div>}
    {ctx.isStudent ? (<>
      <Card title="🔒 Staff tool">The email composer is available to faculty, placement officers and administrators. Any message sent to you appears in your <b>Student 360</b> inbox.</Card>
      <Card title="Your intervention status"><b>{d.status}</b> · {d.activity}</Card>
    </>) : (<>
      <div className="sec-title" style={{ fontSize: "1.1rem" }}>✉️ AI-generated outreach to {d.student_name}</div>
      <label className="lbl">Email body (editable)</label>
      <textarea rows={13} value={body} onChange={(e) => setBody(e.target.value)} />
      <div className="caption">Source column Outreach_Message_Draft: {d.source_draft}</div>
      <div className="btn-row">
        <button className="btn" disabled={busy} onClick={() => run(() => api.sendEmail(id, body), (r) => { setFlash({ m: r.message }); ctx.toast("📧 Email sent - status: In Progress"); })}>📧 Send Email to Student (Mark In Progress)</button>
        <button className="btn" disabled={busy} onClick={() => run(() => api.complete(id), (r) => { setFlash({ m: r.message }); ctx.toast("✅ Intervention completed"); })}>✅ Mark Completed</button>
        <button className="btn" disabled={busy} onClick={() => run(() => api.regenerate(id), (r) => setBody(r.draft))}>🔄 Regenerate AI draft</button>
      </div>
      <div>Current status: <b>{d.status}</b></div>
    </>)}
    <hr />
    <div className="sec-title" style={{ fontSize: "1.1rem" }}>🤝 Peer Buddy Match</div>
    <div className="cols" style={{ "--cols": "1.2fr 1fr" }}>
      <Card title="Recommended mentor">
        <span style={{ fontSize: "1.3rem", fontWeight: 800, color: "#fff" }}>{b.name}</span>
        {b.info && <><br /><span style={{ color: "#CBD5E1" }}>{b.info.id} · {b.info.dept} · Semester {b.info.sem}<br />Success score {b.info.success.toFixed(1)} · CGPA {b.info.cgpa.toFixed(2)}</span></>}
      </Card>
      <Fig fig={d.match_gauge} />
    </div>
  </>);
}

export default function Copilot({ ctx }) {
  const s = useApi(() => api.copilot(ctx.activeId), [ctx.activeId, ctx.rev], 4000);
  return (<>
    <Section title="AI Copilot - Teacher Email System" sub="Review the AI draft, send it to the student, and track the workflow live." />
    <ActiveStrip s={ctx.activeStudent} />
    <div className="cols" style={{ "--cols": "1.1fr 1fr" }}>
      <Async s={s}>{(d) => <Body key={d.student_id} d={d} ctx={ctx} />}</Async>
      <div>
        <div className="sec-title" style={{ fontSize: "1.1rem" }}>📋 Live Intervention Tracker</div>
        <Tracker ctx={ctx} />
      </div>
    </div>
  </>);
}
