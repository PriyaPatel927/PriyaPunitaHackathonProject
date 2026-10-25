"""Constants + the 45-column schema (identical to the Streamlit app) + normalise()."""
import pandas as pd

ROLES = ["Administrator", "Faculty / Mentor", "Placement Officer", "Student (View Own Data)"]
R_ADMIN, R_FAC, R_PO, R_STUDENT = ROLES
RISK_ORDER = ["Critical", "High", "Moderate", "Safe"]
RISK_COLORS = {"Critical": "#EF4444", "High": "#F97316", "Moderate": "#FACC15", "Safe": "#22C55E"}
STATUS_ORDER = ["Pending", "In Progress", "Completed"]
RADAR_AXES = [("Aptitude", "Aptitude_Score"), ("Coding", "Coding_Score"), ("Interview", "Mock_Interview_Score"),
              ("Technical", "Technical_Skill_Score"), ("Soft Skills", "Soft_Skill_Score")]
RADAR_BASELINE_FALLBACK = {"Aptitude_Score": 68.5, "Coding_Score": 69.4, "Mock_Interview_Score": 67.4,
                           "Technical_Skill_Score": 62.6, "Soft_Skill_Score": 63.7}

SCHEMA = {
    "Student_ID": "", "Student_Name": "", "Department": "Unknown", "Gender": "Unknown", "Semester": 1, "CGPA": 7.0,
    "Success_Score": 50.0, "Academic_Risk": "Moderate", "Placement_Risk": "Moderate", "Aptitude_Score": 65.0,
    "Coding_Score": 65.0, "Mock_Interview_Score": 65.0, "Overall_Risk": "Moderate", "Behavioral_Persona": "Balanced",
    "AI_Risk_Explanation": "No explanation available.", "Feedback_Score": 65.0, "Current_Skills": "", "Target_Role": "Not set",
    "Required_Skills": "", "Missing_Skills": "No major gap", "Skill_Gap_Level": "Moderate", "Skill_Gap_Score": 30.0,
    "Technical_Skill_Score": 60.0, "Soft_Skill_Score": 60.0, "Previous_Attendance_Pct": 75.0, "Attendance_Pct": 75.0,
    "Attendance_Drop_Pct": 0.0, "Backlogs": 0, "LMS_Weekly_Logins": 5.0, "Academic_Burnout_Stress_Risk_Index": 20.0,
    "Academic_Burnout_Stress_Risk": "Low", "Outreach_Message_Draft": "Progress message: continue current academic and placement preparation.",
    "Parent_Nudge_Draft": "No parent nudge required.", "Peer_Buddy_ID": "", "Peer_Buddy_Name": "Not assigned",
    "Peer_Match_Score": 0.0, "What_If_Attendance_80_Score": 50.0, "What_If_Score_Plus_10": 60.0,
    "What_If_Improvement_Potential": 10, "Estimated_Recovery_Time_Weeks": 4,
    "Recommended_Action_Plan": "Continue regular mentoring", "Recommended_Faculty_Role": "Faculty Advisor",
    "Intervention_Priority": "P3 - Moderate", "Intervention_Status": "Pending", "Report_Eligible": "No",
}
NUMERIC = ["Semester", "CGPA", "Success_Score", "Aptitude_Score", "Coding_Score", "Mock_Interview_Score", "Feedback_Score",
           "Skill_Gap_Score", "Technical_Skill_Score", "Soft_Skill_Score", "Previous_Attendance_Pct", "Attendance_Pct",
           "Attendance_Drop_Pct", "Backlogs", "LMS_Weekly_Logins", "Academic_Burnout_Stress_Risk_Index", "Peer_Match_Score",
           "What_If_Attendance_80_Score", "What_If_Score_Plus_10", "What_If_Improvement_Potential", "Estimated_Recovery_Time_Weeks"]


def normalise(df: pd.DataFrame) -> pd.DataFrame:
    """Guarantee every one of the 45 columns exists with the right dtype so nothing can KeyError."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    for col, default in SCHEMA.items():
        if col not in df.columns:
            df[col] = default
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(SCHEMA[col])
    for col in df.columns:
        if col not in NUMERIC:
            df[col] = df[col].fillna("").astype(str).str.strip()
    df["Semester"] = df["Semester"].astype(int)
    df["Backlogs"] = df["Backlogs"].astype(int)
    df = df[df["Student_ID"] != ""].drop_duplicates("Student_ID").reset_index(drop=True)
    if df.empty:
        raise ValueError("no rows")
    return df
