"""course_service.py - read-only access to the existing course and department data.

This module has no Streamlit code, so the registration pages, the tests and (later) the
College Admission Assistant can all call the same functions.

The source of truth does NOT move:
  * courses     -> course_catalogue.py (exposed as data.COURSES)
  * departments -> college.db through faculty_db.load_directory()
Nothing is copied here. If you edit a course, these functions return the new values.
"""
from __future__ import annotations

from functools import lru_cache

import faculty_db
from data import COURSES, DATA_IS_SAMPLE, DATA_NOTICE

NOT_LISTED = "Not listed"


# ------------------------------------------------------------------ lookups
def list_courses() -> list[dict]:
    """All courses, in catalogue order."""
    return list(COURSES)


def get_course(course_id: str | None) -> dict | None:
    """Find a course by its stable id (for example 'btech-cse'). None if unknown."""
    if not course_id:
        return None
    return next((c for c in COURSES if c["id"] == course_id), None)


def get_course_by_name(name: str | None) -> dict | None:
    """Find a course by its display name. The website's Register buttons pass the name."""
    if not name:
        return None
    return next((c for c in COURSES if c["name"] == name), None)


# --------------------------------------------------------------- departments
@lru_cache(maxsize=2)
def _departments_by_course(db_stamp: float) -> dict[str, str]:
    directory = faculty_db.load_directory()
    return {cid: d["name"] for d in directory["departments"] for cid in d["course_ids"]}


def department_for(course_id: str) -> str | None:
    """Department that teaches a course (cached until college.db changes)."""
    try:
        stamp = faculty_db.DB_PATH.stat().st_mtime
    except OSError:
        stamp = 0.0
    return _departments_by_course(stamp).get(course_id)


# ------------------------------------------------------------------- figures
def total_tuition(course: dict) -> int | None:
    """Annual tuition x duration, the same calculation the Courses page shows."""
    tuition, years = course.get("tuition"), course.get("years")
    if isinstance(tuition, (int, float)) and isinstance(years, (int, float)):
        return int(tuition * years)
    return None


def mentions_entrance_test(course: dict) -> bool:
    """True when the stored admission mode talks about an entrance test."""
    return "entrance" in (course.get("admission_mode") or "").lower()


# ----------------------------------------------------------------- summaries
def course_summary(course_id: str) -> dict | None:
    """Everything the registration form (or the assistant) may show about one course.

    Values that the data does not record are None. Seat availability is only filled when a
    course record has a 'seats_available' field; today none does, so it stays None.
    """
    course = get_course(course_id)
    if course is None:
        return None
    return {
        "id": course["id"],
        "name": course["name"],
        "group": course.get("group"),
        "category": course.get("category"),
        "level": course.get("level"),
        "department": department_for(course["id"]),
        "duration_years": course.get("years"),
        "annual_tuition": course.get("tuition"),
        "total_tuition": total_tuition(course),
        "seat_capacity": course.get("seats"),
        "seat_availability": course.get("seats_available"),
        "class12_requirement": course.get("class12"),
        "degree_requirement": course.get("degree"),
        "minimum_percentage": course.get("min_pct"),
        "diploma_pathway": course.get("diploma"),
        "admission_mode": course.get("admission_mode"),
        "documents": list(course.get("documents") or []),
        "procedure": list(course.get("procedure") or []),
        "mentions_entrance_test": mentions_entrance_test(course),
        "data_is_sample": DATA_IS_SAMPLE,
        "data_notice": DATA_NOTICE,
    }
