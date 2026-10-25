import { useEffect, useState } from "react";
import { api, setToken } from "./api.js";
import { Badge, Card, RISK_ORDER, useToast } from "./ui.jsx";
import CommandCenter from "./tabs/CommandCenter.jsx";
import Student360 from "./tabs/Student360.jsx";
import SkillGap from "./tabs/SkillGap.jsx";
import Wellness from "./tabs/Wellness.jsx";
import Copilot from "./tabs/Copilot.jsx";
import WhatIf from "./tabs/WhatIf.jsx";

const ROLES = ["Administrator", "Faculty / Mentor", "Placement Officer", "Student (View Own Data)"];

function StudentPicker({ options, value, onChange }) {
  const label = (o) => `${o.id} - ${o.name}`;
  const [text, setText] = useState("");
  const [open, setOpen] = useState(false);
  const [typing, setTyping] = useState(false);
  useEffect(() => { const o = options.find((x) => x.id === value); setText(o ? label(o) : ""); setTyping(false); }, [value, options]);
  const q = text.trim().toLowerCase();
  const shown = typing && q ? options.filter((o) => label(o).toLowerCase().includes(q)) : options;   // ALL students, scrollable
  const choose = (o) => { onChange(o.id); setText(label(o)); setOpen(false); setTyping(false); };
  return (
    <div style={{ position: "relative" }}>
      <input type="text" value={text} placeholder="Type ID or name…"
        onFocus={(e) => { e.target.select(); setOpen(true); }}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onChange={(e) => { setText(e.target.value); setTyping(true); setOpen(true); }} />
      {open && (
        <div style={{ position: "absolute", zIndex: 50, left: 0, right: 0, top: "100%", maxHeight: 280, overflowY: "auto",
                      background: "#111827", border: "1px solid #334155", borderRadius: 8, marginTop: 2 }}>
          {shown.length === 0 && <div style={{ padding: "8px 10px", color: "#94A3B8" }}>No student found</div>}
          {shown.map((o) => (
            <div key={o.id} onMouseDown={(e) => { e.preventDefault(); choose(o); }}
              style={{ padding: "7px 10px", cursor: "pointer", color: "#E5E7EB", background: o.id === value ? "#1E293B" : "transparent" }}>{label(o)}</div>
          ))}
        </div>
      )}
      <div className="caption">{shown.length.toLocaleString()} of {options.length.toLocaleString()} students listed</div>
    </div>
  );
}

