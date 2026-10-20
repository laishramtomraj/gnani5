"""registration_validation.py - reusable checks for registration answers (no Streamlit, no database).

validate_registration() returns a dict {field name: message}. An empty dict means the answers are valid.
Messages are written for students: they say what is wrong and how to fix it.
"""
from __future__ import annotations

import math
import re
import unicodedata
from datetime import date, datetime

import registration_schema as schema

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$")
MIN_AGE, MAX_AGE = 15, 70
YEARS_BACK = 15
MAX_TEXT = 200


# ------------------------------------------------------------ normalisation
def clean_text(value) -> str:
    """Trim, collapse whitespace and drop control characters."""
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return "".join(ch for ch in text if ch.isprintable())


def normalize_mobile(raw) -> str | None:
    """Return '+91XXXXXXXXXX' for a valid Indian mobile number, else None."""
    digits = re.sub(r"[\s\-().]", "", clean_text(raw))
    if digits.startswith("+91"):
        digits = digits[3:]
    elif digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    return "+91" + digits if re.fullmatch(r"[6-9]\d{9}", digits) else None


def _number(value):
    """float when the value is numeric, the original value when it is not, None when blank."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except ValueError:
        return value


def _year(value):
    number = _number(value)
    if isinstance(number, float) and number == int(number):
        return int(number)
    return number


def _dob(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return clean_text(value)


def normalize(data: dict) -> dict:
    """Return the answers in their canonical types. Unknown keys are dropped. Stale route fields are blanked."""
    out: dict = {}
    for field in schema.ALL_FIELDS:
        value = data.get(field)
        if field in ("declaration_accurate", "privacy_acknowledged"):
            out[field] = bool(value)
        elif field == "email":
            out[field] = clean_text(value).lower()
        elif field == "mobile":
            out[field] = normalize_mobile(value) or clean_text(value)
        elif field == "date_of_birth":
            out[field] = _dob(value)
        elif field == "class12_subjects":
            out[field] = [clean_text(v) for v in (value or []) if clean_text(v)]
        elif field.endswith("_percentage"):
            out[field] = _number(value)
        elif field.endswith("_year"):
            out[field] = _year(value)
        else:
            out[field] = clean_text(value) or None
    return schema.prune_by_route(out)


# --------------------------------------------------------------- validation
def _valid_name(name: str) -> bool:
    if not 2 <= len(name) <= 100:
        return False
    # Letters (any language), combining marks such as Hindi vowel signs, spaces, dot, apostrophe, hyphen.
    ok = all(ch.isalpha() or unicodedata.category(ch).startswith("M") or ch in " .'-" for ch in name)
    return ok and any(ch.isalpha() for ch in name)


def validate_registration(course: dict | None, data: dict, today: date | None = None) -> dict[str, str]:
    """Check one registration. `course` is the chosen course record (or None if nothing is chosen)."""
    today = today or date.today()
    d = normalize(data)
    errors: dict[str, str] = {}

    if course is None:
        errors["course_id"] = "Select a course to register for."
    route = d.get("qualification_route")
    allowed = schema.qualification_routes(course) if course else []
    if course and route not in allowed:
        errors["qualification_route"] = "Choose how you are applying to this course."
        route = None

    required = set(schema.required_fields(route, d.get("class12_result_status")))

    def missing(field: str) -> bool:
        value = d.get(field)
        return field in required and (value in (None, "", []) or value is False)

    # Basic information
    if missing("full_name"):
        errors["full_name"] = "Enter your full name."
    elif d["full_name"] and not _valid_name(d["full_name"]):
        errors["full_name"] = "Use letters, spaces, dots, apostrophes or hyphens only (2 to 100 characters)."

    if missing("email"):
        errors["email"] = "Enter your email address."
    elif d["email"] and (len(d["email"]) > 254 or not EMAIL_RE.match(d["email"]) or ".." in d["email"]):
        errors["email"] = "Enter a valid email address, for example name@example.com."

    if missing("mobile"):
        errors["mobile"] = "Enter your mobile number."
    elif d["mobile"] and not re.fullmatch(r"\+91[6-9]\d{9}", d["mobile"]):
        errors["mobile"] = "Enter a 10-digit Indian mobile number starting with 6, 7, 8 or 9."

    if d["date_of_birth"]:
        try:
            born = date.fromisoformat(d["date_of_birth"])
            age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
            if born > today or not MIN_AGE <= age <= MAX_AGE:
                errors["date_of_birth"] = f"Check your date of birth. Applicants are expected to be {MIN_AGE} to {MAX_AGE} years old."
        except ValueError:
            errors["date_of_birth"] = "Enter a valid date of birth."

    for field, allowed_values in (("gender", schema.GENDERS), ("state", schema.STATES)):
        if d.get(field) and d[field] not in allowed_values:
            errors[field] = "Choose one of the listed options."

    # Academic qualifications
    def check_percentage(field: str, label: str):
        value = d.get(field)
        if missing(field):
            errors[field] = f"Enter your {label}."
        elif value is not None and (isinstance(value, bool) or not isinstance(value, float)
                                    or math.isnan(value) or not 0 <= value <= 100):
            errors[field] = "Enter a percentage between 0 and 100."

    def check_year(field: str):
        value = d.get(field)
        if missing(field):
            errors[field] = "Choose the year of passing."
        elif value is not None and (not isinstance(value, int) or not today.year - YEARS_BACK <= value <= today.year + 1):
            errors[field] = f"Choose a year between {today.year - YEARS_BACK} and {today.year + 1}."

    def check_text(field: str, label: str):
        if missing(field):
            errors[field] = f"Enter your {label}."
        elif d.get(field) and len(d[field]) > MAX_TEXT:
            errors[field] = f"Keep this under {MAX_TEXT} characters."

    check_percentage("class10_percentage", "Class 10 percentage")
    if d.get("class10_percentage") is None:
        errors.pop("class10_percentage", None)

    if route == schema.ROUTE_CLASS12:
        if missing("class12_board"):
            errors["class12_board"] = "Choose your Class 12 board."
        elif d["class12_board"] not in schema.BOARDS:
            errors["class12_board"] = "Choose one of the listed boards."
        if missing("class12_stream"):
            errors["class12_stream"] = "Choose your Class 12 stream."
        elif d["class12_stream"] not in schema.STREAMS:
            errors["class12_stream"] = "Choose one of the listed streams."
        if missing("class12_subjects"):
            errors["class12_subjects"] = "Select the subjects you studied in Class 12."
        elif any(s not in schema.CLASS12_SUBJECTS for s in d["class12_subjects"]):
            errors["class12_subjects"] = "Choose subjects from the list, or add others in the box below."
        if d.get("class12_other_subjects") and len(d["class12_other_subjects"]) > MAX_TEXT:
            errors["class12_other_subjects"] = f"Keep this under {MAX_TEXT} characters."
        if missing("class12_result_status"):
            errors["class12_result_status"] = "Choose whether your Class 12 result is declared or awaited."
        elif d["class12_result_status"] not in (schema.RESULT_DECLARED, schema.RESULT_AWAITED):
            errors["class12_result_status"] = "Choose Declared or Awaited."
        check_percentage("class12_percentage", "Class 12 percentage")
        check_year("class12_year")
    elif route == schema.ROUTE_DIPLOMA:
        check_text("diploma_branch", "diploma branch")
        check_percentage("diploma_percentage", "diploma percentage")
        check_year("diploma_year")
    elif route == schema.ROUTE_DEGREE:
        check_text("degree_name", "degree name")
        check_text("degree_discipline", "degree discipline")
        check_percentage("degree_percentage", "degree percentage")
        check_year("degree_year")

    if d.get("entrance_exam_details") and len(d["entrance_exam_details"]) > MAX_TEXT:
        errors["entrance_exam_details"] = f"Keep this under {MAX_TEXT} characters."

    # Declaration and consent
    if missing("declaration_accurate"):
        errors["declaration_accurate"] = "Tick the declaration to confirm your answers are accurate."
    if missing("privacy_acknowledged"):
        errors["privacy_acknowledged"] = "Tick the box to confirm you have read the privacy notice."

    return errors
