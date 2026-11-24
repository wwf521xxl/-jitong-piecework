# -*- coding: utf-8 -*-
"""密码哈希与会话。"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from . import db

COOKIE_NAME = "jitong_session"
SESSION_DAYS = 30
PBKDF2_ITERATIONS = 160_000


def hash_secret(secret: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_secret(secret: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_b64, digest_b64 = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_b64.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def authenticate(conn, account: str, pin: str):
    account = (account or "").strip()
    if not account:
        return None
    row = conn.execute(
        "SELECT * FROM employees WHERE active=1 AND (employee_no=? OR id=? OR lower(name)=lower(?))",
        (int(account) if account.isdigit() else -1, account, account),
    ).fetchone()
    if row is None and account.lower() in ("admin", "a001"):
        row = conn.execute("SELECT * FROM employees WHERE id='A001' AND active=1").fetchone()
    if row is None:
        return None
    if not verify_secret(pin or "", row["pin_hash"]):
        return None
    return row


def create_session(conn, employee_id: str) -> str:
    token = secrets.token_urlsafe(32)
    now = db.utc_now()
    expires = db.utc_after(SESSION_DAYS)
    conn.execute(
        "INSERT INTO sessions(token, employee_id, created_at, expires_at) VALUES(?,?,?,?)",
        (token, employee_id, now, expires),
    )
    conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
    return token


def session_user(conn, token: str):
    if not token:
        return None
    return conn.execute(
        "SELECT e.* FROM sessions s JOIN employees e ON e.id=s.employee_id "
        "WHERE s.token=? AND s.expires_at > ?",
        (token, db.utc_now()),
    ).fetchone()


def destroy_session(conn, token: str) -> None:
    if token:
        conn.execute("DELETE FROM sessions WHERE token=?", (token,))