export default function App() {
  const [meta, setMeta] = useState(null);
  const [fatal, setFatal] = useState("");
  const [role, setRole] = useState(ROLES[0]);
  const [auth, setAuth] = useState(null);          // {role, userId, studentId, name}
  const [loginErr, setLoginErr] = useState("");
  const [mode, setMode] = useState("signin");      // "signin" | "signup"
  const [uidIn, setUidIn] = useState(""); const [pwIn, setPwIn] = useState(""); const [nameIn, setNameIn] = useState("");
  const [busy, setBusy] = useState(false);
  const [dept, setDept] = useState(null);
  const [opts, setOpts] = useState(null);
  const [activeId, setActiveId] = useState(null);
  const [active, setActive] = useState(null);
  const [tab, setTab] = useState(0);
  const [rev, setRev] = useState(0);
  const [upMsg, setUpMsg] = useState("");
  const [toast, showToast] = useToast();

  const isStudent = role.startsWith("Student");
  const signedIn = !!auth && auth.role === role;
  const bump = () => setRev((r) => r + 1);

  useEffect(() => { api.meta().then(setMeta).catch((e) => setFatal(e.message)); }, [rev]);

  // leaving a role signs the previous person out (same as the Streamlit app)
  useEffect(() => { if (auth && auth.role !== role) { setAuth(null); setToken(null); setOpts(null); setActiveId(null); setDept(null); } }, [role]); // eslint-disable-line

  const resetForm = () => { setUidIn(""); setPwIn(""); setNameIn(""); setLoginErr(""); };
  const submitAuth = async (e) => {
    e.preventDefault(); setLoginErr(""); setBusy(true);
    try {
      const r = mode === "signup" ? await api.signup(role, uidIn.trim(), pwIn.trim(), nameIn.trim()) : await api.login(role, uidIn.trim(), pwIn.trim());
      setToken(r.token); setAuth({ role, userId: r.user_id, studentId: r.student_id, name: r.name }); resetForm();
    } catch (err) { setLoginErr(err.message); } finally { setBusy(false); }
  };
  const signOut = () => { setAuth(null); setToken(null); setOpts(null); setActiveId(null); setDept(null); resetForm(); };
  const idEx = meta?.id_examples?.[role] || "";

  // student list for the signed-in role
  useEffect(() => {
    if (!signedIn) return;
    api.students(isStudent ? undefined : dept).then((r) => {
      setOpts(r);
      if (role === "Faculty / Mentor" && r.dept && r.dept !== dept) setDept(r.dept);
      setActiveId((prev) => (r.options.some((o) => o.id === prev) ? prev : r.default_id));
    }).catch((e) => setLoginErr(e.message));
  }, [signedIn, role, dept, rev]); // eslint-disable-line

  useEffect(() => { if (signedIn && activeId) api.summary(activeId).then(setActive).catch(() => {}); }, [signedIn, activeId, rev]);

  const upload = async (e) => {
    const f = e.target.files?.[0]; if (!f) return;
    setUpMsg("Uploading…");
    try { const r = await api.upload(f); setUpMsg(`Loaded ${r.n_students} students from your file.`); setActiveId(null); bump(); }
    catch (err) { setUpMsg(err.message); }
    e.target.value = "";
  };
  const resetData = async () => { await api.resetDataset(); setUpMsg("Built-in dataset restored."); setActiveId(null); bump(); };

  const labels = ["🏠 Command Center", "🎓 Student 360", "💼 Skill Gap", "🧠 Mental Health & Wellness", "🤖 AI Copilot", "🎛 What-If Simulator"];
  if (role === "Placement Officer") labels[3] = "🔒 Wellness (restricted)";
  if (isStudent) { labels[0] = "🏠 My Command Center"; labels[4] = "🤝 My Support & Buddy"; }

  const ctx = { role, isStudent, activeId, activeStudent: active, dept, rev, bump, toast: showToast };
  const src = meta ? { upload: "Uploaded dataset", builtin: "Built-in dataset" }[meta.source] || "Built-in dataset" : "";
  const pages = [CommandCenter, Student360, SkillGap, Wellness, Copilot, WhatIf];
  const Page = pages[tab];

  if (fatal) return <div className="main"><div className="alert alert-err">⚠️ {fatal}</div><div className="caption">Check that the backend is running and VITE_API_URL is correct.</div></div>;

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="hero-title" style={{ fontSize: "1.6rem" }}>Edu<span>Nexus</span> AI</div>
        <div className="hero-tag" style={{ fontSize: ".85rem" }}>Smart Campus Analytics &amp; Student Success</div>
        <hr />
        {!isStudent && signedIn && (<>
          <label className="lbl">📂 Upload Student360 dataset (.xlsx)</label>
          <input type="file" accept=".xlsx" onChange={upload} style={{ color: "#E5E7EB", width: "100%" }} />
          {upMsg && <div className="caption">{upMsg}</div>}
          {meta?.source === "upload" && <div className="btn-row"><button className="btn" onClick={resetData}>↩ Restore built-in data</button></div>}
        </>)}
        <h3>🔐 Access level</h3>
        {ROLES.map((r) => (<label key={r} className="radio"><input type="radio" name="role" checked={role === r} onChange={() => { setRole(r); setTab(0); setLoginErr(""); }} /> {r}</label>))}

        {!signedIn && (<>
          <div className="tabs" style={{ marginTop: 12, marginBottom: 4 }}>
            <button type="button" className={`tab ${mode === "signin" ? "active" : ""}`} onClick={() => { setMode("signin"); setLoginErr(""); }}>Sign in</button>
            <button type="button" className={`tab ${mode === "signup" ? "active" : ""}`} onClick={() => { setMode("signup"); setLoginErr(""); }}>Sign up</button>
          </div>
          <form onSubmit={submitAuth}>
            {mode === "signup" && !isStudent && (<>
              <label className="lbl">Full name</label>
              <input type="text" value={nameIn} onChange={(e) => setNameIn(e.target.value)} placeholder="Your full name" />
            </>)}
            <label className="lbl">{isStudent ? "Student" : role} ID</label>
            <input type="text" value={uidIn} onChange={(e) => setUidIn(e.target.value)} placeholder={`e.g. ${idEx}`} autoComplete="username" />
            <label className="lbl">Password</label>
            <input type="password" value={pwIn} onChange={(e) => setPwIn(e.target.value)} placeholder="Last 4 digits of your ID" autoComplete="current-password" />
            <div className="btn-row"><button className="btn" type="submit" disabled={busy}>{mode === "signup" ? "📝 Create account" : "🔓 Sign in"}</button></div>
          </form>
          <div className="caption">ID format: <b>{idEx.replace(/\d{4}$/, "")}</b> + 4 digits (e.g. {idEx}). Password = the last 4 digits of the ID.</div>
          {isStudent && <details><summary>ℹ️ About student accounts</summary>
            <div className="caption">Sign up with your Student ID from the dataset (e.g. STU1002 → password 1002). Once signed in, a student can only view their own data and cannot switch to another student.</div></details>}
        </>)}
        {loginErr && <div className="alert alert-err">{loginErr}</div>}

        {signedIn && (<>
          <div className="card" style={{ padding: "10px 14px", marginTop: 10 }}><div className="card-title">Signed in as</div><div className="card-text"><b>{auth.name}</b><br /><span style={{ color: "#CBD5E1" }}>{auth.userId}</span></div></div>
          <div className="btn-row"><button className="btn" onClick={signOut}>🚪 Sign out</button></div>
        </>)}

        {signedIn && opts && (<>
          {role === "Faculty / Mentor" && (<>
            <label className="lbl">Your department (faculty sign-in)</label>
            <select value={dept || ""} onChange={(e) => setDept(e.target.value)}>{meta.departments.map((d) => <option key={d}>{d}</option>)}</select>
          </>)}
          {(role === "Administrator" || role === "Placement Officer") && (<>
            <label className="lbl">🏫 Department</label>
            <select value={dept || ""} onChange={(e) => setDept(e.target.value || null)}>
              <option value="">All Departments ({meta.n_students?.toLocaleString()} students)</option>
              {meta.departments.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </>)}
          {isStudent && opts.student_dept && (<>
            <label className="lbl">🏫 Department</label>
            <div className="card" style={{ padding: "8px 14px", marginBottom: 6 }}><div className="card-text"><b>{opts.student_dept}</b></div></div>
          </>)}
          <h3 style={{ marginTop: 14 }}>🎯 Active student</h3>
          {isStudent
            ? <select disabled value={activeId || ""}><option>{opts.options[0]?.id} - {opts.options[0]?.name}</option></select>
            : <StudentPicker options={opts.options} value={activeId} onChange={setActiveId} />}
          <div className="caption">{opts.caption}</div>
        </>)}
        <hr />
        <h3>📂 Dataset</h3>
        <div className="caption">Using: {meta?.source === "upload" ? "your uploaded file" : "built-in 1000-student dataset"}</div>
        <hr />
        <h3>🎨 Risk legend</h3>
        {RISK_ORDER.map((r) => <Badge key={r} label={r} />)}
      </aside>

      <main className="main">
        {!signedIn ? (<>
          <div className="hero"><div className="hero-title">🎓 Edu<span>Nexus</span> AI</div>
            <div className="hero-tag">Smart Campus Analytics &amp; Student Success Platform</div>
            <span className="hero-chip">🔐 Viewing as: {role}</span></div>
          <Card title={isStudent ? "🔒 Student sign-in required" : "🔒 Sign in required"}>
            {isStudent ? <>Please sign in (or sign up) from the sidebar with your <b>Student ID</b> and <b>password</b>. After signing in you will only see your own data - Command Center, Student 360, Skills, Wellness and Support plan.</>
              : <>Please sign in (or sign up) from the sidebar with your <b>{role} ID</b> and <b>password</b> to continue.</>}
          </Card>
        </>) : (<>
          <div className="hero">
            <div className="hero-title">🎓 Edu<span>Nexus</span> AI</div>
            <div className="hero-tag">Smart Campus Analytics &amp; Student Success Platform - The Unified Student Success &amp; Intelligence Hub</div>
            <span className="hero-chip">📊 {src} · {meta?.n_students?.toLocaleString()} students</span>
            {!isStudent && <span className="hero-chip">⬆ Upload your own .xlsx from the sidebar</span>}
            <span className="hero-chip">🔐 Viewing as: {role}</span>
            <span className="hero-chip">🔎 Scope: {opts?.scope_text}</span>
            {active && <span className="hero-chip">🎯 Active: {active.name}</span>}
          </div>
          <div className="tabs">{labels.map((l, i) => <button key={l} className={`tab ${tab === i ? "active" : ""}`} onClick={() => setTab(i)}>{l}</button>)}</div>
          {activeId && opts ? <Page ctx={ctx} /> : <div className="spinner">⏳ Loading…</div>}
        </>)}
      </main>
      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
