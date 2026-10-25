"""Database layer (SQLAlchemy). SQLite locally, PostgreSQL in production - only DATABASE_URL changes.

Tables
  students  - the 45-column Student360 dataset (written with pandas)
  workflow  - per-student intervention status / saved email draft / last activity
  inbox     - emails delivered to a student's inbox
  meta      - small key/value store (e.g. which dataset is loaded)
"""
import os
from datetime import datetime

import pandas as pd
from sqlalchemy import Boolean, Column, Integer, String, Text, create_engine, delete, inspect, select
from sqlalchemy.orm import Session, declarative_base

from .config import DATABASE_URL
from .data import normalise

DEFAULT_CSV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "students.csv")
engine = create_engine(DATABASE_URL, pool_pre_ping=True,
                       connect_args={"check_same_thread": False, "timeout": 30} if DATABASE_URL.startswith("sqlite") else {})
Base = declarative_base()

# When a student marks the emailed plan as read, the staff tracker moves from "In Progress" to this status.
READ_STATUS = "Completed"


class Account(Base):
    __tablename__ = "accounts"
    user_id = Column(String(32), primary_key=True)      # ADMIN1234 / FAC1234 / PLC1234 / STU1002
    role = Column(String(40), nullable=False)
    name = Column(String(120), nullable=False)
    pw_hash = Column(String(200), nullable=False)
    created = Column(String(40))


class Workflow(Base):
    __tablename__ = "workflow"
    student_id = Column(String(32), primary_key=True)
    status = Column(String(20), nullable=False, default="Pending")
    draft = Column(Text, nullable=True)
    activity = Column(String(300), nullable=True)


class InboxMessage(Base):
    __tablename__ = "inbox"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(32), index=True, nullable=False)
    time = Column(String(40))
    sender = Column(String(60))
    subject = Column(String(200))
    body = Column(Text)
    read = Column(Boolean, default=False, nullable=False)


class Meta(Base):
    __tablename__ = "meta"
    key = Column(String(50), primary_key=True)
    value = Column(String(200))


_cache = {"df": None}


def _now() -> str:
    return datetime.now().strftime("%d %b %Y, %H:%M")


# ---------------------------------------------------------------- students
def _write_students(df: pd.DataFrame, source: str):
    df.to_sql("students", engine, if_exists="replace", index=False, chunksize=200, method="multi")
    with Session(engine) as s:
        s.merge(Meta(key="source", value=source))
        s.commit()
    _cache["df"] = df


def init_db():
    Base.metadata.create_all(engine)
    if not inspect(engine).has_table("students"):
        _write_students(normalise(pd.read_csv(DEFAULT_CSV)), "builtin")


def students() -> pd.DataFrame:
    if _cache["df"] is None:
        _cache["df"] = normalise(pd.read_sql("SELECT * FROM students", engine))
    return _cache["df"]


def source() -> str:
    with Session(engine) as s:
        m = s.get(Meta, "source")
        return m.value if m else "builtin"


def _clear_workflow():
    with Session(engine) as s:
        s.execute(delete(Workflow))
        s.execute(delete(InboxMessage))
        s.commit()


def replace_dataset(df: pd.DataFrame, src="upload"):
    _write_students(df, src)
    _clear_workflow()


def reset_dataset():
    replace_dataset(normalise(pd.read_csv(DEFAULT_CSV)), "builtin")


# ---------------------------------------------------------------- workflow / inbox
def workflow_map() -> dict:
    with Session(engine) as s:
        return {w.student_id: {"status": w.status, "draft": w.draft, "activity": w.activity}
                for w in s.scalars(select(Workflow))}


def status_map(df: pd.DataFrame) -> dict:
    out = df.set_index("Student_ID")["Intervention_Status"].to_dict()
    for sid, w in workflow_map().items():
        if sid in out:
            out[sid] = w["status"]
    return out


def inbox_for(sid: str) -> list:
    with Session(engine) as s:
        rows = s.scalars(select(InboxMessage).where(InboxMessage.student_id == sid).order_by(InboxMessage.id))
        return [{"time": m.time, "from": m.sender, "subject": m.subject, "body": m.body, "read": m.read} for m in rows]


def send_email(sid: str, sender_role: str, body: str):
    now = _now()
    with Session(engine) as s:
        w = s.get(Workflow, sid) or Workflow(student_id=sid)
        w.status, w.draft, w.activity = "In Progress", body, f"{now} · Email sent by {sender_role}"
        s.add(w)
        s.add(InboxMessage(student_id=sid, time=now, sender=sender_role, read=False, body=body,
                           subject="Your personalised support plan - EduNexus AI"))
        s.commit()


def complete(sid: str, sender_role: str):
    now = _now()
    with Session(engine) as s:
        w = s.get(Workflow, sid) or Workflow(student_id=sid)
        w.status, w.activity = "Completed", f"{now} · Marked Completed by {sender_role}"
        s.add(w)
        s.commit()


def clear_draft(sid: str):
    with Session(engine) as s:
        w = s.get(Workflow, sid)
        if w:
            w.draft = None
            s.commit()


def mark_read(sid: str):
    """Student opened the message(s): mark them read AND move the staff-side workflow forward."""
    with Session(engine) as s:
        newly_read = 0
        for m in s.scalars(select(InboxMessage).where(InboxMessage.student_id == sid)):
            if not m.read:
                m.read = True
                newly_read += 1
        if newly_read:
            w = s.get(Workflow, sid)
            if w and w.status == "In Progress":      # never overwrite a manual "Completed"
                w.status, w.activity = READ_STATUS, f"{_now()} · Email read by student"
        s.commit()


# ---------------------------------------------------------------- accounts
def get_account(user_id: str):
    with Session(engine) as s:
        a = s.get(Account, user_id)
        return {"user_id": a.user_id, "role": a.role, "name": a.name, "pw_hash": a.pw_hash} if a else None


def create_account(user_id: str, role: str, name: str, pw_hash: str):
    with Session(engine) as s:
        s.add(Account(user_id=user_id, role=role, name=name, pw_hash=pw_hash, created=_now()))
        s.commit()
