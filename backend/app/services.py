"""All analytics / business logic ported 1:1 from the Streamlit app.py (no web framework in here)."""
import html
import re

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .charts import fj, gauge, style_fig
from .data import (R_ADMIN, R_FAC, R_PO, R_STUDENT, RADAR_AXES, RADAR_BASELINE_FALLBACK, RISK_COLORS, RISK_ORDER,
                   STATUS_ORDER)

BURN_COLORS = {"Critical": "#EF4444", "High": "#EF4444", "Moderate": "#FACC15", "Low": "#22C55E"}
COMPETENCY_LIST = ["Coding", "Aptitude", "Interview", "Communication"]
CONTEXT_METRICS = [("Success", "Success_Score"), ("Attendance", "Attendance_Pct"), ("Aptitude", "Aptitude_Score"),
                   ("Coding", "Coding_Score"), ("Interview", "Mock_Interview_Score"),
                   ("Technical", "Technical_Skill_Score"), ("Soft Skills", "Soft_Skill_Score")]
STEPS4 = [(0, 45, "rgba(239,68,68,.55)"), (45, 60, "rgba(249,115,22,.55)"), (60, 75, "rgba(250,204,21,.55)"), (75, 100, "rgba(34,197,94,.55)")]
STEPS3 = [(0, 40, "rgba(239,68,68,.55)"), (40, 70, "rgba(250,204,21,.55)"), (70, 100, "rgba(34,197,94,.55)")]
WEAK_RULES = {"Coding": ("Coding_Score", 60), "Aptitude": ("Aptitude_Score", 60),
              "Interview": ("Mock_Interview_Score", 60), "Communication": ("Soft_Skill_Score", 55)}


# ------------------------------------------------------------------ helpers
def esc(x) -> str:
    return html.escape(str(x))


