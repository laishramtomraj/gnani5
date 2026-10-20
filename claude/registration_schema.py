"""registration_schema.py - the registration fields, form options and status names in one place.

Pure Python (no Streamlit, no database). The form, the validator, the database layer and, later,
the College Admission Assistant all read the same field names from here.
"""
from __future__ import annotations

# ------------------------------------------------------------------ statuses
STATUS_SUBMITTED = "Submitted"
STATUS_UNDER_REVIEW = "Under review"
STATUS_INFO_REQUIRED = "Additional information required"
STATUS_APPROVED = "Approved"
STATUS_REJECTED = "Rejected"

# Every status the data model can hold. Today the website itself only ever sets STATUS_SUBMITTED:
# there is no admissions-officer screen yet, so nothing moves a registration to another status.
STATUSES = (STATUS_SUBMITTED, STATUS_UNDER_REVIEW, STATUS_INFO_REQUIRED, STATUS_APPROVED, STATUS_REJECTED)
INITIAL_STATUS = STATUS_SUBMITTED

STATUS_MEANINGS = {
    STATUS_SUBMITTED: "Your registration is saved and is waiting for the college's review. It has not been reviewed yet.",
    STATUS_UNDER_REVIEW: "The college is reviewing your registration.",
    STATUS_INFO_REQUIRED: "The college needs more information from you. Read the note shown with this status.",
    STATUS_APPROVED: "The college has approved your registration. Approved students continue with the remaining admission requirements.",
    STATUS_REJECTED: "The college has not approved this registration.",
}

# ------------------------------------------------------- qualification routes
ROUTE_CLASS12 = "class12"
ROUTE_DIPLOMA = "diploma"
ROUTE_DEGREE = "degree"
ROUTE_LABELS = {
    ROUTE_CLASS12: "Class 12 or equivalent",
    ROUTE_DIPLOMA: "Diploma (lateral entry)",
    ROUTE_DEGREE: "Bachelor's degree",
}

RESULT_DECLARED = "Declared"
RESULT_AWAITED = "Awaited"


def qualification_routes(course: dict) -> list[str]:
    """How a student can apply to this course, based only on the course record.

    Postgraduate courses (or any course that stores a 'degree' requirement) use the bachelor's-degree
    route. Other courses use Class 12, plus a diploma route only when the course stores a diploma pathway.
    """
    if course.get("level") == "Postgraduate" or course.get("degree"):
        return [ROUTE_DEGREE]
    routes = [ROUTE_CLASS12]
    if course.get("diploma"):
        routes.append(ROUTE_DIPLOMA)
    return routes


# ------------------------------------------------------------- form options
BOARDS = ["CBSE", "ICSE / ISC", "State board", "NIOS", "International board (IB or Cambridge)", "Other"]
STREAMS = ["Science", "Commerce", "Arts or Humanities", "Vocational", "Other"]
GENDERS = ["Female", "Male", "Non-binary", "Prefer not to say"]
CLASS12_SUBJECTS = [
    "Physics", "Chemistry", "Mathematics", "Biology", "Computer Science", "Statistics",
    "Electronics", "Economics", "Accountancy", "Business Studies", "English",
]
STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana",
    "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
    "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal", "Andaman and Nicobar Islands", "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep",
    "Puducherry", "Outside India",
]

# ------------------------------------------------------------- field list
# Canonical field names. The database columns, the form and the validator all use these names.
ALL_FIELDS = (
    "full_name", "email", "mobile", "date_of_birth", "gender", "state",
    "qualification_route",
    "class10_percentage",
    "class12_board", "class12_stream", "class12_subjects", "class12_other_subjects",
    "class12_result_status", "class12_percentage", "class12_year",
    "diploma_branch", "diploma_percentage", "diploma_year",
    "degree_name", "degree_discipline", "degree_percentage", "degree_year",
    "entrance_exam_details",
    "declaration_accurate", "privacy_acknowledged",
)

BASIC_REQUIRED = ("full_name", "email", "mobile", "qualification_route", "declaration_accurate", "privacy_acknowledged")

