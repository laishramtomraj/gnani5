"""registration_db.py - saving and finding registrations (SQLite, Python standard library only).

Why a separate file (registrations.db) and not college.db:
  college.db holds the course/faculty seed data and may be rebuilt. Student registrations are personal data
  and must survive that, so they live in their own file that you can protect, back up or delete separately.

Rules this module enforces:
  * Every new registration starts as 'Submitted'. Callers cannot choose a status when submitting.
  * Status changes go through record_status_change(), which no website page calls. It exists for a future
    admissions-officer tool. The College Admission Assistant must never call it.
  * A registration can be read back only with its reference number AND the email it was registered with
    (lookup_status). Failed attempts are counted and locked out, and the reason is never revealed.
  * All SQL uses ? placeholders. Personal details are never written to the log.

Deployment: set the environment variable COLLEGE_REGISTRATIONS_DB to a full file path to store the database
somewhere else (for example outside the project folder). Nothing else needs configuring.
"""
from __future__ import annotations

import hmac
import json
import logging
import os
import re
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from data import BASE_DIR
from registration_schema import ALL_FIELDS, INITIAL_STATUS, STATUSES, STATUS_MEANINGS

logger = logging.getLogger("registration")

ENV_DB_PATH = "COLLEGE_REGISTRATIONS_DB"
REFERENCE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"      # no 0/O, 1/I/L: easier to read out and copy
REFERENCE_RE = re.compile(r"REG-\d{4}-[A-Z2-9]{8}")
TOKEN_RE = re.compile(r"[A-Za-z0-9\-]{16,64}")

MAX_FAILED_LOOKUPS = 5           # wrong attempts for one reference before it is locked
LOCK_MINUTES = 15
THROTTLE_WINDOW_MINUTES = 10     # across all references
THROTTLE_MAX_FAILURES = 30

_SCHEMA = """
CREATE TABLE IF NOT EXISTS registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reference TEXT NOT NULL UNIQUE,
    submission_token TEXT NOT NULL UNIQUE,
    course_id TEXT NOT NULL,
    course_name TEXT NOT NULL,
    status TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    mobile TEXT NOT NULL,
    date_of_birth TEXT,
    gender TEXT,
    state TEXT,
    qualification_route TEXT NOT NULL,
    class10_percentage REAL,
    class12_board TEXT,
    class12_stream TEXT,
    class12_subjects TEXT,
    class12_other_subjects TEXT,
    class12_result_status TEXT,
    class12_percentage REAL,
    class12_year INTEGER,
    diploma_branch TEXT,
    diploma_percentage REAL,
    diploma_year INTEGER,
    degree_name TEXT,
    degree_discipline TEXT,
    degree_percentage REAL,
    degree_year INTEGER,
    entrance_exam_details TEXT,
    declaration_accurate INTEGER NOT NULL,
    privacy_acknowledged INTEGER NOT NULL,
    eligibility_outcome TEXT NOT NULL,
    eligibility_details TEXT NOT NULL,
    eligibility_acknowledged INTEGER NOT NULL DEFAULT 0,
    course_data_is_sample INTEGER NOT NULL DEFAULT 1,
    failed_lookups INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT
);
CREATE TABLE IF NOT EXISTS status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    registration_id INTEGER NOT NULL REFERENCES registrations(id),
    status TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    changed_by TEXT NOT NULL,
    note TEXT
);
CREATE TABLE IF NOT EXISTS lookup_failures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    failed_at TEXT NOT NULL
);
"""


class RegistrationStorageError(Exception):
    """The registration could not be saved or read. Nothing was stored."""


