"""eligibility_service.py - the public Eligibility Checker page's logic (no Streamlit, no database).

It adds NO new eligibility rules. It validates what a visitor typed, hands it to the existing
eligibility.check_eligibility() (the same function the registration review uses) and shapes the result
for display. So this page and the registration review can never disagree.

Privacy: nothing is saved, logged or sent anywhere. No name, contact or identity details are collected.
"""
from __future__ import annotations

import math
import re

import course_service
import registration_schema as schema
from eligibility import (
    CHECK_MET, CHECK_UNMET, CHECK_UNVERIFIED, OUTCOME_INSUFFICIENT, OUTCOME_MEETS, OUTCOME_NOT_MET,
    check_eligibility, parse_subject_requirement,
)

NOTICE = (
    "Eligibility results are indicative only and are based on the illustrative criteria available in this "
    "prototype. Meeting the listed criteria does not guarantee admission. Please confirm the official "
    "requirements with the college."
)
MAX_TEXT = 200


# ------------------------------------------------------------------ the course
def subject_requirement(course: dict) -> tuple[str, list[str]]:
    """('all', [subjects]) / ('any', []) / ('unknown', []) exactly as the existing check reads the course."""
    structured = course.get("required_subjects")
    if structured:
        return "all", [str(s) for s in structured]
    return parse_subject_requirement(course.get("class12"))


def routes_for(course: dict) -> list[str]:
    return schema.qualification_routes(course)


def inputs_needed(course: dict, route: str | None) -> dict:
    """Which answers can change the result for this course and route (so the form only asks for those)."""
    has_minimum = course.get("min_pct") is not None
    kind, _ = subject_requirement(course)
    return {
        "percentage": route in (schema.ROUTE_CLASS12, schema.ROUTE_DEGREE) and has_minimum,
        "result_status": route == schema.ROUTE_CLASS12 and has_minimum,
        "subjects": route == schema.ROUTE_CLASS12 and kind == "all",
        "other_subjects": route == schema.ROUTE_CLASS12 and kind == "all",
    }


def describe_requirements(course: dict) -> list[str]:
    """The stored requirements in plain language. Stored wording is quoted as written, never reinterpreted."""
    lines = ["You can apply with: " + " or ".join(schema.ROUTE_LABELS[r] for r in routes_for(course)) + "."]
    minimum = course.get("min_pct")
    lines.append(f"Minimum marks: {minimum:g}% (illustrative)." if isinstance(minimum, (int, float))
                 else "Minimum marks: not stored for this course.")
    if schema.ROUTE_CLASS12 in routes_for(course):
        kind, subjects = subject_requirement(course)
        text = course.get("class12")
        if kind == "all":
            lines.append("Class 12 subjects required: " + ", ".join(subjects) + ".")
        elif kind == "any":
            lines.append("Class 12 subjects: accepted from any stream.")
        elif text:
            lines.append(f"Class 12 subjects (stored wording): {text}. This wording needs the college's confirmation, "
                         "so it cannot be checked automatically.")
        else:
            lines.append("Class 12 subjects: not stored for this course.")
    if course.get("degree"):
        lines.append(f"Bachelor's degree (stored wording): {course['degree']}. The college must confirm that your degree is accepted.")
    if course.get("diploma"):
        lines.append(f"Diploma pathway (stored wording): {course['diploma']}")
    if course.get("admission_mode"):
        lines.append(f"Admission mode: {course['admission_mode']}")
    return lines


# --------------------------------------------------------------- the answers
def parse_percentage(value) -> tuple[float | None, str | None]:
    """(number, None) / (None, None) for blank / (None, message) when invalid."""
    if value is None:
        return None, None
    if isinstance(value, bool):
        return None, "Enter your percentage as a number such as 78.5."
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value).strip().rstrip("%").strip()
        if not text:
            return None, None
        if not re.fullmatch(r"\d+(\.\d+)?|\.\d+", text):
            return None, "Enter your percentage as a number such as 78.5."
        number = float(text)
    if not math.isfinite(number) or not 0 <= number <= 100:
        return None, "Your percentage must be between 0 and 100."
    return number, None


