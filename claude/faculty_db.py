"""faculty_db.py - faculty tables, seeding and queries (SQLite, Python standard library).

Tables: departments, department_courses (links to course ids in data.py),
subjects, faculty, faculty_subjects. The database file is created automatically.
On every start the seed data is SYNCED ADDITIVELY: missing departments, course links and
faculty are inserted; records that already exist are never modified or deleted.
Courses come from the live course list (data.COURSES, kept in step with college.db by catalogue_db). A course
without a department is allowed: it is reported by unlinked_courses() and linked with link_course().
"""
import re
import sqlite3
import zlib
from contextlib import closing
from datetime import date

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
    is_sample INTEGER NOT NULL DEFAULT 1, source TEXT, last_updated TEXT,
    published INTEGER NOT NULL DEFAULT 1, description TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS faculty_tombstones (slug TEXT PRIMARY KEY);
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
        if conn.execute("SELECT 1 FROM faculty_tombstones WHERE slug = ?", (rec["slug"],)).fetchone():
            continue                                    # removed by an administrator: stays removed
        dept_id = dept_ids[rec["department"]]
        row = {c: rec[c] for c in _FACULTY_COLUMNS} | {"department_id": dept_id}
        faculty_id = conn.execute(f"INSERT INTO faculty ({columns}) VALUES ({marks})", row).lastrowid
        for subject in rec["subjects"]:
            conn.execute("INSERT OR IGNORE INTO subjects (name, department_id) VALUES (?, ?)",
                         (subject, dept_id))
            subject_id = conn.execute("SELECT id FROM subjects WHERE name = ? AND department_id = ?",
                                      (subject, dept_id)).fetchone()[0]
            conn.execute("INSERT OR IGNORE INTO faculty_subjects VALUES (?, ?)", (faculty_id, subject_id))


def _migrate(conn: sqlite3.Connection) -> None:
    have = {r["name"] for r in conn.execute("PRAGMA table_info(faculty)")}
    for column, ddl in (("published", "INTEGER NOT NULL DEFAULT 1"), ("description", "TEXT DEFAULT ''")):
        if column not in have:
            conn.execute(f"ALTER TABLE faculty ADD COLUMN {column} {ddl}")


def init_db() -> None:
    """Create tables and sync the seed data (only when the seed data or catalogue changed)."""
    with closing(_connect()) as conn:
        conn.executescript(_SCHEMA)
        _migrate(conn)
        conn.commit()
        signature = _signature()
        if conn.execute("PRAGMA user_version").fetchone()[0] == signature:
            return
        with conn:                                      # one transaction
            _sync(conn)
        conn.execute(f"PRAGMA user_version = {signature}")


def load_directory(published_only: bool = True) -> dict:
    """Return {'departments': [...], 'faculty': [...]} with subjects and programmes attached.
    By default only PUBLISHED faculty are included (the public site and the assistant); administration passes False."""
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
        for r in conn.execute("SELECT * FROM faculty" + (" WHERE published = 1" if published_only else "")):
            f = dict(r)
            f["published"] = bool(f.get("published", 1))
            f["description"] = f.get("description") or ""
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


# --------------------------------------------------- administration helpers
_FACULTY_FIELDS = ("name", "designation", "post", "qualifications", "specialization", "teaching_years", "industry_years",
                   "research_interests", "description", "email", "phone", "office", "consultation_hours")


def department_names() -> list[str]:
    init_db()
    with closing(_connect()) as conn:
        return [r[0] for r in conn.execute("SELECT name FROM departments ORDER BY position")]


def _slug_for(conn: sqlite3.Connection, name: str) -> str:
    words = [w for w in re.sub(r"[^a-z0-9 ]+", " ", name.lower()).split() if w not in ("dr", "mr", "ms", "prof")]
    base = "-".join(words)[:50] or "faculty"
    taken = {r[0] for r in conn.execute("SELECT slug FROM faculty")} | {r[0] for r in conn.execute("SELECT slug FROM faculty_tombstones")}
    candidate, n = base, 2
    while candidate in taken:
        candidate, n = f"{base}-{n}", n + 1
    return candidate


