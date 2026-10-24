"""content_db.py - editable website content (draft / publish), achievements and enquiries, stored in college.db.

Public pages never read these tables directly. sync() copies the PUBLISHED values into the shared objects the
pages already use (data.COLLEGE and data.ACHIEVEMENTS), in place, whenever the database file changes. Drafts and
unpublished records therefore never reach the public site.
"""
from __future__ import annotations

import copy
import csv
import io
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import date, datetime, timezone
from urllib.parse import urlparse

from data import ACHIEVEMENTS, BASE_DIR, COLLEGE

DB_PATH = BASE_DIR / "college.db"
ACHIEVEMENT_IMAGES = BASE_DIR / "assets" / "achievements"
_ORIGINAL = copy.deepcopy(COLLEGE)                   # the values written in data.py, before any published override


# ------------------------------------------------------------------- fields
@dataclass(frozen=True)
class Field:
    key: str
    label: str
    kind: str                       # text | area | phone | email | url | bool
    max_len: int = 200
    required: bool = False
    default: object = ""
    help: str = ""


DEFAULT_INTRO = ("A modern learning environment built around education, innovation, "
                 "student development, and real-world opportunities.")
_social = lambda key, label: Field(key, label, "url", 200, help="Start with https://")
FIELDS: dict[str, Field] = {f.key: f for f in [
    Field("name", "College name", "text", 120, True, _ORIGINAL.get("name") or ""),
    Field("description", "Introduction and description", "area", 2000),
    Field("vision", "Vision", "area", 1000),
    Field("mission", "Mission", "area", 1500),
    Field("address", "Address", "area", 300, default=_ORIGINAL.get("address") or ""),
    Field("phone", "General enquiry phone", "phone", 30, default=_ORIGINAL.get("phone") or ""),
    Field("admissions_phone", "Admissions helpline", "phone", 30),
    Field("email", "General email", "email", 120, default=_ORIGINAL.get("email") or ""),
    Field("admissions_email", "Admissions email", "email", 120),
    Field("office_hours", "Office hours", "text", 200, default=_ORIGINAL.get("office_hours") or ""),
    _social("facebook", "Facebook"), _social("instagram", "Instagram"), _social("linkedin", "LinkedIn"),
    _social("youtube", "YouTube"), _social("x_twitter", "X (Twitter)"),
    Field("home_headline", "Homepage headline", "area", 120, True, "Discover Your Future.\nBegin Your Journey.",
          "Two short lines work best."),
    Field("home_intro", "Homepage introduction", "area", 400, True, DEFAULT_INTRO),
    Field("home_why_heading", "Homepage heading: why choose us", "text", 120, True, "Education That Prepares You for What's Next"),
    Field("home_achievements_heading", "Homepage heading: achievements", "text", 80, True, "Our Achievements"),
    Field("home_programmes_heading", "Homepage heading: programmes", "text", 80, True, "Explore Courses"),
    Field("accreditations_text", "About Us: accreditations and approvals", "area", 1500),
    Field("show_prototype_notice", "Show 'illustrative prototype data' notices", "bool", default=True,
          help="Switch off only after every course, fee, seat and faculty detail on the site has been verified."),
]}
FORM_COLLEGE = ["name", "description", "vision", "mission", "address", "phone", "email", "office_hours"]
FORM_CONTACT = ["address", "phone", "admissions_phone", "email", "admissions_email", "office_hours",
                "facebook", "instagram", "linkedin", "youtube", "x_twitter"]
FORM_WEBSITE = ["home_headline", "home_intro", "home_why_heading", "home_achievements_heading",
                "home_programmes_heading", "accreditations_text", "show_prototype_notice"]
_PHONE = re.compile(r"^\+?[\d\s().-]{7,25}$")
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,200}\.[^@\s.]{2,}$")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS site_content (key TEXT PRIMARY KEY, value TEXT, draft TEXT, updated_at TEXT, updated_by TEXT);
CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY, title TEXT NOT NULL, highlight TEXT DEFAULT '', description TEXT DEFAULT '',
    category TEXT DEFAULT 'General', achieved_on TEXT DEFAULT '', published INTEGER NOT NULL DEFAULT 0,
    created_at TEXT, updated_at TEXT, updated_by TEXT);