_ROUTE_FIELDS = {
    ROUTE_CLASS12: ("class12_board", "class12_stream", "class12_subjects", "class12_other_subjects",
                    "class12_result_status", "class12_percentage", "class12_year"),
    ROUTE_DIPLOMA: ("diploma_branch", "diploma_percentage", "diploma_year"),
    ROUTE_DEGREE: ("degree_name", "degree_discipline", "degree_percentage", "degree_year"),
}
_ALL_ROUTE_FIELDS = {f for fields in _ROUTE_FIELDS.values() for f in fields}

# Labels and help text. The form shows them, and the assistant can reuse them to explain a field.
FIELD_SPECS = {
    "full_name": {"label": "Full name", "help": "As it appears on your mark sheet."},
    "email": {"label": "Email address",
              "help": "You will need this email address, together with your reference number, to check your status."},
    "mobile": {"label": "Mobile number (India)", "help": "10 digits starting with 6, 7, 8 or 9. +91 is optional."},
    "date_of_birth": {"label": "Date of birth (optional)", "help": "Optional. Leave blank if you prefer."},
    "gender": {"label": "Gender (optional)", "help": "Optional."},
    "state": {"label": "State or region of residence (optional)", "help": "Optional."},
    "qualification_route": {"label": "How are you applying?", "help": "Choose the qualification you are applying with."},
    "class10_percentage": {"label": "Class 10 percentage (optional)", "help": "Optional. Enter a number from 0 to 100."},
    "class12_board": {"label": "Class 12 board", "help": "The board that conducted your Class 12 or equivalent examination."},
    "class12_stream": {"label": "Class 12 stream", "help": "Your main stream in Class 12."},
    "class12_subjects": {"label": "Subjects studied in Class 12",
                         "help": "Select every subject you studied. The course's subject requirement is shown above."},
    "class12_other_subjects": {"label": "Other subjects (optional)", "help": "Separate subjects with commas."},
    "class12_result_status": {"label": "Class 12 result", "help": "Choose 'Awaited' if your result is not out yet."},
    "class12_percentage": {"label": "Class 12 overall percentage", "help": "Enter a number from 0 to 100."},
    "class12_year": {"label": "Class 12 year of passing", "help": "Choose the expected year if your result is awaited."},
    "diploma_branch": {"label": "Diploma branch or discipline", "help": "For example, the engineering branch of your diploma."},
    "diploma_percentage": {"label": "Diploma overall percentage", "help": "Enter a number from 0 to 100."},
    "diploma_year": {"label": "Diploma year of passing", "help": "Choose the year you completed or will complete the diploma."},
    "degree_name": {"label": "Bachelor's degree name", "help": "For example, the degree title on your certificate."},
    "degree_discipline": {"label": "Degree discipline", "help": "Your main subject or branch."},
    "degree_percentage": {"label": "Degree overall percentage", "help": "Enter a number from 0 to 100."},
    "degree_year": {"label": "Degree year of passing", "help": "Choose the year you completed or will complete the degree."},
    "entrance_exam_details": {"label": "Entrance examination details (optional)",
                              "help": "Optional. Name of the exam, score or rank, if you have taken one."},
    "declaration_accurate": {"label": "Declaration",
                             "help": "You confirm that you have reviewed your answers and they are accurate."},
    "privacy_acknowledged": {"label": "Privacy notice", "help": "You confirm that you have read the privacy notice."},
}


def required_fields(route: str | None, result_status: str | None = None) -> list[str]:
    """Fields a student must fill for the chosen qualification route."""
    required = list(BASIC_REQUIRED)
    if route == ROUTE_CLASS12:
        required += ["class12_board", "class12_stream", "class12_subjects", "class12_result_status", "class12_year"]
        if result_status != RESULT_AWAITED:
            required.append("class12_percentage")
    elif route == ROUTE_DIPLOMA:
        required += ["diploma_branch", "diploma_percentage", "diploma_year"]
    elif route == ROUTE_DEGREE:
        required += ["degree_name", "degree_discipline", "degree_percentage", "degree_year"]
    return required


def prune_by_route(data: dict) -> dict:
    """Blank out academic fields that do not belong to the chosen route (stale answers are not stored)."""
    route = data.get("qualification_route")
    keep = set(_ROUTE_FIELDS.get(route, ()))
    return {k: (None if k in _ALL_ROUTE_FIELDS and k not in keep else v) for k, v in data.items()}
