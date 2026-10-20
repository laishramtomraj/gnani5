"""eligibility.py - compare a student's answers with the requirements STORED in the course record.

This is NOT an admission decision and never approves anyone. It reports one of three outcomes:

  meets          every stored criterion that can be checked is satisfied
  does_not_meet  at least one stored criterion is clearly not satisfied
  insufficient   nothing is clearly unmet, but something cannot be verified from the stored data

What is checked:
  * Minimum marks (course['min_pct'], a number) against the percentage for the chosen route.
  * Class 12 subjects, but ONLY when the stored text is a plain list such as
    "Physics, Chemistry and Mathematics" (every listed subject is then required) or "in any stream".
    Anything with wording like "or", "one of", "with", "plus", "preferred", "to be confirmed" or
    brackets is free text that a program cannot judge reliably, so it is reported as "needs the
    college's confirmation" instead of being guessed.
  * Diploma and bachelor's-degree requirements are stored as free text, so they are never auto-confirmed.

To make a course fully checkable later, add a list field to its record in course_catalogue.py:
    "required_subjects": ["Physics", "Mathematics"]      # every subject listed is required
That list takes priority over the text. No other file needs to change.
"""
from __future__ import annotations

import re

import registration_schema as schema

OUTCOME_MEETS = "meets"
OUTCOME_NOT_MET = "does_not_meet"
OUTCOME_INSUFFICIENT = "insufficient"

OUTCOME_LABELS = {
    OUTCOME_MEETS: "Meets the stored criteria based on the information provided",
    OUTCOME_NOT_MET: "Does not meet the stored criteria",
    OUTCOME_INSUFFICIENT: "Insufficient information to determine eligibility",
}
DISCLAIMER = (
    "This check compares your answers with the requirements stored on this website. It is not an official "
    "eligibility decision and does not guarantee admission. The college makes the final decision."
)

CHECK_MET, CHECK_UNMET, CHECK_UNVERIFIED = "met", "unmet", "unverified"

_AMBIGUOUS_WORDS = re.compile(
    r"\b(or|one of|plus|with|preferred|prefer|confirm\w*|specified|accepted|relevant|other|any)\b", re.I
)
_ANY_STREAM = re.compile(r"\s*(class 12\s+)?in any stream\s*\.?\s*", re.I)


# ------------------------------------------------------- subject-text parser
def parse_subject_requirement(text: str | None) -> tuple[str, list[str]]:
    """Return ('any', []), ('all', [subjects]) or ('unknown', []) for a stored subject requirement."""
    if not text or not text.strip():
        return "unknown", []
    if _ANY_STREAM.fullmatch(text):
        return "any", []
    if "(" in text or ")" in text or ";" in text or _AMBIGUOUS_WORDS.search(text):
        return "unknown", []
    parts = [p.strip() for p in re.split(r",|\band\b", text) if p.strip()]
    if not parts or any(not re.fullmatch(r"[A-Za-z ]+", p) for p in parts):
        return "unknown", []
    return "all", parts


def _student_subjects(academic: dict) -> set[str]:
    chosen = [str(s) for s in (academic.get("class12_subjects") or [])]
    extra = [s for s in re.split(r"[,;]", str(academic.get("class12_other_subjects") or "")) if s.strip()]
    return {s.strip().lower() for s in chosen + extra}


def _check(criterion: str, status: str, detail: str) -> dict:
    return {"criterion": criterion, "status": status, "detail": detail}