def save_faculty(rec: dict, department: str, subjects: list[str], published: bool, faculty_id: int | None = None) -> int:
    """Insert or update one faculty profile (administration; callers must have authorised the user)."""
    init_db()
    with closing(_connect()) as conn, conn:
        dept = conn.execute("SELECT id FROM departments WHERE name = ?", (department,)).fetchone()
        if not dept:
            raise ValueError(f"No department named '{department}'")
        values = {k: rec.get(k) for k in _FACULTY_FIELDS}
        values.update(department_id=dept[0], published=1 if published else 0, is_sample=1 if rec.get("is_sample") else 0,
                      last_updated=date.today().isoformat())
        if faculty_id is None:
            values.update(slug=_slug_for(conn, rec["name"]), source="Entered by an administrator")
            cols = ", ".join(values)
            faculty_id = conn.execute(f"INSERT INTO faculty ({cols}) VALUES ({', '.join(':' + k for k in values)})", values).lastrowid
        else:
            sets = ", ".join(f"{k} = :{k}" for k in values)
            if conn.execute(f"UPDATE faculty SET {sets} WHERE id = :_id", {**values, "_id": faculty_id}).rowcount == 0:
                raise ValueError("That faculty profile no longer exists.")
        conn.execute("DELETE FROM faculty_subjects WHERE faculty_id = ?", (faculty_id,))
        for subject in subjects:
            conn.execute("INSERT OR IGNORE INTO subjects (name, department_id) VALUES (?, ?)", (subject, dept[0]))
            sid = conn.execute("SELECT id FROM subjects WHERE name = ? AND department_id = ?", (subject, dept[0])).fetchone()[0]
            conn.execute("INSERT OR IGNORE INTO faculty_subjects VALUES (?, ?)", (faculty_id, sid))
        return faculty_id


def set_faculty_published(faculty_id: int, published: bool) -> None:
    init_db()
    with closing(_connect()) as conn, conn:
        if conn.execute("UPDATE faculty SET published = ? WHERE id = ?", (1 if published else 0, faculty_id)).rowcount == 0:
            raise ValueError("That faculty profile no longer exists.")


def delete_faculty(faculty_id: int) -> str:
    """Remove a profile for good. Its slug is remembered so a seed update cannot bring it back. Returns the slug."""
    init_db()
    with closing(_connect()) as conn, conn:
        row = conn.execute("SELECT slug FROM faculty WHERE id = ?", (faculty_id,)).fetchone()
        if not row:
            raise ValueError("That faculty profile no longer exists.")
        conn.execute("DELETE FROM faculty_subjects WHERE faculty_id = ?", (faculty_id,))
        conn.execute("DELETE FROM faculty WHERE id = ?", (faculty_id,))
        conn.execute("INSERT OR IGNORE INTO faculty_tombstones VALUES (?)", (row[0],))
        return row[0]


def set_course_department(course_id: str, department: str | None) -> None:
    """Link a course to exactly one department (or to none)."""
    init_db()
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM department_courses WHERE course_id = ?", (course_id,))
        if department:
            row = conn.execute("SELECT id FROM departments WHERE name = ?", (department,)).fetchone()
            if not row:
                raise ValueError(f"No department named '{department}'")
            conn.execute("INSERT INTO department_courses VALUES (?, ?)", (row[0], course_id))


def department_of_course(course_id: str) -> str | None:
    init_db()
    with closing(_connect()) as conn:
        row = conn.execute("SELECT d.name FROM departments d JOIN department_courses dc ON dc.department_id = d.id "
                           "WHERE dc.course_id = ?", (course_id,)).fetchone()
    return row[0] if row else None


def linked_course_ids() -> set[str]:
    """Ids of every course that has a department (published or not)."""
    init_db()
    with closing(_connect()) as conn:
        return {r[0] for r in conn.execute("SELECT DISTINCT course_id FROM department_courses")}


def course_departments() -> dict[str, str]:
    """course id -> department name for every link."""
    init_db()
    with closing(_connect()) as conn:
        return {r[0]: r[1] for r in conn.execute("SELECT dc.course_id, d.name FROM department_courses dc "
                                                 "JOIN departments d ON d.id = dc.department_id")}