def native(o):
    """Make pandas / numpy values JSON friendly."""
    if isinstance(o, dict):
        return {k: native(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [native(v) for v in o]
    if isinstance(o, pd.Series):
        return native(o.to_dict())
    if isinstance(o, np.generic):
        return native(o.item())
    if isinstance(o, np.ndarray):
        return native(o.tolist())
    if isinstance(o, float) and o != o:
        return None
    return o


def kpi(label, value, sub="", accent="#38BDF8"):
    return {"label": label, "value": str(value), "sub": sub, "accent": accent}


def split_list(s):
    return [x.strip() for x in str(s).split(",") if x.strip()]


def skill_match(required, current):
    cur = {c.lower() for c in current}
    return {r: any(alt.strip().lower() in cur for alt in r.split("/")) for r in required}


def row(df, sid) -> pd.Series:
    m = df[df["Student_ID"] == sid]
    if m.empty:
        raise KeyError(sid)
    return m.iloc[0]


def pie(sd, col, title, total=None):
    rc = sd[col].value_counts().reindex(RISK_ORDER).dropna().reset_index()
    rc.columns = ["Risk", "Students"]
    fig = px.pie(rc, names="Risk", values="Students", hole=0.55, color="Risk", color_discrete_map=RISK_COLORS,
                 category_orders={"Risk": RISK_ORDER}, title=title)
    fig.update_traces(textposition="outside", textinfo="label+percent", textfont=dict(color="#F8FAFC", size=13),
                      marker=dict(line=dict(color="#0E1117", width=2)), sort=False)
    fig.update_layout(showlegend=False)
    if total is not None:
        fig.add_annotation(text=f"<b>{total:,}</b><br>students", showarrow=False, font=dict(size=16, color="#FFFFFF"))
    return fig


# ------------------------------------------------------------------ scope / users
def opt_dept(df, dept):
    """Optional department filter (Admin / Placement Officer). None = all departments."""
    return dept if dept in set(df["Department"]) else None


def dept_view(df, dept):
    return df[df["Department"] == dept] if dept else df


def scope(df, role, sid=None, dept=None):
    if role == R_STUDENT:
        return df[df["Student_ID"] == sid]
    if role == R_FAC:
        return df[df["Department"] == dept]
    base = dept_view(df, opt_dept(df, dept))
    if role == R_PO:
        s = base[base["Placement_Risk"].isin(["High", "Critical"])]
        return s if len(s) else base
    return base


def resolve_dept(df, dept):
    depts = sorted(df["Department"].unique())
    return dept if dept in depts else depts[0]


def scope_text(df, role, sd, dept):
    if role == R_STUDENT:
        return "Your personal data only"
    if role == R_FAC:
        return f"{dept} department - {len(sd):,} students"
    if role == R_PO:
        where = f"{dept} department" if dept else "all departments"
        return f"Placement caseload ({where}) - {len(sd):,} students with High/Critical placement risk"
    return f"{dept} department - {len(sd):,} students" if dept else f"Entire institution - {len(df):,} students"


def student_list(df, role, sid, dept):
    if role == R_FAC:
        dept = resolve_dept(df, dept)
    elif role in (R_ADMIN, R_PO):
        dept = opt_dept(df, dept)
    else:
        dept = None
    sd = dept_view(df, dept) if role == R_PO else scope(df, role, sid, dept)   # Placement Officer can pick ANY student
    crit = sd[sd["Overall_Risk"] == "Critical"]
    default = (crit if len(crit) else sd).iloc[0]["Student_ID"]
    cap = {R_STUDENT: "🔒 Locked: students can only view their own data.",
           R_FAC: f"{len(sd)} students in {dept} department.",
           R_PO: f"{len(sd):,} students in {dept} department." if dept else f"{len(sd):,} students - all departments.",
           R_ADMIN: f"{len(sd):,} students in {dept} department." if dept else f"{len(sd):,} students - full institution access."}[role]
    student_dept = sd.iloc[0]["Department"] if role == R_STUDENT and len(sd) else None
    return {"options": [{"id": i, "name": n} for i, n in zip(sd["Student_ID"], sd["Student_Name"])],
            "default_id": default, "dept": dept, "student_dept": student_dept, "caption": cap,
            "scope_text": scope_text(df, role, sd, dept)}


# ------------------------------------------------------------------ outreach email
def default_email(s, sender_role) -> str:
    draft = str(s["Outreach_Message_Draft"]).strip()
    m1 = re.match(r"Supportive outreach:\s*(.*)", draft, flags=re.I)
    m2 = re.match(r"Progress message:\s*(.*)", draft, flags=re.I)
    if m1:
        core = f"Your faculty team would like to {m1.group(1)}"
    elif m2:
        core = f"Great progress so far - {m2.group(1)}"
    else:
        core = draft or "Please continue your current academic and placement preparation."
    return (f"Dear {s['Student_Name']},\n\n{core}\n\n"
            f"Recommended next step: {s['Recommended_Action_Plan']}.\n"
            f"Your peer buddy: {s['Peer_Buddy_Name']} (match score {s['Peer_Match_Score']:.0f}%).\n"
            f"Expected recovery window: about {s['Estimated_Recovery_Time_Weeks']} weeks.\n\n"
            f"Regards,\n{s['Recommended_Faculty_Role']}, {s['Department']} Department\nEduNexus AI Student Success Cell")


PL_COLS = ["Student_ID", "Student_Name", "Department", "Target_Role", "Placement_Risk", "CGPA", "Aptitude_Score",
           "Coding_Score", "Mock_Interview_Score", "Readiness"]


def placement_lists(df):
    """Three student lists for the Placement Officer: caseload (needs support), placement-ready (likely offers), everyone."""
    t = df.copy()
    t["Readiness"] = t[["Aptitude_Score", "Coding_Score", "Mock_Interview_Score", "Technical_Skill_Score", "Soft_Skill_Score"]].mean(axis=1).round(1)
    t["_r"] = t["Placement_Risk"].map({"Safe": 0, "Moderate": 1, "High": 2, "Critical": 3})
    rows = lambda x: x[PL_COLS].to_dict("records")
    ready = t[t["Placement_Risk"] == "Safe"].sort_values("Readiness", ascending=False)
    case = t[t["Placement_Risk"].isin(["High", "Critical"])].sort_values("Readiness")
    return {"ready": rows(ready), "caseload": rows(case), "all": rows(t.sort_values(["_r", "Readiness"], ascending=[True, False]))}


# ------------------------------------------------------------------ TAB 1: command center
def context_fig(S, sd, scope_name, title):
    labels = [a for a, _ in CONTEXT_METRICS]
    stu = [float(S[c]) for _, c in CONTEXT_METRICS]
    avg_ = [float(sd[c].mean()) for _, c in CONTEXT_METRICS]
    fig = go.Figure()
    fig.add_bar(x=labels, y=stu, name=S["Student_Name"], marker_color="#D946EF", text=[f"{v:.0f}" for v in stu],
                textposition="outside", textfont=dict(color="#F8FAFC"))
    fig.add_bar(x=labels, y=avg_, name=f"{scope_name} average", marker_color="#38BDF8", text=[f"{v:.0f}" for v in avg_],
                textposition="outside", textfont=dict(color="#F8FAFC"))
    fig.update_layout(barmode="group", title=title, legend=dict(orientation="h", y=-0.15))
    fig.update_yaxes(range=[0, 115], title="Score / %")
    return fj(style_fig(fig, 380))


def matrix(sd):
    persona = sd["Behavioral_Persona"]
    total_n = max(len(sd), 1)
    segments = [
        ("⚠️ Low Attendance", persona == "Low Attendance", "#F97316", "Attendance below target - risk of academic slide."),
        ("💼 High Academic / Low Placement", persona == "Placement Risk", "#D946EF", "Solid academics but weak placement readiness."),
        ("✅ Consistent All-Rounders", persona == "Balanced", "#22C55E", "Balanced performance across all signals."),
        ("😴 Low Engagement", persona == "Low Engagement", "#38BDF8", "Low LMS activity and participation."),
        ("📚 Academic Strugglers", persona == "Academic Struggler", "#EF4444", "Backlogs and weak grades need mentoring."),
        ("🏆 High Performers", persona == "High Performer", "#FACC15", "Top performers - ideal peer mentors."),
    ]
    cols = ["Student_ID", "Student_Name", "Department", "Success_Score", "CGPA", "Overall_Risk"]
    out = []
    for title, mask, color, desc in segments:
        sub = sd[mask]
        out.append({"title": title, "color": color, "desc": desc, "count": len(sub),
                    "pct": round(len(sub) / total_n * 100, 1),
                    "avg_score": f"{sub['Success_Score'].mean():.1f}" if len(sub) else "-",
                    "avg_cgpa": f"{sub['CGPA'].mean():.2f}" if len(sub) else "-",
                    "students": sub.sort_values("Success_Score")[cols].to_dict("records")})
    return out


def command_center(df, role, sid, active_id, dept):
    S = row(df, active_id)
    if role == R_STUDENT:
        dd = df[df["Department"] == S["Department"]]
        rank = int((dd["Success_Score"] > S["Success_Score"]).sum()) + 1
        pctl = float((df["Success_Score"] < S["Success_Score"]).mean() * 100)
        kpis = [kpi("My Success Score", f"{S['Success_Score']:.1f}", f"dept average {dd['Success_Score'].mean():.1f}", "#A78BFA"),
                kpi("Rank in Department", f"#{rank}", f"out of {len(dd):,} in {S['Department']}", "#38BDF8"),
                kpi("Campus Percentile", f"{pctl:.0f}th", "higher than this % of students", "#22C55E"),
                kpi("My Overall Risk", S["Overall_Risk"], f"CGPA {S['CGPA']:.2f} · attendance {S['Attendance_Pct']:.0f}%",
                    RISK_COLORS.get(S["Overall_Risk"], "#64748B"))]
        hist = px.histogram(dd, x="Success_Score", nbins=20, title=f"Where I stand in {S['Department']} (Success Score)",
                            color_discrete_sequence=["#38BDF8"])
        hist.add_vline(x=float(S["Success_Score"]), line_color="#D946EF", line_width=4,
                       annotation_text=f"You: {S['Success_Score']:.1f}", annotation_font_color="#F0ABFC")
        hist.update_layout(showlegend=False)
        hist.update_xaxes(title="Success Score")
        hist.update_yaxes(title="Students (anonymous)")
        pf = pie(dd, "Overall_Risk", f"{S['Department']} risk mix - you are: {S['Overall_Risk']}")
        return {"variant": "student", "title": "My Command Center",
                "subtitle": f"Your personal dashboard - {S['Student_Name']} · {S['Department']} · Semester {S['Semester']}",
                "kpis": kpis,
                "figs": {"context": context_fig(S, dd, f"{S['Department']} dept", "Me vs my department average"),
                         "hist": fj(style_fig(hist, 380)), "pie": fj(style_fig(pf, 340))},
                "persona": {"name": S["Behavioral_Persona"], "same": int((dd["Behavioral_Persona"] == S["Behavioral_Persona"]).sum()),
                            "dept": S["Department"], "action": S["Recommended_Action_Plan"], "owner": S["Recommended_Faculty_Role"]}}

    if role == R_PO:
        pdept = opt_dept(df, dept)
        df = dept_view(df, pdept)          # department filter (None = all departments)
        cd = scope(df, role)
        kpis = [kpi("Students Tracked", f"{len(df):,}", f"{df['Department'].nunique()} department(s)", "#38BDF8"),
                kpi("Placement Caseload", f"{len(cd):,}", f"{len(cd) / len(df) * 100:.0f}% need placement support", "#F97316"),
                kpi("Avg Skill Gap Score", f"{df['Skill_Gap_Score'].mean():.1f}", f"caseload {cd['Skill_Gap_Score'].mean():.1f}", "#FACC15"),
                kpi("Avg Mock Interview", f"{df['Mock_Interview_Score'].mean():.1f}", f"caseload {cd['Mock_Interview_Score'].mean():.1f}", "#A78BFA")]
        p = pie(df, "Placement_Risk", "Placement Risk Distribution")
        dr = df.groupby(["Department", "Placement_Risk"]).size().reset_index(name="Students")
        b1 = px.bar(dr, x="Department", y="Students", color="Placement_Risk", color_discrete_map=RISK_COLORS,
                    category_orders={"Placement_Risk": RISK_ORDER}, title="Department-wise Placement Risk", text="Students")
        b1.update_traces(textfont=dict(color="#0B1220"))
        b1.update_layout(barmode="stack", legend_title_text="Placement risk")
        ra = cd.groupby("Target_Role")["Skill_Gap_Score"].mean().reset_index().sort_values("Skill_Gap_Score")
        b2 = px.bar(ra, x="Skill_Gap_Score", y="Target_Role", orientation="h", title="Caseload: avg skill-gap score by target role",
                    text=ra["Skill_Gap_Score"].round(1), color_discrete_sequence=["#D946EF"])
        b2.update_traces(textposition="outside", textfont=dict(color="#F8FAFC"))
        b2.update_yaxes(title="")
        counts = {c: int(cd["Missing_Skills"].str.contains(c, na=False).sum()) for c in COMPETENCY_LIST}
        b3 = px.bar(pd.DataFrame({"Competency": list(counts), "Students": list(counts.values())}), x="Competency", y="Students",
                    title="Caseload: competency gaps flagged", text="Students", color_discrete_sequence=["#38BDF8"])
        b3.update_traces(textposition="outside", textfont=dict(color="#F8FAFC"))
        sc = cd.groupby("Department")[["Aptitude_Score", "Coding_Score", "Mock_Interview_Score"]].mean().reset_index().melt("Department", var_name="Score", value_name="Average")
        sc["Score"] = sc["Score"].str.replace("_Score", "").str.replace("_", " ")
        b4 = px.bar(sc, x="Department", y="Average", color="Score", barmode="group", title="Caseload: placement scores by department",
                    color_discrete_sequence=["#38BDF8", "#D946EF", "#FACC15"])
        b4.update_yaxes(range=[0, 100])
        return {"variant": "placement", "title": "Placement Command Center",
                "subtitle": f"Placement readiness across {'all ' if not pdept else pdept + ' - '}{len(df):,} students · your caseload = {len(cd):,} students with High/Critical placement risk",
                "kpis": kpis, "matrix": matrix(cd), "lists": placement_lists(df),
                "figs": {"pie": fj(style_fig(p, 360)), "dept": fj(style_fig(b1, 360)), "role": fj(style_fig(b2, 340)),
                         "comp": fj(style_fig(b3, 340)), "scores": fj(style_fig(b4, 340)),
                         "context": context_fig(S, cd, "Caseload", "Selected student vs placement-caseload average")}}

    is_fac = role == R_FAC
    dept = resolve_dept(df, dept) if is_fac else opt_dept(df, dept)
    sd = scope(df, role, sid, dept)
    total = len(sd)
    n_crit = int((sd["Overall_Risk"] == "Critical").sum())
    n_high = int(sd["Overall_Risk"].isin(["High", "Critical"]).sum())
    kpis = [kpi("Total Students", f"{total:,}", f"{sd['Department'].nunique()} department(s)", "#38BDF8"),
            kpi("Avg Success Score", f"{sd['Success_Score'].mean():.1f}", f"Avg CGPA {sd['CGPA'].mean():.2f}", "#A78BFA"),
            kpi("High Risk Count", f"{n_high:,}", f"{n_high / max(total, 1) * 100:.0f}% of this view (High + Critical)", "#F97316"),
            kpi("Critical Cases", n_crit, "need action today", "#EF4444")]
    if dept:
        dr = sd.groupby(["Semester", "Overall_Risk"]).size().reset_index(name="Students")
        bar = px.bar(dr, x="Semester", y="Students", color="Overall_Risk", color_discrete_map=RISK_COLORS,
                     category_orders={"Overall_Risk": RISK_ORDER}, title=f"{dept}: Risk by Semester", text="Students")
        bar.update_xaxes(type="category")
    else:
        dr = sd.groupby(["Department", "Overall_Risk"]).size().reset_index(name="Students")
        bar = px.bar(dr, x="Department", y="Students", color="Overall_Risk", color_discrete_map=RISK_COLORS,
                     category_orders={"Overall_Risk": RISK_ORDER}, title="Department Risk Breakdown", text="Students")
    bar.update_traces(textfont=dict(color="#0B1220"))
    bar.update_layout(barmode="stack", legend_title_text="Risk")
    nm = "Department" if dept else "Institution"
    return {"variant": "faculty" if is_fac else "admin",
            "title": f"Command Center - {dept} Department" if dept else "Command Center",
            "subtitle": f"Aggregated view of {total:,} students - {scope_text(df, role, sd, dept)}.",
            "kpis": kpis, "matrix": matrix(sd),
            "figs": {"pie": fj(style_fig(pie(sd, "Overall_Risk", "Overall Risk Distribution", total), 360)),
                     "bar": fj(style_fig(bar, 360)),
                     "context": context_fig(S, sd, nm, f"Selected student vs {nm.lower()} average")}}


def summary(df, sid):
    S = row(df, sid)
    return {"id": sid, "name": S["Student_Name"], "dept": S["Department"], "sem": int(S["Semester"]),
            "cgpa": float(S["CGPA"]), "risk": S["Overall_Risk"]}


# ------------------------------------------------------------------ TAB 2: student 360
def student360(df, status, inbox, sid):
    S = row(df, sid)
    avg = float(df["Success_Score"].mean())
    gaps = [m for m in split_list(S["Missing_Skills"]) if m.lower() != "no major gap"]
    cohort = {"success": avg, "cgpa": float(df["CGPA"].mean()), "coding": float(df["Coding_Score"].mean()),
              "aptitude": float(df["Aptitude_Score"].mean()), "mock": float(df["Mock_Interview_Score"].mean())}
    return {"student_id": sid, "student": S, "cohort": cohort, "gaps": gaps,
            "status": status.get(sid, S["Intervention_Status"]), "inbox": inbox,
            "gauge": fj(gauge(S["Success_Score"], "Success Score (0-100)", STEPS4, ref=avg))}


# ------------------------------------------------------------------ TAB 3: skill gap
def skills(df, sid):
    S = row(df, sid)
    cur_sk, req_sk = split_list(S["Current_Skills"]), split_list(S["Required_Skills"])
    match = skill_match(req_sk, cur_sk)
    pct = sum(match.values()) / len(req_sk) * 100 if req_sk else 0
    miss_comp = [m for m in split_list(S["Missing_Skills"]) if m.lower() != "no major gap"]
    flagged = [{"comp": c, "score": float(S[WEAK_RULES[c][0]]) if c in WEAK_RULES else None} for c in miss_comp]
    watch = [{"comp": c, "score": float(S[col])} for c, (col, th) in WEAK_RULES.items() if c not in miss_comp and S[col] < th]
    tech_missing = [k for k, ok in match.items() if not ok]
    learn_first = None
    if tech_missing or flagged or watch:
        w = min(WEAK_RULES.items(), key=lambda kv: S[kv[1][0]])
        learn_first = {"comp": w[0], "score": float(S[w[1][0]])}
    tech_s, gap_s = float(S["Technical_Skill_Score"]), float(S["Skill_Gap_Score"])
    match_score = float(np.clip(0.5 * pct + 0.3 * tech_s + 0.2 * (100 - gap_s), 0, 100))
    baseline = ({c: float(df[c].mean()) for _, c in RADAR_AXES} if len(df) >= 50 else dict(RADAR_BASELINE_FALLBACK))
    labels = [a for a, _ in RADAR_AXES]
    stu_vals = [float(S[c]) for _, c in RADAR_AXES]
    base_vals = [baseline[c] for _, c in RADAR_AXES]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=base_vals + base_vals[:1], theta=labels + labels[:1], name="Cohort average",
                                  line=dict(color="#38BDF8", dash="dash", width=2), fill="toself", fillcolor="rgba(56,189,248,0.12)"))
    fig.add_trace(go.Scatterpolar(r=stu_vals + stu_vals[:1], theta=labels + labels[:1], name=S["Student_Name"],
                                  line=dict(color="#D946EF", width=3), fill="toself", fillcolor="rgba(217,70,239,0.30)"))
    fig.update_layout(title="Skill Radar - student vs cohort baseline",
                      polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(range=[0, 100], gridcolor="#334155", tickfont=dict(color="#CBD5E1"), linecolor="#334155"),
                                 angularaxis=dict(tickfont=dict(color="#FFFFFF", size=14), gridcolor="#334155")),
                      legend=dict(orientation="h", y=-0.08))
    table = []
    for (lab, col), b in zip(RADAR_AXES, base_vals):
        v = float(S[col])
        table.append({"Competency": lab, "Student": round(v, 1), "Cohort average": round(b, 1), "Difference": round(v - b, 1),
                      "Status": "Above average" if v >= b else "Below average"})
    return {"student_id": sid, "target_role": S["Target_Role"], "gap_level": S["Skill_Gap_Level"], "gap_score": float(S["Skill_Gap_Score"]),
            "current": cur_sk, "required": [{"skill": k, "ok": ok} for k, ok in match.items()], "tech_missing": tech_missing,
            "flagged": flagged, "watch": watch, "learn_first": learn_first, "n_have": sum(match.values()), "n_req": len(req_sk),
            "pct": pct, "tech_s": tech_s, "gap_s": gap_s,
            "match_gauge": fj(gauge(match_score, "Required-skill match", STEPS3, suffix="%")),
            "radar": fj(style_fig(fig, 470)), "table": table}


