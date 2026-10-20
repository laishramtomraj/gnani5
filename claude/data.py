"""Single source of college data.

Replace placeholders with VERIFIED college information. Nothing here should be
treated as real institutional data until the college confirms it.
Later phases can swap these lists for database queries.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

COLLEGE = {
    "name": "College Name",                  # placeholder until identity is chosen
    "short_name": "CN",
    "tagline": "Discover Your Future. Begin Your Journey.",
    # SAMPLE contact details for the prototype. Placeholders, not a real college's details.
    "address": "Knowledge Park, Sector 12, Bengaluru, Karnataka, India – 560001",
    "phone": "+91 98765 43210",
    "email": "info@yourcollege.example",
    "office_hours": "Monday–Saturday, 9:00 AM–5:00 PM; Sunday closed.",
    "admissions_phone": "+91 91234 56780",
    "admissions_email": "admissions@yourcollege.example",
}

# Verified achievements only. Each item: {"label": ..., "value": ..., "source": ...}
ACHIEVEMENTS: list[dict] = []

# Each item: name, designation, qualifications, department, specialization,
# subjects, experience, interests. Text only, no photos.
FACULTY: list[dict] = []

# ---------------------------------------------------------------- courses
DATA_IS_SAMPLE = True
DATA_NOTICE = (
    "Illustrative sample data for prototype purposes, not verified details of a "
    "real institution. Fees are annual tuition estimates and exclude hostel, "
    "transport, examination, registration and other charges. Seat counts are "
    "sample intake targets, not confirmed sanctioned seats."
)

from course_catalogue import COURSES  # noqa: E402  (course data now lives in course_catalogue.py)

# Shown on the home page ONLY while ACHIEVEMENTS (above) is empty. Every figure except the programme
# count is an invented sample for the prototype. Replace them with verified college information.
ILLUSTRATIVE_ACHIEVEMENTS: list[dict] = [
    {"icon": ":material/school:", "title": "Programmes offered", "value": str(len(COURSES)),
     "description": "Undergraduate and postgraduate programmes in the course catalogue."},
    {"icon": ":material/work:", "title": "Placement support", "value": "85%",
     "description": "Sample figure: students placed through campus recruitment."},
    {"icon": ":material/handshake:", "title": "Industry partners", "value": "40+",
     "description": "Sample figure: companies engaged for internships and projects."},
    {"icon": ":material/science:", "title": "Research output", "value": "120+",
     "description": "Sample figure: papers and projects by students and faculty."},
    {"icon": ":material/groups:", "title": "Student clubs", "value": "25+",
     "description": "Sample figure: technical, cultural and sports clubs."},
    {"icon": ":material/emoji_events:", "title": "Awards and recognitions", "value": "30+",
     "description": "Sample figure: student and faculty awards."},
]


def format_inr(amount: int) -> str:
    """150000 -> ₹1,50,000 (Indian digit grouping)."""
    s = str(int(amount))
    if len(s) <= 3:
        return f"₹{s}"
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return "₹" + ",".join(parts + [tail])


def find_hero_image():
    """Returns the campus aerial image path if you've added one, else None."""
    return next((BASE_DIR / "assets").glob("campus-aerial.*"), None)