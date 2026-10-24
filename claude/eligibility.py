"""eligibility.py - compares a student's answers with the STORED requirements of one course (no Streamlit, no database).

It is the single place where eligibility is decided. The registration review, the public Eligibility Checker page
and (through eligibility_service.py) everything else call check_eligibility(), so they can never disagree.

Principles
  * Only stored requirements are used. Nothing is invented.
  * Anything that cannot be verified from the stored data or the answers is 'unverified'. It is NEVER counted as a pass.
  * One clearly unmet requirement gives 'does not meet', even when other items still need confirmation.
  * The result is indicative. It is not an admission decision.
"""
from __future__ import annotations

import re

CHECK_MET, CHECK_UNMET, CHECK_UNVERIFIED = "met", "unmet", "unverified"
OUTCOME_MEETS, OUTCOME_NOT_MET, OUTCOME_INSUFFICIENT = "meets", "does_not_meet", "insufficient"

OUTCOME_LABELS = {
    OUTCOME_MEETS: "Meets the stored criteria",
    OUTCOME_NOT_MET: "Does not meet the stored criteria",
    OUTCOME_INSUFFICIENT: "Cannot be confirmed yet",
}
DISCLAIMER = (
    "Eligibility results are indicative only and are based on the illustrative criteria stored in this prototype. "
    "Meeting the listed criteria does not guarantee admission. The college confirms the final requirements."
)

_KNOWN = ("physics", "chemistry", "mathematics", "biology", "computer science", "statistics", "electronics",
          "economics", "accountancy", "business studies", "english")
_ALIASES = {"maths": "mathematics", "math": "mathematics"}


# ------------------------------------------------------------ subject rules
def _norm_subject(text: str) -> str:
    s = re.sub(r"\s+", " ", str(text or "").strip().lower())
    return _ALIASES.get(s, s)


def parse_subject_requirement(text: str | None) -> tuple[str, list[str]]:
    """Read a plain-text Class 12 requirement. Returns ('all', [subjects]), ('any', []) or ('unknown', []).

    Only simple wording such as 'Physics and Mathematics' is understood. Wording with 'or', 'one of',
    'preferred', 'to be confirmed' and so on is 'unknown', because it cannot be checked safely by machine.
    """
    if not text or not str(text).strip():
        return "unknown", []
    low = _norm_subject(text)
    if re.search(r"\bany (?:stream|subject)", low):
        return "any", []
    if re.search(r"\b(or|one of|preferred|confirm\w*|specified|other|plus|accepted|any)\b|/|;", low):
        return "unknown", []
    parts = [_norm_subject(p) for p in re.split(r",|\band\b", low) if p.strip()]
    if parts and all(p in _KNOWN for p in parts):
        return "all", [p.title() for p in parts]
    return "unknown", []


def subject_rule(course: dict) -> dict:
    """The course's Class 12 subject rule in one shape:
    {'all': [...], 'one_of': [[...]], 'any_stream': bool, 'unverified': str|None, 'other_unverified': bool}."""
    rule = {"all": [], "one_of": [], "any_stream": False, "unverified": None, "other_unverified": False}
    structured = course.get("req12")
    if isinstance(structured, dict) and structured:
        rule["all"] = [_norm_subject(s) for s in structured.get("all", [])]
        rule["one_of"] = [[_norm_subject(s) for s in g] for g in structured.get("one_of", [])]
        rule["any_stream"] = bool(structured.get("any_stream"))
        rule["unverified"] = structured.get("unverified")
        rule["other_unverified"] = bool(structured.get("other_unverified"))
        return rule
    if course.get("required_subjects"):
        rule["all"] = [_norm_subject(s) for s in course["required_subjects"]]
        return rule
    kind, subjects = parse_subject_requirement(course.get("class12"))
    if kind == "all":
        rule["all"] = [_norm_subject(s) for s in subjects]
    elif kind == "any":
        rule["any_stream"] = True
    elif course.get("class12"):
        rule["unverified"] = "The stored Class 12 subject wording needs the college's confirmation."
    return rule


def _student_subjects(academic: dict) -> set[str]:
    chosen = {_norm_subject(s) for s in (academic.get("class12_subjects") or [])}
    for extra in re.split(r"[,;/]", str(academic.get("class12_other_subjects") or "")):
        if extra.strip():
            chosen.add(_norm_subject(extra))
    if _norm_subject(academic.get("class12_stream")) == "vocational":
        chosen.add("technical vocational subject")
    return chosen


def _title(items) -> str:
    return ", ".join(str(i).title() for i in items)


# --------------------------------------------------------------- the checks
def _check(criterion: str, status: str, detail: str) -> dict:
    return {"criterion": criterion, "status": status, "detail": detail}


