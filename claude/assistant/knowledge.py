"""assistant/knowledge.py - Unified college knowledge access module.

Reads shared course, faculty, fee, and institutional data from the single source of truth.
The assistant relies strictly on this module; no college data is duplicated or invented.
"""
from __future__ import annotations

import difflib
import re
from typing import Any

# Import from existing project single-source-of-truth modules
import course_catalogue
import data
import faculty_db


def get_college_info() -> dict[str, Any]:
    """Return institutional metadata and contact details."""
    return dict(data.COLLEGE)


def get_all_courses() -> list[dict[str, Any]]:
    """Return all courses available in the course catalogue."""
    return list(course_catalogue.COURSES)


def find_course(name_or_query: str) -> dict[str, Any] | None:
    """Find a specific course by ID, code, or title with case-insensitive and fuzzy matching."""
    q = (name_or_query or "").strip().lower()
    if not q:
        return None

    # 1. Exact ID or name match
    for c in course_catalogue.COURSES:
        if c["id"].lower() == q or c["name"].lower() == q:
            return c

    # 2. Check course ID and abbreviations in query
    q_normalized = q.replace(".", "").replace("&", "and").replace("-", " ")
    for c in course_catalogue.COURSES:
        cid = c["id"].lower()
        cid_clean = cid.replace("-", " ")
        if re.search(r"\b" + re.escape(cid) + r"\b", q) or re.search(r"\b" + re.escape(cid_clean) + r"\b", q_normalized):
            return c

        # Check course ID parts (e.g., 'btech-cse' matches 'cse' or 'btech cse')
        parts = cid.split("-")
        if len(parts) > 1:
            sub = parts[1]
            if len(sub) >= 2 and re.search(r"\b" + re.escape(sub) + r"\b", q_normalized):
                return c

        # Check acronym in parentheses from course name (e.g. BCA, CSE, MCA)
        m = re.search(r"\(([A-Za-z0-9.& ]+)\)", c["name"])
        if m:
            acronym = m.group(1).strip().lower()
            if re.search(r"\b" + re.escape(acronym) + r"\b", q_normalized):
                return c

    # 3. Match normalized course name substring
    for c in course_catalogue.COURSES:
        c_name_norm = c["name"].lower().replace(".", "").replace("&", "and").replace("-", " ")
        if c_name_norm in q_normalized or q_normalized in c_name_norm:
            return c

    # 4. Fuzzy similarity match across course names
    names = [c["name"] for c in course_catalogue.COURSES]
    matches = difflib.get_close_matches(name_or_query, names, n=1, cutoff=0.55)
    if matches:
        matched_name = matches[0]
        for c in course_catalogue.COURSES:
            if c["name"] == matched_name:
                return c

    return None


def search_courses(keyword: str) -> list[dict[str, Any]]:
    """Search courses by subject, category, or keyword."""
    k = (keyword or "").strip().lower()
    if not k:
        return []

    results = []
    for c in course_catalogue.COURSES:
        haystack = " ".join([
            c.get("id", ""),
            c.get("name", ""),
            c.get("category", ""),
            c.get("group", ""),
            c.get("overview", ""),
            " ".join(c.get("subjects", [])),
            " ".join(c.get("careers", []))
        ]).lower()
        if k in haystack:
            results.append(c)
    return results


def get_courses_by_budget(max_annual_fee: int) -> list[dict[str, Any]]:
    """Return courses where annual tuition is less than or equal to max_annual_fee."""
    return [c for c in course_catalogue.COURSES if c.get("tuition", 0) <= max_annual_fee]


def get_course_fee_details(course_id_or_name: str) -> dict[str, Any] | None:
    """Return fee details for a course, formatted in INR."""
    c = find_course(course_id_or_name)
    if not c:
        return None
    tuition = c.get("tuition", 0)
    years = c.get("years", 1)
    return {
        "course_id": c["id"],
        "course_name": c["name"],
        "annual_tuition": tuition,
        "annual_tuition_formatted": data.format_inr(tuition),
        "duration_years": years,
        "total_tuition_estimate": tuition * years,
        "total_tuition_formatted": data.format_inr(tuition * years),
        "note": "Tuition only. Excludes hostel, transport, registration, and exam fees."
    }


def get_course_eligibility(course_id_or_name: str) -> dict[str, Any] | None:
    """Return eligibility criteria for a given course."""
    c = find_course(course_id_or_name)
    if not c:
        return None
    return {
        "course_id": c["id"],
        "course_name": c["name"],
        "level": c.get("level", "Undergraduate"),
        "min_percentage": c.get("min_pct"),
        "class12_requirements": c.get("class12"),
        "degree_requirements": c.get("degree"),
        "diploma_lateral_entry": c.get("diploma"),
        "admission_mode": c.get("admission_mode"),
        "documents": c.get("documents", [])
    }


def get_admission_procedure() -> dict[str, Any]:
    """Return the general admission steps and required document checklists."""
    return {
        "general_procedure": list(course_catalogue.PROCEDURE),
        "ug_documents": list(course_catalogue.DOCS_UG),
        "pg_documents": list(course_catalogue.DOCS_PG),
    }


def get_faculty_list(department_or_keyword: str = "") -> list[dict[str, Any]]:
    """Return faculty members, optionally filtered by department or name."""
    faculty_db.init_db()
    directory = faculty_db.load_directory() or {}
    all_faculty = directory.get("faculty", [])
    q = (department_or_keyword or "").strip().lower()
    if not q:
        return all_faculty

    matches = []
    for f in all_faculty:
        text = " ".join([
            f.get("name", ""),
            f.get("department", ""),
            f.get("designation", ""),
            f.get("specialization", ""),
            " ".join(f.get("subjects", []))
        ]).lower()
        if q in text:
            matches.append(f)
    return matches