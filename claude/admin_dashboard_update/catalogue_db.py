"""catalogue_db.py - the course catalogue lives in college.db and the running app follows it.

course_catalogue.py supplies the INITIAL rows (and any course you add to that file later, once).
After that the DATABASE is the source of truth: change a fee, a seat count, an eligibility rule or add a
course in college.db (with update_course / add_course below, or any SQLite editor) and the whole site,
including the assistant and its spoken answers, shows it on the next interaction. No restart needed.

How it stays live: app.py calls sync() at the start of every run. sync() refreshes the one shared course
list (data.COURSES) in place whenever the database file has changed.
"""
from __future__ import annotations

import copy
import json
import re
import sqlite3
from contextlib import closing
from datetime import date

from course_catalogue import COURSES
from data import BASE_DIR

DB_PATH = BASE_DIR / "college.db"
_SEED = copy.deepcopy(COURSES)               # pristine initial rows, captured before the list is synced

_JSON_LISTS = ("subjects", "procedure", "documents", "careers", "higher_studies", "specialisations")
_TEXT = ("name", "category", "level", "overview", "class12", "degree", "diploma", "semesters", "admission_mode")
_INTS = ("position", "years", "tuition", "seats", "min_pct")
_FIELDS = set(_TEXT) | set(_INTS) | set(_JSON_LISTS) | {"group", "req12", "published", "is_sample"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS courses (
    id TEXT PRIMARY KEY,
    position INTEGER NOT NULL DEFAULT 1000,
    name TEXT NOT NULL,
    grp TEXT NOT NULL DEFAULT 'Other programmes',
    category TEXT NOT NULL DEFAULT 'Other',
    level TEXT NOT NULL DEFAULT 'Undergraduate',
    years INTEGER NOT NULL DEFAULT 3,
    tuition INTEGER NOT NULL DEFAULT 0,
    seats INTEGER NOT NULL DEFAULT 0,
    min_pct INTEGER NOT NULL DEFAULT 45,
    overview TEXT DEFAULT '', class12 TEXT, degree TEXT, diploma TEXT,
    semesters TEXT DEFAULT '', admission_mode TEXT DEFAULT '',
    subjects TEXT DEFAULT '[]', procedure TEXT DEFAULT '[]', documents TEXT DEFAULT '[]',
    careers TEXT DEFAULT '[]', higher_studies TEXT DEFAULT '[]', req12 TEXT,
    is_sample INTEGER NOT NULL DEFAULT 1, source TEXT DEFAULT 'Fictional prototype data', last_updated TEXT,
    published INTEGER NOT NULL DEFAULT 1, specialisations TEXT DEFAULT '[]');
CREATE TABLE IF NOT EXISTS catalogue_meta (key TEXT PRIMARY KEY, value TEXT);
"""
_state = {"stamp": None, "problems": []}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _stamp() -> tuple:
    return tuple(p.stat().st_mtime_ns if p.exists() else 0
                 for p in (DB_PATH, DB_PATH.with_name(DB_PATH.name + "-wal")))


def _dump(value) -> str | None:
    return None if value is None else json.dumps(value, ensure_ascii=False)


# ------------------------------------------------------------------ database
def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns introduced after the first release to an existing database."""
    have = {r["name"] for r in conn.execute("PRAGMA table_info(courses)")}
    for column, ddl in (("published", "INTEGER NOT NULL DEFAULT 1"), ("specialisations", "TEXT DEFAULT '[]'")):
        if column not in have:
            conn.execute(f"ALTER TABLE courses ADD COLUMN {column} {ddl}")


def init_db() -> None:
    """Create the table and insert seed courses that were never inserted before (deleted ones stay deleted)."""
    with closing(_connect()) as conn:
        conn.executescript(_SCHEMA)
        _migrate(conn)
        conn.commit()
        row = conn.execute("SELECT value FROM catalogue_meta WHERE key = 'seeded_ids'").fetchone()
        seeded = set(json.loads(row[0])) if row else set()
        fresh = [(pos, c) for pos, c in enumerate(_SEED, start=1) if c["id"] not in seeded]
        if not fresh and row:
            return
        with conn:
            for pos, c in fresh:
                conn.execute(
                    "INSERT OR IGNORE INTO courses (id, position, name, grp, category, level, years, tuition, seats, min_pct,"
                    " overview, class12, degree, diploma, semesters, admission_mode, subjects, procedure, documents, careers,"
                    " higher_studies, req12, last_updated) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (c["id"], pos, c["name"], c["group"], c["category"], c["level"], c["years"], c["tuition"], c["seats"],
                     c["min_pct"], c["overview"], c["class12"], c["degree"], c["diploma"], c["semesters"], c["admission_mode"],
                     _dump(c["subjects"]), _dump(c["procedure"]), _dump(c["documents"]), _dump(c["careers"]),
                     _dump(c["higher_studies"]), _dump(c.get("req12")), date.today().isoformat()))
            conn.execute("INSERT OR REPLACE INTO catalogue_meta VALUES ('seeded_ids', ?)",
                         (json.dumps(sorted(seeded | {c["id"] for _, c in fresh})),))