def clean_answers(course: dict, answers: dict | None) -> tuple[dict, dict]:
    """Return (academic answers in the form eligibility.check_eligibility() expects, errors)."""
    a = answers or {}
    errors: dict[str, str] = {}
    route = a.get("route")
    if route not in routes_for(course):
        errors["route"] = "Choose how you are applying to this course."
        return {}, errors
    needs = inputs_needed(course, route)
    academic: dict = {"qualification_route": route}

    if needs["percentage"]:
        number, message = parse_percentage(a.get("percentage"))
        if message:
            errors["percentage"] = message
        field = "class12_percentage" if route == schema.ROUTE_CLASS12 else "degree_percentage"
        academic[field] = number
    if needs["result_status"]:
        status = a.get("result_status")
        if status in (None, ""):
            academic["class12_result_status"] = None
        elif status in (schema.RESULT_DECLARED, schema.RESULT_AWAITED):
            academic["class12_result_status"] = status
        else:
            errors["result_status"] = "Choose Declared or Awaited."
    if needs["subjects"]:
        subjects = a.get("subjects") or []
        if not isinstance(subjects, (list, tuple, set)) or any(s not in schema.CLASS12_SUBJECTS for s in subjects):
            errors["subjects"] = "Choose subjects from the list."
        else:
            academic["class12_subjects"] = list(subjects)
        other = re.sub(r"\s+", " ", str(a.get("other_subjects") or "")).strip()
        if len(other) > MAX_TEXT:
            errors["other_subjects"] = f"Keep this under {MAX_TEXT} characters."
        else:
            academic["class12_other_subjects"] = other
    return academic, errors


# ------------------------------------------------------------------ the check
def check_course(course_id: str | None, answers: dict | None) -> dict:
    """Validate the answers and compare them with the stored requirements of one course."""
    course = course_service.get_course(course_id)
    if course is None:
        return {"valid": False, "errors": {"course": "Choose a course."}, "outcome": None}
    academic, errors = clean_answers(course, answers)
    if errors:
        return {"valid": False, "errors": errors, "outcome": None,
                "course_id": course["id"], "course_name": course["name"]}

    raw = check_eligibility(course, academic)
    pick = lambda status: [{"criterion": c["criterion"], "detail": c["detail"]}  # noqa: E731
                           for c in raw["checks"] if c["status"] == status]
    met, unmet, unverified = pick(CHECK_MET), pick(CHECK_UNMET), pick(CHECK_UNVERIFIED)
    return {
        "valid": True, "errors": {}, "course_id": course["id"], "course_name": course["name"],
        "outcome": raw["outcome"], "label": raw["label"],
        "met": met, "unmet": unmet, "unverified": unverified, "notes": list(raw["notes"]),
        "explanation": _explain(raw["outcome"], len(met), len(unmet), len(unverified)),
        "next_steps": _next_steps(raw["outcome"]),
        "notice": NOTICE,
    }


def _explain(outcome: str, met: int, unmet: int, unverified: int) -> str:
    base = ("Your answers were compared with the requirements stored on this website for this course: "
            f"{met} met, {unmet} not met, {unverified} need the college's confirmation or more information. ")
    if outcome == OUTCOME_NOT_MET:
        return base + "At least one stored requirement is clearly not met, so the result is 'does not meet', even if other items still need confirmation."
    if outcome == OUTCOME_INSUFFICIENT:
        return base + ("Nothing is clearly unmet, but some requirements cannot be verified from the stored data or your answers. "
                       "Anything that cannot be verified is never counted as a pass.")
    return base + "Every stored requirement that can be checked is met. This is not an admission decision."


def _next_steps(outcome: str) -> list[str]:
    if outcome == OUTCOME_MEETS:
        steps = ["Confirm the official requirements with the college. These criteria are illustrative.",
                 "Ask the college about application dates, documents and how admission decisions are made."]
    elif outcome == OUTCOME_NOT_MET:
        steps = ["Read the requirements that were not met and check that your answers are correct.",
                 "Ask the college whether other qualifications or pathways are considered for this course.",
                 "You can check another course. This does not mean any course is available to you."]
    else:
        steps = ["Fill in any missing answers and check again.",
                 "Ask the college to confirm the requirements marked as needing confirmation.",
                 "You can check another course."]
    return steps + ["Registration approval and admission decisions are made only by the college."]