class LookupRefused(Exception):
    """A status lookup was refused. `reason` is for tests and logs; users always see one generic message."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


# --------------------------------------------------------------- connection
def db_path() -> Path:
    override = os.environ.get(ENV_DB_PATH)
    return Path(override) if override else BASE_DIR / "registrations.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA)
    return conn


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def new_reference(year: int | None = None) -> str:
    """Random reference such as REG-2026-K7M4QX9P. Random, not sequential, so it cannot be guessed by counting."""
    code = "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(8))
    return f"REG-{year or _now().year}-{code}"


# ------------------------------------------------------------------- submit
def _row_from_record(record: dict) -> dict:
    row: dict = {}
    for field in ALL_FIELDS:
        value = record.get(field)
        if isinstance(value, (list, tuple)):
            value = json.dumps(list(value), ensure_ascii=False)
        elif isinstance(value, bool):
            value = int(value)
        row[field] = value
    for required in ("full_name", "email", "mobile", "qualification_route"):
        if not row.get(required):
            raise ValueError(f"Missing required field: {required}")
    row["course_id"] = record["course_id"]
    row["course_name"] = record["course_name"]
    row["eligibility_outcome"] = record["eligibility_outcome"]
    row["eligibility_details"] = json.dumps(record.get("eligibility_details") or [], ensure_ascii=False)
    row["eligibility_acknowledged"] = int(bool(record.get("eligibility_acknowledged")))
    row["course_data_is_sample"] = int(bool(record.get("course_data_is_sample", True)))
    return row


def _confirmation(row: sqlite3.Row, already: bool) -> dict:
    return {
        "reference": row["reference"],
        "status": row["status"],
        "course_id": row["course_id"],
        "course_name": row["course_name"],
        "submitted_at": row["submitted_at"],
        "already_submitted": already,
    }


def create_registration(record: dict, submission_token: str) -> dict:
    """Save a registration and return its confirmation.

    `submission_token` identifies one filling-in of the form. Sending the same token again (a double click,
    a page rerun) returns the registration that was already saved instead of creating a second one.
    Raises RegistrationStorageError if nothing could be saved. The caller must then NOT show a reference.
    """
    if not TOKEN_RE.fullmatch(submission_token or ""):
        raise ValueError("Invalid submission token")
    row = _row_from_record(record)
    row.update(submission_token=submission_token, status=INITIAL_STATUS)
    stamp = _iso(_now())
    row.update(submitted_at=stamp, updated_at=stamp)
    columns = ", ".join(row)
    marks = ", ".join(f":{c}" for c in row)
    try:
        with closing(_connect()) as conn:
            existing = conn.execute("SELECT * FROM registrations WHERE submission_token = ?", (submission_token,)).fetchone()
            if existing:
                return _confirmation(existing, already=True)
            for _ in range(8):
                row["reference"] = new_reference()
                columns_all = columns + ", reference"
                marks_all = marks + ", :reference"
                try:
                    with conn:                       # one transaction: both rows are saved, or neither
                        cursor = conn.execute(f"INSERT INTO registrations ({columns_all}) VALUES ({marks_all})", row)
                        conn.execute(
                            "INSERT INTO status_history (registration_id, status, changed_at, changed_by, note) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (cursor.lastrowid, INITIAL_STATUS, stamp, "system", "Registration submitted by the student."),
                        )
                    saved = conn.execute("SELECT * FROM registrations WHERE id = ?", (cursor.lastrowid,)).fetchone()
                    logger.info("registration saved reference=%s course=%s", saved["reference"], saved["course_id"])
                    return _confirmation(saved, already=False)
                except sqlite3.IntegrityError as exc:
                    again = conn.execute("SELECT * FROM registrations WHERE submission_token = ?", (submission_token,)).fetchone()
                    if again:                         # a parallel request saved the same submission first
                        return _confirmation(again, already=True)
                    if "registrations.reference" in str(exc):
                        continue                      # extremely unlikely reference clash: try another
                    raise
        raise RegistrationStorageError("Could not create a unique reference number.")
    except sqlite3.Error as exc:
        logger.error("registration not saved (%s)", type(exc).__name__)
        raise RegistrationStorageError("The registration could not be saved.") from exc


# ----------------------------------------------------------- status lookup
def _recent_failures(conn: sqlite3.Connection, now: datetime) -> int:
    since = _iso(now - timedelta(minutes=THROTTLE_WINDOW_MINUTES))
    return conn.execute("SELECT COUNT(*) FROM lookup_failures WHERE failed_at >= ?", (since,)).fetchone()[0]


def lookup_status(reference: str, email: str) -> dict:
    """Return the status of ONE registration, but only for the reference + registered email pair.

    Raises LookupRefused for every kind of failure (unknown reference, wrong email, locked, throttled).
    The caller must show the same generic message for all of them so nothing about other students leaks.
    """
    ref = (reference or "").strip().upper()
    mail = (email or "").strip().lower()
    now = _now()
    try:
        with closing(_connect()) as conn:
            if _recent_failures(conn, now) >= THROTTLE_MAX_FAILURES:
                raise LookupRefused("throttled")
            row = None
            if REFERENCE_RE.fullmatch(ref):
                row = conn.execute("SELECT * FROM registrations WHERE reference = ?", (ref,)).fetchone()
            if row is not None and row["locked_until"] and datetime.fromisoformat(row["locked_until"]) > now:
                raise LookupRefused("locked")

            verified = row is not None and bool(mail) and hmac.compare_digest(row["email"].encode(), mail.encode())
            if not verified:
                with conn:
                    conn.execute("INSERT INTO lookup_failures (failed_at) VALUES (?)", (_iso(now),))
                    conn.execute("DELETE FROM lookup_failures WHERE failed_at < ?", (_iso(now - timedelta(days=1)),))
                    if row is not None:
                        failed = row["failed_lookups"] + 1
                        if failed >= MAX_FAILED_LOOKUPS:
                            conn.execute("UPDATE registrations SET failed_lookups = 0, locked_until = ? WHERE id = ?",
                                         (_iso(now + timedelta(minutes=LOCK_MINUTES)), row["id"]))
                        else:
                            conn.execute("UPDATE registrations SET failed_lookups = ? WHERE id = ?", (failed, row["id"]))
                raise LookupRefused("not_verified")

            with conn:
                conn.execute("UPDATE registrations SET failed_lookups = 0, locked_until = NULL WHERE id = ?", (row["id"],))
            history = [
                {"status": h["status"], "changed_at": h["changed_at"], "note": h["note"]}
                for h in conn.execute(
                    "SELECT status, changed_at, note FROM status_history WHERE registration_id = ? ORDER BY id", (row["id"],))
            ]
            return {
                "reference": row["reference"],
                "applicant_name": row["full_name"],
                "course_id": row["course_id"],
                "course_name": row["course_name"],
                "status": row["status"],
                "status_meaning": STATUS_MEANINGS.get(row["status"], ""),
                "submitted_at": row["submitted_at"],
                "updated_at": row["updated_at"],
                "history": history,
            }
    except sqlite3.Error as exc:
        logger.error("status lookup failed (%s)", type(exc).__name__)
        raise RegistrationStorageError("The registration could not be read.") from exc


# ------------------------------------------------- status changes (not on any page)
def record_status_change(reference: str, new_status: str, changed_by: str, note: str = "") -> None:
    """Change a registration's status. FOR A FUTURE ADMISSIONS-OFFICER TOOL ONLY.

    No page of this website calls this function, and the College Admission Assistant must never call it.
    Registration submission, eligibility checks and approval are deliberately separate things.
    """
    if new_status not in STATUSES:
        raise ValueError(f"Unknown status: {new_status}")
    if not (changed_by or "").strip():
        raise ValueError("changed_by is required")
    stamp = _iso(_now())
    try:
        with closing(_connect()) as conn, conn:
            row = conn.execute("SELECT id FROM registrations WHERE reference = ?", ((reference or "").strip().upper(),)).fetchone()
            if row is None:
                raise ValueError("Unknown reference")
            conn.execute("UPDATE registrations SET status = ?, updated_at = ? WHERE id = ?", (new_status, stamp, row["id"]))
            conn.execute(
                "INSERT INTO status_history (registration_id, status, changed_at, changed_by, note) VALUES (?, ?, ?, ?, ?)",
                (row["id"], new_status, stamp, changed_by.strip(), note.strip() or None),
            )
        logger.info("status changed reference=%s status=%s", reference, new_status)
    except sqlite3.Error as exc:
        logger.error("status change failed (%s)", type(exc).__name__)
        raise RegistrationStorageError("The status could not be changed.") from exc