def _course(r: sqlite3.Row) -> dict:
    def js(name, default):
        try:
            value = json.loads(r[name]) if r[name] else default
        except json.JSONDecodeError:
            return default
        return default if value is None else value

    return {
        "id": r["id"], "name": r["name"], "group": r["grp"], "category": r["category"], "level": r["level"],
        "years": int(r["years"]), "tuition": int(r["tuition"]), "seats": int(r["seats"]), "min_pct": int(r["min_pct"]),
        "overview": r["overview"] or "", "class12": r["class12"] or None, "degree": r["degree"] or None,
        "diploma": r["diploma"] or None, "semesters": r["semesters"] or "", "admission_mode": r["admission_mode"] or "",
        "subjects": js("subjects", []), "procedure": js("procedure", []), "documents": js("documents", []),
        "careers": js("careers", []), "higher_studies": js("higher_studies", []), "req12": js("req12", None),
        "specialisations": js("specialisations", []), "published": bool(r["published"]), "is_sample": bool(r["is_sample"]),
    }


def load_courses(published_only: bool = True) -> list[dict]:
    """Valid courses (by default only the PUBLISHED ones, which is what the public site and assistant use). A row with unusable values (for example text in a fee column) is skipped, not shown
    with made-up numbers, and listed by problems() so it can be fixed."""
    init_db()
    courses, bad = [], []
    with closing(_connect()) as conn:
        where = "WHERE published = 1" if published_only else ""
        for r in conn.execute(f"SELECT * FROM courses {where} ORDER BY position, rowid"):
            try:
                courses.append(_course(r))
            except (ValueError, TypeError):
                bad.append(r["id"])
    _state["problems"] = bad
    return courses


def all_courses() -> list[dict]:
    """Every course including unpublished drafts (administration only)."""
    return load_courses(published_only=False)


def course_name_taken(name: str, exclude_id: str | None = None) -> bool:
    init_db()
    with closing(_connect()) as conn:
        row = conn.execute("SELECT id FROM courses WHERE lower(name) = lower(?) AND id != ?", (name.strip(), exclude_id or "")).fetchone()
    return row is not None


def new_course_id(name: str) -> str:
    """A unique, URL-safe id made from the course name."""
    base = re.sub(r"[^a-z0-9]+", "-", name.lower().replace("&", " and ")).strip("-")[:40] or "course"
    init_db()
    with closing(_connect()) as conn:
        taken = {r[0] for r in conn.execute("SELECT id FROM courses")}
    candidate, n = base, 2
    while candidate in taken:
        candidate, n = f"{base}-{n}", n + 1
    return candidate


def delete_course_row(course_id: str) -> None:
    init_db()
    with closing(_connect()) as conn, conn:
        if conn.execute("DELETE FROM courses WHERE id = ?", (course_id,)).rowcount == 0:
            raise ValueError(f"No course with id '{course_id}'")


def problems() -> list[str]:
    """Ids of course rows skipped at the last refresh because their values were not usable."""
    return list(_state["problems"])


def sync(target: list | None = None) -> bool:
    """Refresh the shared course list in place if college.db changed. Returns True when it was refreshed."""
    target = COURSES if target is None else target
    if _state["stamp"] is not None and _stamp() == _state["stamp"]:
        return False
    rows = load_courses()
    if rows:                                        # never leave the site with an empty catalogue
        target[:] = rows
    _state["stamp"] = _stamp()
    return True


# ------------------------------------------------------------ editing helpers
def update_course(course_id: str, **fields) -> None:
    """Change fields of an existing course, e.g. update_course('bca', tuition=75000, seats=100)."""
    unknown = set(fields) - _FIELDS
    if unknown:
        raise ValueError(f"Unknown field(s): {sorted(unknown)}. Allowed: {sorted(_FIELDS)}")
    sets, values = [], []
    for key, value in fields.items():
        column = "grp" if key == "group" else key
        if key in _INTS:
            value = int(value)
            if value < 0 or (key == "min_pct" and value > 100) or (key == "years" and value < 1):
                raise ValueError(f"{key}: {value} is out of range")
        elif key in _JSON_LISTS:
            if not isinstance(value, (list, tuple)):
                raise ValueError(f"{key} must be a list")
            value = _dump(list(value))
        elif key == "req12":
            value = _dump(value)
        elif key in ("published", "is_sample"):
            value = 1 if value else 0
        sets.append(f"{column} = ?")
        values.append(value)
    if not sets:
        return
    init_db()
    with closing(_connect()) as conn, conn:
        done = conn.execute(f"UPDATE courses SET {', '.join(sets)}, last_updated = ? WHERE id = ?",
                            (*values, date.today().isoformat(), course_id))
        if done.rowcount == 0:
            raise ValueError(f"No course with id '{course_id}'")


def add_course(course_id: str, name: str, *, group: str, category: str, years: int, tuition: int, seats: int,
               department: str | None = None, **optional) -> None:
    """Add a course. Give `department` (an existing department name) so it gets faculty and a department link."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", course_id):
        raise ValueError("course_id must use lowercase letters, digits and hyphens, e.g. 'bsc-geology'")
    init_db()
    with closing(_connect()) as conn, conn:
        if conn.execute("SELECT 1 FROM courses WHERE id = ?", (course_id,)).fetchone():
            raise ValueError(f"A course with id '{course_id}' already exists")
        position = conn.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM courses").fetchone()[0]
        conn.execute("INSERT INTO courses (id, position, name, grp, category, years, tuition, seats, last_updated)"
                     " VALUES (?,?,?,?,?,?,?,?,?)", (course_id, position, name, group, category, int(years), int(tuition),
                                                    int(seats), date.today().isoformat()))
    if optional:
        update_course(course_id, **optional)
    if department:
        import faculty_db                                   # imported here to avoid a circular import
        faculty_db.link_course(course_id, department)