CREATE TABLE IF NOT EXISTS enquiries (
    id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, name TEXT NOT NULL, email TEXT DEFAULT '', phone TEXT DEFAULT '',
    course_id TEXT DEFAULT '', course_name TEXT DEFAULT '', message TEXT DEFAULT '', status TEXT NOT NULL DEFAULT 'New',
    admin_note TEXT DEFAULT '', updated_at TEXT, updated_by TEXT);
"""
_state = {"stamp": None}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def validate_value(field: Field, raw) -> tuple[object, str | None]:
    """-> (clean value, error message or None)."""
    if field.kind == "bool":
        return bool(raw), None
    text = _CONTROL.sub("", raw if isinstance(raw, str) else ("" if raw is None else str(raw))).strip()
    if len(text) > field.max_len:
        return text, f"{field.label} must be at most {field.max_len} characters."
    if not text:
        return "", (f"{field.label} is required." if field.required else None)
    if field.kind == "phone":
        digits = re.sub(r"\D", "", text)
        if not _PHONE.match(text) or not 7 <= len(digits) <= 15:
            return text, f"{field.label}: enter a valid phone number, for example +91 98765 43210."
    elif field.kind == "email" and not _EMAIL.match(text):
        return text, f"{field.label}: enter a valid email address."
    elif field.kind == "url":
        parsed = urlparse(text)
        if parsed.scheme != "https" or "." not in parsed.netloc or re.search(r"\s", text):
            return text, f"{field.label}: enter a full link starting with https://"
    return text, None


# ------------------------------------------------------------ site content
def _typed(field: Field, raw: str | None):
    if raw is None:
        return field.default
    return raw == "1" if field.kind == "bool" else raw


def _stored(field: Field, value) -> str:
    return ("1" if value else "0") if field.kind == "bool" else str(value)


def _rows() -> dict[str, sqlite3.Row]:
    with closing(_connect()) as conn:
        return {r["key"]: r for r in conn.execute("SELECT * FROM site_content")}


def effective_values() -> dict:
    """What the public site shows: the published value if there is one, else the original / default."""
    rows = _rows()
    return {k: _typed(f, rows[k]["value"] if k in rows else None) for k, f in FIELDS.items()}


def form_values(keys: list[str]) -> tuple[dict, bool]:
    """Values to show in an editing form (the draft where one exists) and whether any key has an unpublished draft."""
    rows, effective = _rows(), effective_values()
    out, drafted = {}, False
    for k in keys:
        f = FIELDS[k]
        if k in rows and rows[k]["draft"] is not None:
            out[k], drafted = _typed(f, rows[k]["draft"]), True
        else:
            out[k] = effective[k]
    return out, drafted


def save_drafts(values: dict, actor: str) -> None:
    with closing(_connect()) as conn, conn:
        for k, v in values.items():
            conn.execute("INSERT INTO site_content (key, draft, updated_at, updated_by) VALUES (?,?,?,?) "
                         "ON CONFLICT(key) DO UPDATE SET draft = excluded.draft, updated_at = excluded.updated_at, "
                         "updated_by = excluded.updated_by", (k, _stored(FIELDS[k], v), _now(), actor))


def publish_keys(keys: list[str], actor: str) -> int:
    with closing(_connect()) as conn, conn:
        n = 0
        for k in keys:
            n += conn.execute("UPDATE site_content SET value = draft, draft = NULL, updated_at = ?, updated_by = ? "
                              "WHERE key = ? AND draft IS NOT NULL", (_now(), actor, k)).rowcount
        return n


def discard_drafts(keys: list[str]) -> None:
    with closing(_connect()) as conn, conn:
        for k in keys:
            conn.execute("UPDATE site_content SET draft = NULL WHERE key = ?", (k,))


def pending_drafts() -> int:
    with closing(_connect()) as conn:
        return conn.execute("SELECT COUNT(*) FROM site_content WHERE draft IS NOT NULL").fetchone()[0]


# ---------------------------------------------------------- achievements
_DATE = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$")


def clean_achievement(rec: dict) -> tuple[dict, dict]:
    clean, errors = {}, {}
    def text(key, label, limit, required=False, default=""):
        value = _CONTROL.sub("", str(rec.get(key) or "")).strip() or default
        if required and not value:
            errors[key] = f"{label} is required."
        elif len(value) > limit:
            errors[key] = f"{label} must be at most {limit} characters."
        clean[key] = value
    text("title", "Title", 150, True)
    text("highlight", "Highlight value", 40)
    text("description", "Description", 1000)
    text("category", "Category", 60, default="General")
    when = str(rec.get("achieved_on") or "").strip()
    if when:
        m = _DATE.match(when)
        try:
            ok = bool(m) and 1900 <= int(m.group(1)) <= date.today().year + 1
            if ok and m.group(3):
                date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            elif ok and m.group(2):
                ok = 1 <= int(m.group(2)) <= 12
        except ValueError:
            ok = False
        if not ok:
            errors["achieved_on"] = "Date must be a year (2024), a month (2024-06) or a full date (2024-06-30)."
    clean["achieved_on"] = when
    return clean, errors


def title_taken(title: str, achieved_on: str, exclude_id: int | None = None) -> bool:
    with closing(_connect()) as conn:
        return conn.execute("SELECT 1 FROM achievements WHERE lower(title) = lower(?) AND achieved_on = ? AND id != ?",
                            (title, achieved_on, exclude_id or 0)).fetchone() is not None


def list_achievements(published_only: bool = False) -> list[dict]:
    with closing(_connect()) as conn:
        where = "WHERE published = 1" if published_only else ""
        return [dict(r, published=bool(r["published"])) for r in
                conn.execute(f"SELECT * FROM achievements {where} ORDER BY achieved_on DESC, id DESC")]


def get_achievement(achievement_id: int) -> dict | None:
    with closing(_connect()) as conn:
        r = conn.execute("SELECT * FROM achievements WHERE id = ?", (achievement_id,)).fetchone()
    return dict(r, published=bool(r["published"])) if r else None


def save_achievement(clean: dict, published: bool, actor: str, achievement_id: int | None = None) -> int:
    with closing(_connect()) as conn, conn:
        values = (clean["title"], clean["highlight"], clean["description"], clean["category"], clean["achieved_on"],
                  1 if published else 0, _now(), actor)
        if achievement_id is None:
            return conn.execute("INSERT INTO achievements (title, highlight, description, category, achieved_on, published,"
                                " updated_at, updated_by, created_at) VALUES (?,?,?,?,?,?,?,?,?)", values + (_now(),)).lastrowid
        if conn.execute("UPDATE achievements SET title=?, highlight=?, description=?, category=?, achieved_on=?, published=?,"
                        " updated_at=?, updated_by=? WHERE id=?", values + (achievement_id,)).rowcount == 0:
            raise ValueError("That achievement no longer exists.")
        return achievement_id


def set_achievement_published(achievement_id: int, published: bool, actor: str) -> None:
    with closing(_connect()) as conn, conn:
        if conn.execute("UPDATE achievements SET published=?, updated_at=?, updated_by=? WHERE id=?",
                        (1 if published else 0, _now(), actor, achievement_id)).rowcount == 0:
            raise ValueError("That achievement no longer exists.")


def delete_achievement(achievement_id: int) -> None:
    with closing(_connect()) as conn, conn:
        if conn.execute("DELETE FROM achievements WHERE id = ?", (achievement_id,)).rowcount == 0:
            raise ValueError("That achievement no longer exists.")


def achievement_image(achievement_id: int):
    return next(ACHIEVEMENT_IMAGES.glob(f"{achievement_id}.*"), None) if ACHIEVEMENT_IMAGES.exists() else None


def public_achievements() -> list[dict]:
    out = []
    for a in list_achievements(published_only=True):
        year = (a["achieved_on"] or "")[:4]
        out.append({"id": a["id"], "label": a["title"], "value": a["highlight"] or year or a["category"],
                    "source": a["description"], "category": a["category"], "date": a["achieved_on"],
                    "image": achievement_image(a["id"])})
    return out


# ------------------------------------------------------------- enquiries
STATUSES = ("New", "In review", "Contacted", "Closed")


def enquiry_ref(enquiry_id: int) -> str:
    return f"ENQ-{enquiry_id:05d}"


def submit_enquiry(name: str, email: str = "", phone: str = "", course_id: str = "", course_name: str = "",
                   message: str = "") -> str:
    """The write path for a FUTURE public registration/enquiry form (nothing on the site calls it yet).
    It validates every value and returns the reference number."""
    name = _CONTROL.sub("", name or "").strip()
    if not name or len(name) > 120:
        raise ValueError("Name is required (at most 120 characters).")
    email = (email or "").strip()
    if email and not _EMAIL.match(email):
        raise ValueError("Enter a valid email address.")
    phone = (phone or "").strip()
    if phone and (not _PHONE.match(phone) or not 7 <= len(re.sub(r"\D", "", phone)) <= 15):
        raise ValueError("Enter a valid phone number.")
    if not email and not phone:
        raise ValueError("Give an email address or a phone number.")
    message = _CONTROL.sub("", message or "").strip()[:2000]
    with closing(_connect()) as conn, conn:
        new_id = conn.execute("INSERT INTO enquiries (created_at, name, email, phone, course_id, course_name, message)"
                              " VALUES (?,?,?,?,?,?,?)", (_now(), name, email, phone, course_id[:60], course_name[:150], message)).lastrowid
    return enquiry_ref(new_id)


def _like(text: str) -> str:
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def list_enquiries(search: str = "", status: str | None = None, course: str | None = None,
                   date_from: str | None = None, date_to: str | None = None) -> list[dict]:
    where, args = [], []
    if search.strip():
        pattern = _like(search.strip())
        ref_digits = re.sub(r"\D", "", search)
        where.append("(name LIKE ? ESCAPE '\\' OR email LIKE ? ESCAPE '\\' OR phone LIKE ? ESCAPE '\\' OR message LIKE ? ESCAPE '\\'"
                     " OR course_name LIKE ? ESCAPE '\\'" + (" OR id = ?" if ref_digits else "") + ")")
        args += [pattern] * 5 + ([int(ref_digits)] if ref_digits else [])
    if status and status in STATUSES:
        where.append("status = ?"); args.append(status)
    if course:
        where.append("course_id = ?"); args.append(course)
    if date_from:
        where.append("substr(created_at, 1, 10) >= ?"); args.append(date_from)
    if date_to:
        where.append("substr(created_at, 1, 10) <= ?"); args.append(date_to)
    sql = "SELECT * FROM enquiries" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY id DESC"
    with closing(_connect()) as conn:
        return [dict(r, ref=enquiry_ref(r["id"])) for r in conn.execute(sql, args)]


def get_enquiry(enquiry_id: int) -> dict | None:
    with closing(_connect()) as conn:
        r = conn.execute("SELECT * FROM enquiries WHERE id = ?", (enquiry_id,)).fetchone()
    return dict(r, ref=enquiry_ref(r["id"])) if r else None


def set_enquiry_status(enquiry_id: int, status: str, note: str, actor: str) -> None:
    if status not in STATUSES:
        raise ValueError("Choose a valid status.")
    with closing(_connect()) as conn, conn:
        if conn.execute("UPDATE enquiries SET status=?, admin_note=?, updated_at=?, updated_by=? WHERE id=?",
                        (status, _CONTROL.sub("", note or "").strip()[:1000], _now(), actor, enquiry_id)).rowcount == 0:
            raise ValueError("That record no longer exists.")


def enquiry_counts() -> dict:
    with closing(_connect()) as conn:
        total = conn.execute("SELECT COUNT(*) FROM enquiries").fetchone()[0]
        new = conn.execute("SELECT COUNT(*) FROM enquiries WHERE status = 'New'").fetchone()[0]
    return {"total": total, "new": new}


def _safe_cell(value) -> str:
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text       # blocks spreadsheet formula injection


def enquiries_csv(rows: list[dict]) -> str:
    columns = ["ref", "created_at", "name", "email", "phone", "course_name", "message", "status", "admin_note", "updated_at"]
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(columns)
    for r in rows:
        writer.writerow([_safe_cell(r.get(c)) for c in columns])
    return out.getvalue()


# -------------------------------------------------------------- public sync
def _stamp() -> tuple:
    return tuple(p.stat().st_mtime_ns if p.exists() else 0 for p in (DB_PATH, DB_PATH.with_name(DB_PATH.name + "-wal")))


def sync() -> bool:
    """Copy the published content into data.COLLEGE and data.ACHIEVEMENTS (in place) when college.db changed."""
    if _state["stamp"] is not None and _stamp() == _state["stamp"]:
        return False
    values = effective_values()
    for k, v in values.items():
        COLLEGE[k] = (v or _ORIGINAL.get(k)) if k == "name" else (v or None) if k in _ORIGINAL else v
    ACHIEVEMENTS[:] = public_achievements()
    _state["stamp"] = _stamp()
    return True


def text(key: str):
    """A published content value for use in a public page, falling back to its default."""
    field, value = FIELDS[key], COLLEGE.get(key)
    if field.kind == "bool":
        return field.default if value is None else bool(value)
    return value if value else field.default
