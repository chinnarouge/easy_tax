from __future__ import annotations

import hashlib
import hmac
import json
import base64
import time
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request

from apps.api.app.config import settings
from apps.api.app.db import get_conn


@dataclass
class UserRecord:
    user_id: str
    email: str
    password_hash: str
    full_name: str


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _next_user_id() -> str:
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) AS cnt FROM users").fetchone()
    return f"user_{row['cnt'] + 1}"


def register_user(email: str, password: str, full_name: str) -> UserRecord:
    conn = get_conn()
    existing = conn.execute("SELECT user_id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        raise ValueError("Email already registered")
    user_id = _next_user_id()
    pw_hash = _hash_password(password)
    conn.execute(
        "INSERT INTO users (user_id, email, password_hash, full_name) VALUES (?, ?, ?, ?)",
        (user_id, email, pw_hash, full_name),
    )
    conn.commit()
    return UserRecord(user_id=user_id, email=email, password_hash=pw_hash, full_name=full_name)


def authenticate_user(email: str, password: str) -> UserRecord | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if row is None:
        return None
    if row["password_hash"] != _hash_password(password):
        return None
    return UserRecord(
        user_id=row["user_id"],
        email=row["email"],
        password_hash=row["password_hash"],
        full_name=row["full_name"],
    )


def create_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": int(time.time()) + settings.access_token_expire_minutes * 60,
    }
    payload_bytes = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig = hmac.new(settings.secret_key.encode(), payload_bytes.encode(), hashlib.sha256).hexdigest()
    return f"{payload_bytes}.{sig}"


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload_bytes, sig = token.rsplit(".", 1)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token format")
    expected_sig = hmac.new(settings.secret_key.encode(), payload_bytes.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        raise HTTPException(status_code=401, detail="Invalid token signature")
    payload = json.loads(base64.urlsafe_b64decode(payload_bytes))
    if payload.get("exp", 0) < time.time():
        raise HTTPException(status_code=401, detail="Token expired")
    return payload


def get_current_user(request: Request) -> UserRecord:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header")
    token = auth_header[7:]
    payload = decode_token(token)
    user_id = payload.get("sub")
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="User not found")
    return UserRecord(
        user_id=row["user_id"],
        email=row["email"],
        password_hash=row["password_hash"],
        full_name=row["full_name"],
    )
