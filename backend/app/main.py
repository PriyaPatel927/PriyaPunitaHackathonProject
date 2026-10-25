"""EduNexus AI - FastAPI backend. Run: uvicorn app.main:app --reload"""
import io
import logging
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import database as db
from . import services as sv
from .auth import (can_see, check_password, current_user, hash_password, id_example, make_token, normalise_id,
                   required_password, staff_only)
from .config import CORS_ORIGINS
from .data import RISK_COLORS, RISK_ORDER, ROLES, R_STUDENT, normalise


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()          # creates tables and loads the 1000-student dataset on first start
    yield


app = FastAPI(title="EduNexus AI API", version="1.0.0", lifespan=lifespan)
log = logging.getLogger("edunexus")


@app.middleware("http")
async def never_hide_errors(request: Request, call_next):
    """An unhandled exception normally skips the CORS headers, so the browser reports it as a network failure
    ("Cannot reach the server"). Turn it into a normal JSON 500 so the real reason reaches the UI."""
    try:
        return await call_next(request)
    except Exception as e:  # noqa: BLE001
        log.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse({"detail": f"Server error: {type(e).__name__}: {e}"}, status_code=500)


# added AFTER the middleware above so CORS wraps it (last added = outermost)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def out(x):
    return sv.native(x)


def student_row_or_404(df, sid):
    if sid not in set(df["Student_ID"]):
        raise HTTPException(404, f"Student {sid} not found")


class Login(BaseModel):
    role: str
    user_id: str
    password: str


class Signup(Login):
    name: str = ""


class EmailBody(BaseModel):
    body: str


# ----------------------------------------------------------------- public
@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/meta")
def meta():
    df = db.students()
    return {"roles": ROLES, "risk_order": RISK_ORDER, "risk_colors": RISK_COLORS, "source": db.source(),
            "n_students": len(df), "departments": sorted(df["Department"].unique().tolist()),
            "id_examples": {r: id_example(r) for r in ROLES}}


# ----------------------------------------------------------------- auth
def _session(account: dict) -> dict:
    return {"token": make_token(account["role"], account["user_id"], account["name"]), "role": account["role"],
            "user_id": account["user_id"], "name": account["name"],
            "student_id": account["user_id"] if account["role"] == R_STUDENT else None}


@app.post("/api/auth/signup")
def signup(b: Signup):
    if b.role not in ROLES:
        raise HTTPException(400, "Unknown access level.")
    uid = normalise_id(b.role, b.user_id)
    if (b.password or "").strip() != required_password(uid):
        raise HTTPException(400, f"Password must be the last 4 digits of your ID ({uid} -> {required_password(uid)}).")
    if db.get_account(uid):
        raise HTTPException(409, f"{uid} is already registered - please sign in instead.")
    if b.role == R_STUDENT:
        df = db.students()
        if uid not in set(df["Student_ID"]):
            raise HTTPException(404, f"Student ID {uid} was not found in the student dataset.")
        name = df.loc[df["Student_ID"] == uid, "Student_Name"].iloc[0]
    else:
        name = (b.name or "").strip()
        if len(name) < 2:
            raise HTTPException(400, "Please enter your full name.")
    db.create_account(uid, b.role, name, hash_password(required_password(uid)))
    return _session({"user_id": uid, "role": b.role, "name": name})


@app.post("/api/auth/login")
def login(b: Login):
    if b.role not in ROLES:
        raise HTTPException(400, "Unknown access level.")
    uid = normalise_id(b.role, b.user_id)
    a = db.get_account(uid)
    if not a or a["role"] != b.role or not check_password((b.password or "").strip(), a["pw_hash"]):
        raise HTTPException(401, "Invalid ID or password. If you are new, please sign up first.")
    if b.role == R_STUDENT and uid not in set(db.students()["Student_ID"]):
        raise HTTPException(401, "This Student ID is no longer in the loaded dataset.")
    return _session(a)


# ----------------------------------------------------------------- students / tabs
@app.get("/api/students")
def students(dept: str | None = None, u=Depends(current_user)):
    return out(sv.student_list(db.students(), u["role"], u["sid"], dept))