# ------------------------------------------------------------------ TAB 4: wellness
def wellness(df, sid):
    S = row(df, sid)
    idx_col, lab_col = "Academic_Burnout_Stress_Risk_Index", "Academic_Burnout_Stress_Risk"
    mins = df.groupby(lab_col)[idx_col].min()
    mod_start, high_start = float(mins.get("Moderate", 30)), float(mins.get("High", 50))
    if not mod_start < high_start:
        mod_start, high_start = 30.0, 50.0
    level = S[lab_col]
    lms_avg, lms_q25 = float(df["LMS_Weekly_Logins"].mean()), float(df["LMS_Weekly_Logins"].quantile(0.25))
    drop = float(S["Attendance_Drop_Pct"])
    kpis = [kpi("Burnout / Stress Index", f"{S[idx_col]:.1f}", f"level: {level}", BURN_COLORS.get(level, "#64748B")),
            kpi("LMS Logins / week", f"{S['LMS_Weekly_Logins']:.1f}", f"cohort avg {lms_avg:.1f}", "#A78BFA"),
            kpi("Attendance Drop", f"{drop:.1f} pts", f"{S['Previous_Attendance_Pct']:.1f}% → {S['Attendance_Pct']:.1f}%", "#F97316" if drop >= 10 else "#22C55E"),
            kpi("Active Backlogs", S["Backlogs"], "academic pressure", "#EF4444" if S["Backlogs"] >= 3 else "#38BDF8")]
    g = gauge(S[idx_col], "Burnout / Stress Risk Index", [(0, mod_start, "rgba(34,197,94,.55)"), (mod_start, high_start, "rgba(250,204,21,.55)"),
                                                          (high_start, 100, "rgba(239,68,68,.55)")], ref=df[idx_col].mean(), num_size=24)
    att = go.Figure(go.Bar(x=["Previous", "Current"], y=[S["Previous_Attendance_Pct"], S["Attendance_Pct"]],
                           marker_color=["#64748B", "#EF4444" if drop >= 10 else "#38BDF8"],
                           text=[f"{S['Previous_Attendance_Pct']:.1f}%", f"{S['Attendance_Pct']:.1f}%"], textposition="outside", textfont=dict(color="#F8FAFC")))
    att.update_layout(title=f"Attendance (drop {drop:.1f} pts)", showlegend=False)
    att.update_yaxes(range=[0, 115], title="%")
    lms = go.Figure(go.Bar(x=["This student", "Cohort average", "Cohort bottom quartile"], y=[S["LMS_Weekly_Logins"], lms_avg, lms_q25],
                           marker_color=["#D946EF", "#38BDF8", "#64748B"],
                           text=[f"{S['LMS_Weekly_Logins']:.1f}", f"{lms_avg:.1f}", f"{lms_q25:.1f}"], textposition="outside", textfont=dict(color="#F8FAFC")))
    lms.update_layout(title="LMS weekly logins", showlegend=False)
    lms.update_yaxes(range=[0, max(14, S["LMS_Weekly_Logins"] + 2)])
    signals = []
    if drop >= 10:
        signals.append(f"📉 Attendance fell <b>{drop:.1f} points</b> ({S['Previous_Attendance_Pct']:.1f}% → {S['Attendance_Pct']:.1f}%)")
    if S["Backlogs"] >= 2:
        signals.append(f"📚 <b>{S['Backlogs']} active backlogs</b> are adding academic pressure")
    if S["LMS_Weekly_Logins"] <= lms_q25:
        signals.append(f"💻 LMS logins ({S['LMS_Weekly_Logins']:.1f}/week) are in the cohort's bottom quartile")
    if S["Attendance_Pct"] < 65:
        signals.append(f"🏫 Attendance of <b>{S['Attendance_Pct']:.1f}%</b> is below the 65% comfort line")
    if str(level) in ("High", "Critical"):
        color, title = "#EF4444", "🚨 WARNING - High stress / burnout risk"
        steps = ["Refer to the Student Counselor within 48 hours", "Hold a one-to-one check-in with the faculty mentor this week",
                 "Reduce academic load: agree a backlog-clearance timetable", "Activate the peer buddy and notify parent/guardian if advised"]
    elif str(level) == "Moderate":
        color, title = "#FACC15", "⚠️ WATCH - Moderate stress level"
        steps = ["Schedule a mentor check-in within two weeks", "Set weekly attendance and LMS targets", "Encourage peer-buddy study sessions"]
    else:
        color, title = "#22C55E", "✅ STABLE - Low stress level"
        steps = ["No intervention needed - continue routine mentoring", "Keep monitoring attendance and LMS activity monthly"]
    return {"student_id": sid, "kpis": kpis, "signals": signals or ["✅ No acute stress signals detected."],
            "plan": {"color": color, "title": title, "steps": steps},
            "figs": {"gauge": fj(g), "attendance": fj(style_fig(att, 265)), "lms": fj(style_fig(lms, 265))}}