# ----------------------------------------------------------- the main check
def check_eligibility(course: dict, academic: dict) -> dict:
    """Compare the student's academic answers with the stored requirements of one course."""
    checks: list[dict] = []
    notes: list[str] = []
    route = academic.get("qualification_route")
    allowed = schema.qualification_routes(course)

    # 1. Qualification route
    if route not in allowed:
        listed = " or ".join(schema.ROUTE_LABELS[r] for r in allowed)
        checks.append(_check("Qualification route", CHECK_UNMET,
                             f"This course lists these ways to apply: {listed}."))
    else:
        checks.append(_check("Qualification route", CHECK_MET, schema.ROUTE_LABELS[route]))

    # 2. Minimum marks
    minimum = course.get("min_pct")
    pct_field = {schema.ROUTE_CLASS12: "class12_percentage", schema.ROUTE_DEGREE: "degree_percentage"}.get(route)
    if route == schema.ROUTE_DIPLOMA:
        checks.append(_check(
            "Diploma pathway", CHECK_UNVERIFIED,
            f"Stored rule: {course.get('diploma')} The stored minimum marks are not stated for this pathway, "
            "so the college must confirm."))
    elif route in allowed and pct_field:
        label = "Class 12" if route == schema.ROUTE_CLASS12 else "Bachelor's degree"
        value = academic.get(pct_field)
        if minimum is None:
            checks.append(_check(f"Minimum marks ({label})", CHECK_UNVERIFIED, "No minimum marks are stored for this course."))
        elif route == schema.ROUTE_CLASS12 and academic.get("class12_result_status") == schema.RESULT_AWAITED:
            checks.append(_check(f"Minimum marks ({label})", CHECK_UNVERIFIED,
                                 f"Your result is awaited, so marks cannot be compared with the stored minimum of {minimum}%."))
        elif not isinstance(value, (int, float)):
            checks.append(_check(f"Minimum marks ({label})", CHECK_UNVERIFIED, "No percentage was provided."))
        elif value >= minimum:
            checks.append(_check(f"Minimum marks ({label})", CHECK_MET,
                                 f"Your {value:g}% is at or above the stored minimum of {minimum}%."))
        else:
            checks.append(_check(f"Minimum marks ({label})", CHECK_UNMET,
                                 f"Your {value:g}% is below the stored minimum of {minimum}%."))

    # 3. Subjects (Class 12 route) or degree requirement (degree route)
    if route == schema.ROUTE_CLASS12 and route in allowed:
        structured = course.get("required_subjects")
        stored_text = course.get("class12")
        if structured:
            kind, required = "all", [str(s) for s in structured]
        else:
            kind, required = parse_subject_requirement(stored_text)
        if not stored_text and not structured:
            notes.append("No Class 12 subject requirement is stored for this course.")
        elif kind == "any":
            checks.append(_check("Class 12 subjects", CHECK_MET, "The stored requirement accepts any stream."))
        elif kind == "all":
            have = _student_subjects(academic)
            missing = [s for s in required if s.lower() not in have]
            if missing:
                checks.append(_check("Class 12 subjects", CHECK_UNMET,
                                     f"Stored requirement: {', '.join(required)}. Not listed in your answers: {', '.join(missing)}."))
            else:
                checks.append(_check("Class 12 subjects", CHECK_MET, f"Stored requirement ({', '.join(required)}) is covered by your subjects."))
        else:
            checks.append(_check("Class 12 subjects", CHECK_UNVERIFIED,
                                 f"Stored requirement: {stored_text} This wording needs the college's confirmation."))
    elif route == schema.ROUTE_DEGREE and route in allowed and course.get("degree"):
        checks.append(_check("Bachelor's degree", CHECK_UNVERIFIED,
                             f"Stored requirement: {course['degree']} The college must confirm that your degree is accepted."))

    if "entrance" in (course.get("admission_mode") or "").lower():
        notes.append(f"Admission mode: {course['admission_mode']}")

    statuses = {c["status"] for c in checks}
    if CHECK_UNMET in statuses:
        outcome = OUTCOME_NOT_MET
    elif CHECK_UNVERIFIED in statuses or not checks:
        outcome = OUTCOME_INSUFFICIENT
    else:
        outcome = OUTCOME_MEETS

    return {
        "outcome": outcome,
        "label": OUTCOME_LABELS[outcome],
        "checks": checks,
        "unmet": [c for c in checks if c["status"] == CHECK_UNMET],
        "unverified": [c for c in checks if c["status"] == CHECK_UNVERIFIED],
        "notes": notes,
        "disclaimer": DISCLAIMER,
    }
