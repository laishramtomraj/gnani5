"""faculty_db.py - faculty tables, seeding and queries (SQLite, Python standard library).

Tables: departments, department_courses (links to course ids in data.py),
subjects, faculty, faculty_subjects. The database file is created automatically.
On every start the seed data is SYNCED ADDITIVELY: missing departments, course links and
faculty are inserted; records that already exist are never modified or deleted.
Courses come from the live course list (data.COURSES, kept in step with college.db by catalogue_db). A course
without a department is allowed: it is reported by unlinked_courses() and linked with link_course().
"""
import sqlite3
import zlib
from contextlib import closing

from catalogue_seed import EXTRA_COURSE_LINKS, EXTRA_DEPARTMENTS, EXTRA_FACULTY
from data import BASE_DIR, COURSES
from faculty_seed import DEPARTMENTS, FACULTY_SAMPLE

DB_PATH = BASE_DIR / "college.db"

_ALL_DEPARTMENTS = DEPARTMENTS + EXTRA_DEPARTMENTS
_ALL_FACULTY = FACULTY_SAMPLE + EXTRA_FACULTY

_SCHEMA = """
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, position INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS department_courses (
    department_id INTEGER NOT NULL REFERENCES departments(id),
    course_id TEXT NOT NULL, PRIMARY KEY (department_id, course_id));
CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL,
    department_id INTEGER NOT NULL REFERENCES departments(id), UNIQUE (name, department_id));
CREATE TABLE IF NOT EXISTS faculty (
    id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
    qualifications TEXT, designation TEXT NOT NULL, post TEXT,
    department_id INTEGER NOT NULL REFERENCES departments(id), specialization TEXT,
    teaching_years INTEGER, industry_years INTEGER, research_interests TEXT,
    publications TEXT, patents TEXT, projects TEXT, certifications TEXT, achievements TEXT,
    email TEXT, phone TEXT, office TEXT, consultation_hours TEXT,
    is_sample INTEGER NOT NULL DEFAULT 1, source TEXT, last_updated TEXT);
CREATE TABLE IF NOT EXISTS faculty_subjects (
    faculty_id INTEGER NOT NULL REFERENCES faculty(id),
    subject_id INTEGER NOT NULL REFERENCES subjects(id), PRIMARY KEY (faculty_id, subject_id));
"""

_FACULTY_COLUMNS = (
    "slug", "name", "qualifications", "designation", "post", "specialization",
    "teaching_years", "industry_years", "research_interests", "publications", "patents",
    "projects", "certifications", "achievements", "email", "phone", "office",
    "consultation_hours", "is_sample", "source", "last_updated",
)
_RANK = {"Professor": 0, "Associate Professor": 1, "Assistant Professor": 2, "Lecturer": 3}


def _course_names() -> dict[str, str]:
    return {c["id"]: c["name"] for c in COURSES}          # always the current course list


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _department_links() -> dict[str, list[str]]:
    """department name -> course ids from the seed data."""
    links = {name: list(ids) for name, ids in _ALL_DEPARTMENTS}
    for name, ids in EXTRA_COURSE_LINKS.items():
        if name not in links:
            raise ValueError(f"EXTRA_COURSE_LINKS: unknown department '{name}'")
        links[name] += [i for i in ids if i not in links[name]]
    return links


def _signature() -> int:
    payload = repr((_ALL_DEPARTMENTS, sorted(EXTRA_COURSE_LINKS.items()), [r["slug"] for r in _ALL_FACULTY]))
    return zlib.crc32(payload.encode()) & 0x7FFFFFFF