# ------------------------------------------------------------------ TAB 5: copilot
def copilot(df, status, workflow, sid, role):
    S = row(df, sid)
    saved = (workflow.get(sid) or {}).get("draft")
    peer = None
    if S["Peer_Buddy_ID"] in set(df["Student_ID"]):
        B = row(df, S["Peer_Buddy_ID"])
        peer = {"id": B["Student_ID"], "dept": B["Department"], "sem": int(B["Semester"]), "success": float(B["Success_Score"]), "cgpa": float(B["CGPA"])}
    return {"student_id": sid, "student_name": S["Student_Name"], "draft": saved or default_email(S, role),
            "source_draft": S["Outreach_Message_Draft"], "status": status.get(sid, S["Intervention_Status"]),
            "activity": (workflow.get(sid) or {}).get("activity") or "No activity yet",
            "buddy": {"name": S["Peer_Buddy_Name"], "match": float(S["Peer_Match_Score"]), "info": peer},
            "match_gauge": fj(gauge(S["Peer_Match_Score"], "Match score", STEPS3, num_size=24))}


def tracker(df, status, workflow, role, sid, active_id, dept, mode):
    dept = resolve_dept(df, dept) if role == R_FAC else (opt_dept(df, dept) if role in (R_ADMIN, R_PO) else None)
    sd = dept_view(df, dept) if role == R_PO else scope(df, role, sid, dept)
    counts = pd.Series({i: status.get(i, "Pending") for i in sd["Student_ID"]}).value_counts()
    modes = ["My workflow"] if role == R_STUDENT else ["Updated this session", "Active P1-P2 workflows", "All students"]
    if mode not in modes:
        mode = modes[-1] if role == R_STUDENT else modes[1]
    act = {k: v["activity"] for k, v in workflow.items() if v.get("activity")}
    t = sd[["Student_ID", "Student_Name", "Department", "Overall_Risk", "Intervention_Priority", "Success_Score"]].copy()
    t["Status"] = t["Student_ID"].map(status)
    t["Last Action"] = t["Student_ID"].map(act).fillna("-")
    t["Touched"] = t["Student_ID"].isin(act.keys())
    if mode == "My workflow":
        t = t[t["Student_ID"] == active_id]
    elif mode == "Updated this session":
        t = t[t["Touched"]]
    elif mode == "Active P1-P2 workflows":
        t = t[(t["Intervention_Priority"].str.startswith(("P1", "P2")) & (t["Status"] != "Completed")) | t["Touched"]]
    t = t.sort_values(["Touched", "Intervention_Priority", "Success_Score"], ascending=[False, True, True])
    shown = t.drop(columns=["Touched", "Success_Score"]).rename(columns={"Student_ID": "ID", "Student_Name": "Student", "Overall_Risk": "Risk", "Intervention_Priority": "Priority"})
    return {"scope_text": scope_text(df, role, sd, dept), "mode": mode, "modes": modes,
            "counts": {k: int(counts.get(k, 0)) for k in STATUS_ORDER}, "rows": shown.to_dict("records")}