def _percentage_check(label: str, value, minimum, waiting: bool = False) -> dict:
    name = f"Minimum marks ({label})"
    if minimum is None:
        return _check(name, CHECK_UNVERIFIED, "No minimum percentage is stored for this course.")
    if waiting:
        return _check(name, CHECK_UNVERIFIED, f"Your result is awaited, so your marks cannot be compared with the {minimum:g}% minimum yet.")
    if value is None:
        return _check(name, CHECK_UNVERIFIED, "Your percentage was not provided.")
    if value >= minimum:
        return _check(name, CHECK_MET, f"Your {value:g}% is at or above the {minimum:g}% minimum.")
    return _check(name, CHECK_UNMET, f"Your {value:g}% is below the {minimum:g}% minimum.")


def _subject_check(course: dict, academic: dict) -> dict:
    rule = subject_rule(course)
    name = "Class 12 subjects"
    if rule["any_stream"] and not rule["all"] and not rule["one_of"]:
        return _check(name, CHECK_MET, "Any Class 12 stream is accepted.")
    if rule["unverified"] and not rule["all"] and not rule["one_of"]:
        return _check(name, CHECK_UNVERIFIED, str(rule["unverified"]))
    if not rule["all"] and not rule["one_of"]:
        return _check(name, CHECK_UNVERIFIED, "The Class 12 subject requirement for this course is not stored.")
    have = _student_subjects(academic)
    if not have:
        return _check(name, CHECK_UNVERIFIED, "Your Class 12 subjects were not provided.")
    missing = [s for s in rule["all"] if s not in have]
    bad_groups = [g for g in rule["one_of"] if not any(s in have for s in g)]
    if not missing and not bad_groups:
        used = list(rule["all"]) + [next(s for s in g if s in have) for g in rule["one_of"]]
        detail = "Required subjects present: " + _title(used) + "."
        if rule["other_unverified"]:
            return _check(name, CHECK_UNVERIFIED, detail + " Other subjects may also be accepted, but that list is not stored.")
        return _check(name, CHECK_MET, detail)
    parts = []
    if missing:
        parts.append("Missing required subject(s): " + _title(missing) + ".")
    for g in bad_groups:
        parts.append("At least one of these is needed: " + " / ".join(s.title() for s in g) + ".")
    if rule["other_unverified"]:
        return _check(name, CHECK_UNVERIFIED, " ".join(parts) + " Other subjects may also be accepted, but that list is not stored.")
    return _check(name, CHECK_UNMET, " ".join(parts))


def check_eligibility(course: dict, academic: dict) -> dict:
    """Compare validated answers with one course's stored requirements.

    `academic` uses the registration field names (qualification_route, class12_percentage, class12_subjects, ...).
    Returns {'outcome', 'label', 'checks': [{criterion, status, detail}], 'notes': [...], 'disclaimer'}.
    """
    route = academic.get("qualification_route")
    minimum = course.get("min_pct")
    minimum = float(minimum) if isinstance(minimum, (int, float)) else None
    checks: list[dict] = []
    notes: list[str] = []

    if route == "class12":
        checks.append(_subject_check(course, academic))
        waiting = academic.get("class12_result_status") == "Awaited"
        checks.append(_percentage_check("Class 12", academic.get("class12_percentage"), minimum, waiting))
        if course.get("level") == "Postgraduate" or course.get("degree"):
            checks.append(_check("Qualification level", CHECK_UNMET,
                                 "This is a postgraduate course and needs a bachelor's degree."))
    elif route == "diploma":
        if course.get("diploma"):
            checks.append(_check("Diploma pathway", CHECK_UNVERIFIED,
                                 "Stored wording: " + str(course["diploma"]) + " Lateral entry is not automatic."))
        else:
            checks.append(_check("Diploma pathway", CHECK_UNMET, "No diploma pathway is listed for this course."))
        checks.append(_percentage_check("diploma", academic.get("diploma_percentage"), minimum))
    elif route == "degree":
        name = str(academic.get("degree_name") or "").strip()
        checks.append(_check("Bachelor's degree", CHECK_MET if name else CHECK_UNVERIFIED,
                             f"You entered: {name}." if name else "Your degree name was not provided."))
        if course.get("degree"):
            checks.append(_check("Accepted degrees", CHECK_UNVERIFIED,
                                 "Stored wording: " + str(course["degree"]) + " The college must confirm that your degree is accepted."))
        else:
            checks.append(_check("Accepted degrees", CHECK_UNVERIFIED, "Which degrees are accepted is not stored."))
        checks.append(_percentage_check("bachelor's degree", academic.get("degree_percentage"), minimum))
    else:
        checks.append(_check("Qualification", CHECK_UNVERIFIED, "How you are applying was not provided."))

    mode = str(course.get("admission_mode") or "")
    if "entrance" in mode.lower():
        notes.append("Admission mode: " + mode)
    notes.append("Final eligibility, any entrance test and the admission decision are made only by the college.")

    if any(c["status"] == CHECK_UNMET for c in checks):
        outcome = OUTCOME_NOT_MET
    elif any(c["status"] == CHECK_UNVERIFIED for c in checks):
        outcome = OUTCOME_INSUFFICIENT
    else:
        outcome = OUTCOME_MEETS
    return {"outcome": outcome, "label": OUTCOME_LABELS[outcome], "checks": checks, "notes": notes,
            "disclaimer": DISCLAIMER}
