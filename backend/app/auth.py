"""Accounts + tokens.

ID format per access level (4 digits at the end), and the password is always the LAST 4 DIGITS of the ID:
    Administrator      ADMIN1234  -> password 1234
    Faculty / Mentor   FAC1234    -> password 1234
    Placement Officer  PLC1234    -> password 1234
    Student            STU1002    -> password 1002   (must be an ID that exists in the dataset)
"""
import hashlib
import hmac
import re
import time

import jwt
from fastapi import Header, HTTPException

from .config import JWT_SECRET
from .data import R_ADMIN, R_FAC, R_PO, R_STUDENT

ID_PREFIX = {R_ADMIN: "ADMIN", R_FAC: "FAC", R_PO: "PLC", R_STUDENT: "STU"}


def id_example(role: str) -> str:
    return f"{ID_PREFIX[role]}1234"


def normalise_id(role: str, user_id: str) -> str:
    """Return the cleaned-up ID, or raise 400 if it does not follow the format for this access level."""
    uid = re.sub(r"\s+", "", str(user_id or "")).upper()
    if role not in ID_PREFIX:
        raise HTTPException(400, "Unknown access level.")
    if not re.fullmatch(re.escape(ID_PREFIX[role]) + r"\d{4}", uid):
        raise HTTPException(400, f"{role} ID must be {ID_PREFIX[role]} followed by 4 digits (e.g. {id_example(role)}).")
    return uid


def required_password(uid: str) -> str:
    """Password rule: last 4 digits of the ID (ADMIN1234 -> 1234)."""
    return re.sub(r"\D", "", uid)[-4:]


def hash_password(pw: str, salt: str | None = None) -> str:
    salt = salt or hashlib.sha256(str(time.time_ns()).encode()).hexdigest()[:16]
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 60_000).hex()
    return f"{salt}${h}"


def check_password(pw: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(pw or "", salt), stored)


def make_token(role: str, uid: str, name: str) -> str:
    sid = uid if role == R_STUDENT else None
    return jwt.encode({"role": role, "uid": uid, "sid": sid, "name": name, "exp": int(time.time()) + 12 * 3600},
                      JWT_SECRET, algorithm="HS256")


def current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Please sign in first.")
    try:
        p = jwt.decode(authorization.split(" ", 1)[1], JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Session expired - please sign in again.")
    return {"role": p["role"], "sid": p.get("sid"), "uid": p.get("uid"), "name": p.get("name")}


def can_see(user: dict, sid: str):
    if user["role"] == R_STUDENT and user["sid"] != sid:
        raise HTTPException(403, "Students can only view their own data.")


def staff_only(user: dict):
    if user["role"] == R_STUDENT:
        raise HTTPException(403, "This action is only for staff.")