# ------------------------------------------------------------------ TAB 6: what-if
def whatif(df, sid):
    S = row(df, sid)
    base, att80, plus10 = float(S["Success_Score"]), float(S["What_If_Attendance_80_Score"]), float(S["What_If_Score_Plus_10"])
    d_att, d_skill = att80 - base, plus10 - base
    fig = go.Figure(go.Bar(x=["Current", "Attendance → 80%", "Skills +10 pts"], y=[base, att80, plus10],
                           marker_color=["#64748B", "#38BDF8", "#22C55E"],
                           text=[f"{base:.1f}", f"{att80:.1f} ({d_att:+.1f})", f"{plus10:.1f} ({d_skill:+.1f})"],
                           textposition="outside", textfont=dict(color="#F8FAFC", size=14)))
    fig.update_layout(title=f"Projected Success Score - {S['Student_Name']}", showlegend=False)
    fig.update_yaxes(range=[max(0, base - 15), min(105, max(plus10, att80) + 10)], title="Success Score")
    if S["Attendance_Pct"] >= 80:
        att_msg = f"Attendance is already <b>{S['Attendance_Pct']:.1f}%</b> (above 80%), so raising it gives no extra uplift."
    else:
        att_msg = f"Raising attendance from <b>{S['Attendance_Pct']:.1f}%</b> to <b>80%</b> adds <b>{d_att:+.1f}</b> points."
    return {"student_id": sid,
            "kpis": [kpi("Current Success Score", f"{base:.1f}", f"attendance {S['Attendance_Pct']:.1f}%", "#64748B"),
                     kpi("If attendance reaches 80%", f"{att80:.1f}", f"{d_att:+.1f} points", "#38BDF8"),
                     kpi("If skills improve +10 pts", f"{plus10:.1f}", f"{d_skill:+.1f} points", "#22C55E")],
            "insight": f"{att_msg}<br>A +10 skill improvement adds <b>{d_skill:+.1f}</b> points.<br>Biggest lever for this student: "
                       f"<b>{'improving skills (+10 pts)' if d_skill >= d_att else 'raising attendance to 80%'}</b>.",
            "recovery": {"weeks": int(S["Estimated_Recovery_Time_Weeks"]), "potential": int(S["What_If_Improvement_Potential"]),
                         "plan": S["Recommended_Action_Plan"]},
            "bar": fj(style_fig(fig, 380)),
            "gauge": fj(gauge(plus10, "Best-case score (+10 skills)", STEPS4, ref=base))}