@app.get("/api/command-center")
def command_center(student_id: str, dept: str | None = None, u=Depends(current_user)):
    can_see(u, student_id)
    df = db.students()
    student_row_or_404(df, student_id)
    return out(sv.command_center(df, u["role"], u["sid"], student_id, dept))


@app.get("/api/students/{sid}/summary")
def summary(sid: str, u=Depends(current_user)):
    can_see(u, sid)
    df = db.students()
    student_row_or_404(df, sid)
    return out(sv.summary(df, sid))


@app.get("/api/students/{sid}")
def student360(sid: str, u=Depends(current_user)):
    can_see(u, sid)
    df = db.students()
    student_row_or_404(df, sid)
    return out(sv.student360(df, db.status_map(df), db.inbox_for(sid), sid))


@app.get("/api/students/{sid}/skills")
def skills(sid: str, u=Depends(current_user)):
    can_see(u, sid)
    df = db.students()
    student_row_or_404(df, sid)
    return out(sv.skills(df, sid))


@app.get("/api/students/{sid}/wellness")
def wellness(sid: str, u=Depends(current_user)):
    can_see(u, sid)
    if u["role"] == "Placement Officer":
        raise HTTPException(403, "Wellness data is restricted for Placement Officers.")
    df = db.students()
    student_row_or_404(df, sid)
    return out(sv.wellness(df, sid))


@app.get("/api/students/{sid}/copilot")
def copilot(sid: str, u=Depends(current_user)):
    can_see(u, sid)
    df = db.students()
    student_row_or_404(df, sid)
    return out(sv.copilot(df, db.status_map(df), db.workflow_map(), sid, u["role"]))


@app.post("/api/students/{sid}/email")
def send_email(sid: str, b: EmailBody, u=Depends(current_user)):
    staff_only(u)
    student_row_or_404(db.students(), sid)
    db.send_email(sid, u["role"], b.body)
    return {"ok": True, "message": "Email delivered to the student's inbox and status set to In Progress. Open the Student 360 tab to see it."}


@app.post("/api/students/{sid}/complete")
def complete(sid: str, u=Depends(current_user)):
    staff_only(u)
    student_row_or_404(db.students(), sid)
    db.complete(sid, u["role"])
    return {"ok": True, "message": "Intervention marked as Completed."}


@app.post("/api/students/{sid}/regenerate")
def regenerate(sid: str, u=Depends(current_user)):
    staff_only(u)
    df = db.students()
    student_row_or_404(df, sid)
    db.clear_draft(sid)
    return {"draft": sv.default_email(sv.row(df, sid), u["role"])}


@app.post("/api/students/{sid}/inbox/read")
def inbox_read(sid: str, u=Depends(current_user)):
    can_see(u, sid)
    db.mark_read(sid)
    return {"ok": True}


@app.get("/api/students/{sid}/whatif")
def whatif(sid: str, u=Depends(current_user)):
    can_see(u, sid)
    df = db.students()
    student_row_or_404(df, sid)
    return out(sv.whatif(df, sid))


@app.get("/api/tracker")
def tracker(student_id: str, mode: str = "", dept: str | None = None, u=Depends(current_user)):
    can_see(u, student_id)
    df = db.students()
    return out(sv.tracker(df, db.status_map(df), db.workflow_map(), u["role"], u["sid"], student_id, dept, mode))


# ----------------------------------------------------------------- dataset
@app.post("/api/dataset/upload")
async def upload(file: UploadFile = File(...), u=Depends(current_user)):
    staff_only(u)
    try:
        df = normalise(pd.read_excel(io.BytesIO(await file.read()), sheet_name=0))
    except Exception:
        raise HTTPException(400, "The uploaded file could not be read. Please upload a valid Student360 .xlsx file.")
    db.replace_dataset(df, "upload")
    return {"ok": True, "n_students": len(df)}


@app.post("/api/dataset/reset")
def reset(u=Depends(current_user)):
    staff_only(u)
    db.reset_dataset()
    return {"ok": True}