def _sync(conn: sqlite3.Connection) -> None:
    links = _department_links()
    dept_ids = {}
    for position, name in enumerate(links, start=1):
        row = conn.execute("SELECT id FROM departments WHERE name = ?", (name,)).fetchone()
        dept_ids[name] = row[0] if row else conn.execute(
            "INSERT INTO departments (name, position) VALUES (?, ?)", (name, position)).lastrowid
        conn.executemany("INSERT OR IGNORE INTO department_courses VALUES (?, ?)",
                         [(dept_ids[name], c) for c in links[name]])

    columns = ", ".join(_FACULTY_COLUMNS + ("department_id",))
    marks = ", ".join(f":{c}" for c in _FACULTY_COLUMNS + ("department_id",))
    for rec in _ALL_FACULTY:
        if conn.execute("SELECT 1 FROM faculty WHERE slug = ?", (rec["slug"],)).fetchone():
            continue                                    # existing faculty are never modified
        dept_id = dept_ids[rec["department"]]
        row = {c: rec[c] for c in _FACULTY_COLUMNS} | {"department_id": dept_id}
        faculty_id = conn.execute(f"INSERT INTO faculty ({columns}) VALUES ({marks})", row).lastrowid
        for subject in rec["subjects"]:
            conn.execute("INSERT OR IGNORE INTO subjects (name, department_id) VALUES (?, ?)",
                         (subject, dept_id))
            subject_id = conn.execute("SELECT id FROM subjects WHERE name = ? AND department_id = ?",
                                      (subject, dept_id)).fetchone()[0]
            conn.execute("INSERT OR IGNORE INTO faculty_subjects VALUES (?, ?)", (faculty_id, subject_id))


def init_db() -> None:
    """Create tables and sync the seed data (only when the seed data or catalogue changed)."""
    with closing(_connect()) as conn:
        conn.executescript(_SCHEMA)
        signature = _signature()
        if conn.execute("PRAGMA user_version").fetchone()[0] == signature:
            return
        with conn:                                      # one transaction
            _sync(conn)
        conn.execute(f"PRAGMA user_version = {signature}")


def load_directory() -> dict:
    """Return {'departments': [...], 'faculty': [...]} with subjects and programmes attached."""
    init_db()
    with closing(_connect()) as conn:
        courses_by_dept: dict[int, list[str]] = {}
        for r in conn.execute("SELECT department_id, course_id FROM department_courses"):
            courses_by_dept.setdefault(r["department_id"], []).append(r["course_id"])
        departments = []
        for r in conn.execute("SELECT id, name FROM departments ORDER BY position"):
            names = _course_names()
            ids = [c for c in names if c in courses_by_dept.get(r["id"], [])]           # catalogue order
            departments.append({"id": r["id"], "name": r["name"], "course_ids": ids,
                                "courses": [names[c] for c in ids]})
        dept_by_id = {d["id"]: d for d in departments}

        subjects: dict[int, list[str]] = {}
        for r in conn.execute(
            "SELECT fs.faculty_id, s.name FROM faculty_subjects fs "
            "JOIN subjects s ON s.id = fs.subject_id ORDER BY s.name"
        ):
            subjects.setdefault(r["faculty_id"], []).append(r["name"])

        faculty = []
        for r in conn.execute("SELECT * FROM faculty"):
            f = dict(r)
            dept = dept_by_id[f["department_id"]]
            f["department"] = dept["name"]
            f["course_ids"] = dept["course_ids"]
            f["courses"] = dept["courses"]
            f["subjects"] = subjects.get(f["id"], [])
            faculty.append(f)
        order = {d["name"]: i for i, d in enumerate(departments)}
        faculty.sort(key=lambda f: (order[f["department"]], not f["post"],
                                    _RANK.get(f["designation"], 9), f["name"]))
        return {"departments": departments, "faculty": faculty}


def faculty_for_course(course_id: str) -> list[dict]:
    """Faculty of the department that teaches a course."""
    return [f for f in load_directory()["faculty"] if course_id in f["course_ids"]]


def link_course(course_id: str, department_name: str) -> None:
    """Link a course to a department, e.g. link_course('bsc-geology', 'Life Sciences')."""
    init_db()
    with closing(_connect()) as conn, conn:
        row = conn.execute("SELECT id FROM departments WHERE name = ?", (department_name,)).fetchone()
        if not row:
            raise ValueError(f"No department named '{department_name}'")
        conn.execute("INSERT OR IGNORE INTO department_courses VALUES (?, ?)", (row[0], course_id))


def unlinked_courses() -> list[str]:
    """Ids of courses that are not linked to any department yet."""
    init_db()
    with closing(_connect()) as conn:
        linked = {r[0] for r in conn.execute("SELECT course_id FROM department_courses")}
    return [c for c in _course_names() if c not in linked]
