"""admin_auth.py - administrator accounts, sessions and the audit log (Python standard library only).

Security design
  * Passwords are hashed with scrypt (salted, memory-hard) and compared in constant time.
  * There is NO public registration. Accounts are created on the server with create_admin.py.
  * A successful login creates a random session token. Only its SHA-256 hash is stored in college.db,
    so a copy of the database cannot be used to impersonate an administrator.
  * Sessions end after an idle period and an absolute maximum, and on logout. Every sensitive operation
    in admin_service.py calls require(token) first; the check runs on the server, not in the browser.
  * Five wrong passwords lock the account for 15 minutes. Failures all give the same generic message and
    unknown emails cost the same time as known ones, so accounts cannot be discovered by trying emails.
  * Security events are written to an audit log that never stores passwords or tokens.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from data import BASE_DIR

DB_PATH = BASE_DIR / "college.db"
IDLE_MINUTES = int(os.environ.get("ADMIN_IDLE_MINUTES", "30"))
MAX_SESSION_HOURS = int(os.environ.get("ADMIN_MAX_SESSION_HOURS", "8"))
MAX_FAILED_LOGINS = 5
LOCK_MINUTES = 15
FAIL_DELAY_SECONDS = 0.5                       # small pause after a failed login (tests set this to 0)
_SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1, "dklen": 32}
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,200}\.[^@\s.]{2,}$")
_COMMON = {"password1234", "123456789012", "qwertyuiop12", "adminadmin12", "welcome12345", "changeme1234",
           "letmein12345", "administrator1", "password12345", "iloveyou1234"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE COLLATE NOCASE, name TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1, failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT, last_login TEXT, created_at TEXT NOT NULL, password_changed_at TEXT);
CREATE TABLE IF NOT EXISTS admin_sessions (
    token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES admin_users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL, last_seen TEXT NOT NULL, expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS admin_audit (
    id INTEGER PRIMARY KEY, ts TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
    entity TEXT, entity_id TEXT, detail TEXT);
"""


@dataclass(frozen=True)
class AdminUser:
    id: int
    email: str
    name: str
    token_hash: str


# ------------------------------------------------------------------ helpers
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _parse(text: str) -> datetime:
    return datetime.fromisoformat(text)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA)
    return conn


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _audit(conn: sqlite3.Connection, actor: str, action: str, entity: str = "", entity_id: str = "", detail: str = "") -> None:
    conn.execute("INSERT INTO admin_audit (ts, actor, action, entity, entity_id, detail) VALUES (?,?,?,?,?,?)",
                 (_iso(_now()), (actor or "")[:120], action, entity, str(entity_id), (detail or "")[:500]))


def audit(actor: str, action: str, entity: str = "", entity_id: str = "", detail: str = "") -> None:
    with closing(_connect()) as conn, conn:
        _audit(conn, actor, action, entity, entity_id, detail)


# ---------------------------------------------------------------- passwords
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    b64 = lambda b: base64.b64encode(b).decode()
    return f"scrypt${_SCRYPT['n']}${_SCRYPT['r']}${_SCRYPT['p']}${b64(salt)}${b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p),
                                dklen=len(expected))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))      # used so unknown emails cost the same time as known ones


def valid_email(email: str) -> bool:
    return bool(_EMAIL.match((email or "").strip()))


def password_problems(password: str, email: str = "") -> list[str]:
    problems = []
    if len(password) < 12:
        problems.append("Use at least 12 characters.")
    if len(password) > 200:
        problems.append("Use at most 200 characters.")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        problems.append("Include both letters and numbers.")
    local = (email or "").split("@")[0].lower()
    if len(local) >= 3 and local in password.lower():
        problems.append("Do not include the name from your email address.")
    if password.lower() in _COMMON or re.fullmatch(r"(.)\1+", password or ""):
        problems.append("That password is too common.")
    return problems


# ----------------------------------------------------------------- accounts
def create_admin(email: str, password: str, name: str = "") -> int:
    """Provision an administrator (server-side only; there is no public sign-up)."""
    email = (email or "").strip().lower()
    if not valid_email(email):
        raise ValueError("Enter a valid email address.")
    problems = password_problems(password, email)
    if problems:
        raise ValueError(" ".join(problems))
    with closing(_connect()) as conn, conn:
        if conn.execute("SELECT 1 FROM admin_users WHERE email = ?", (email,)).fetchone():
            raise ValueError("An administrator with this email already exists.")
        now = _iso(_now())
        new_id = conn.execute(
            "INSERT INTO admin_users (email, name, password_hash, created_at, password_changed_at) VALUES (?,?,?,?,?)",
            (email, (name or "").strip()[:100], hash_password(password), now, now)).lastrowid
        _audit(conn, "system", "admin_created", "admin_user", new_id, email)
        return new_id


def set_password(email: str, new_password: str) -> None:
    """Server-side password reset (create_admin.py --reset-password). Ends all sessions and unlocks the account."""
    email = (email or "").strip().lower()
    problems = password_problems(new_password, email)
    if problems:
        raise ValueError(" ".join(problems))
    with closing(_connect()) as conn, conn:
        row = conn.execute("SELECT id FROM admin_users WHERE email = ?", (email,)).fetchone()
        if not row:
            raise ValueError("No administrator with this email.")
        conn.execute("UPDATE admin_users SET password_hash=?, failed_attempts=0, locked_until=NULL, password_changed_at=?"
                     " WHERE id=?", (hash_password(new_password), _iso(_now()), row["id"]))
        conn.execute("DELETE FROM admin_sessions WHERE user_id = ?", (row["id"],))
        _audit(conn, "system", "password_reset", "admin_user", row["id"], email)


def admin_count() -> int:
    with closing(_connect()) as conn:
        return conn.execute("SELECT COUNT(*) FROM admin_users").fetchone()[0]


# ----------------------------------------------------------------- sessions
def login(email: str, password: str) -> str | None:
    """Return a session token, or None. Every failure looks the same to the caller."""
    email = (email or "").strip().lower()[:254]
    password = password or ""
    with closing(_connect()) as conn, conn:
        row = conn.execute("SELECT * FROM admin_users WHERE email = ?", (email,)).fetchone()
        now = _now()
        locked = bool(row and row["locked_until"] and _parse(row["locked_until"]) > now)
        password_ok = verify_password(password, row["password_hash"] if row else _DUMMY_HASH)   # always runs once
        if row and row["is_active"] and not locked and password_ok:
            token = secrets.token_urlsafe(32)
            conn.execute("DELETE FROM admin_sessions WHERE expires_at < ?", (_iso(now),))
            conn.execute("INSERT INTO admin_sessions (token_hash, user_id, created_at, last_seen, expires_at) VALUES (?,?,?,?,?)",
                         (_token_hash(token), row["id"], _iso(now), _iso(now), _iso(now + timedelta(hours=MAX_SESSION_HOURS))))
            conn.execute("UPDATE admin_users SET failed_attempts=0, locked_until=NULL, last_login=? WHERE id=?",
                         (_iso(now), row["id"]))
            _audit(conn, email, "login", "admin_user", row["id"])
            return token
        if row and row["is_active"] and not locked:                    # a wrong password on a real account
            failures = row["failed_attempts"] + 1
            lock_until = _iso(now + timedelta(minutes=LOCK_MINUTES)) if failures >= MAX_FAILED_LOGINS else None
            conn.execute("UPDATE admin_users SET failed_attempts=?, locked_until=? WHERE id=?",
                         (0 if lock_until else failures, lock_until, row["id"]))
            _audit(conn, email, "login_failed", "admin_user", row["id"], "account locked" if lock_until else "")
        else:
            _audit(conn, email, "login_failed", "", "", "unknown, inactive or locked account")
    if FAIL_DELAY_SECONDS:
        time.sleep(FAIL_DELAY_SECONDS)
    return None


def validate(token: str | None) -> AdminUser | None:
    """The administrator behind a session token, or None if it is unknown, expired, idle or the user is disabled."""
    if not token or not isinstance(token, str):
        return None
    digest = _token_hash(token)
    with closing(_connect()) as conn, conn:
        row = conn.execute("SELECT s.user_id, s.last_seen, s.expires_at, u.email, u.name, u.is_active FROM admin_sessions s "
                           "JOIN admin_users u ON u.id = s.user_id WHERE s.token_hash = ?", (digest,)).fetchone()
        if not row:
            return None
        now = _now()
        if (_parse(row["expires_at"]) <= now or now - _parse(row["last_seen"]) > timedelta(minutes=IDLE_MINUTES)
                or not row["is_active"]):
            conn.execute("DELETE FROM admin_sessions WHERE token_hash = ?", (digest,))
            return None
        conn.execute("UPDATE admin_sessions SET last_seen = ? WHERE token_hash = ?", (_iso(now), digest))
        return AdminUser(row["user_id"], row["email"], row["name"], digest)


def require(token: str | None) -> AdminUser:
    """Authorisation check used by every administrative operation."""
    user = validate(token)
    if user is None:
        raise PermissionError("Your session has ended. Please sign in again.")
    return user


def logout(token: str | None) -> None:
    user = validate(token)
    with closing(_connect()) as conn, conn:
        if token:
            conn.execute("DELETE FROM admin_sessions WHERE token_hash = ?", (_token_hash(token),))
        if user:
            _audit(conn, user.email, "logout", "admin_user", user.id)


def logout_other_sessions(token: str) -> int:
    user = require(token)
    with closing(_connect()) as conn, conn:
        count = conn.execute("DELETE FROM admin_sessions WHERE user_id = ? AND token_hash != ?",
                             (user.id, user.token_hash)).rowcount
        _audit(conn, user.email, "logout_other_sessions", "admin_user", user.id, f"{count} ended")
    return count


def change_password(token: str, current: str, new: str) -> None:
    user = require(token)
    problems = password_problems(new, user.email)
    with closing(_connect()) as conn, conn:
        row = conn.execute("SELECT password_hash FROM admin_users WHERE id = ?", (user.id,)).fetchone()
        if not verify_password(current or "", row["password_hash"]):
            _audit(conn, user.email, "password_change_failed", "admin_user", user.id)
            raise ValueError("The current password is not correct.")
        if problems:
            raise ValueError(" ".join(problems))
        conn.execute("UPDATE admin_users SET password_hash=?, password_changed_at=? WHERE id=?",
                     (hash_password(new), _iso(_now()), user.id))
        conn.execute("DELETE FROM admin_sessions WHERE user_id = ? AND token_hash != ?", (user.id, user.token_hash))
        _audit(conn, user.email, "password_changed", "admin_user", user.id)


# --------------------------------------------------------------------- views
def recent_audit(token: str, limit: int = 40) -> list[dict]:
    require(token)
    with closing(_connect()) as conn:
        return [dict(r) for r in conn.execute("SELECT ts, actor, action, entity, entity_id, detail FROM admin_audit "
                                              "ORDER BY id DESC LIMIT ?", (int(limit),))]


def list_admins(token: str) -> list[dict]:
    require(token)
    with closing(_connect()) as conn:
        return [dict(r) for r in conn.execute("SELECT email, name, is_active, last_login, created_at FROM admin_users ORDER BY id")]
