"""admin_service.py - every administrative operation in one place.

Each function takes the session token FIRST and calls admin_auth.require(token) before doing anything, so the
authorisation check happens on the server for every create, read, update and delete, whatever the page that
called it. The public pages never import this module. Inputs are validated here (ValidationError carries one
message per field) and every change is written to the audit log.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

from PIL import Image

import admin_auth as auth
import catalogue_db as cat
import content_db as content
import faculty_db as fdb
from data import BASE_DIR

LEVELS = ("Undergraduate", "Postgraduate")
SUBJECTS = ("physics", "chemistry", "mathematics", "biology", "computer science", "technical vocational subject")
DESIGNATIONS = ("Professor", "Associate Professor", "Assistant Professor", "Lecturer")
FACULTY_PHOTOS = BASE_DIR / "assets" / "faculty"
MAX_IMAGE_BYTES = 2 * 1024 * 1024
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,200}\.[^@\s.]{2,}$")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


class ValidationError(Exception):
    """One or more fields are not acceptable. `errors` maps a field name to a message for the user."""

    def __init__(self, errors: dict[str, str]):
        super().__init__("; ".join(errors.values()))
        self.errors = errors


# ---------------------------------------------------------------- helpers
def _text(value, label: str, limit: int, errors: dict, key: str, required: bool = False) -> str:
    text = _CONTROL.sub("", "" if value is None else str(value)).strip()
    if required and not text:
        errors[key] = f"{label} is required."
    elif len(text) > limit:
        errors[key] = f"{label} must be at most {limit} characters."
    return text


def _int(value, label: str, low: int, high: int, errors: dict, key: str) -> int:
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        errors[key] = f"{label} must be a whole number."
        return 0
    if not low <= number <= high:
        errors[key] = f"{label} must be between {low} and {high}."
    return number


def _lines(value, label: str, errors: dict, key: str, limit: int = 150, max_items: int = 30) -> list[str]:
    raw = value if isinstance(value, (list, tuple)) else str(value or "").splitlines()
    items = []
    for line in raw:
        line = _CONTROL.sub("", str(line)).strip()
        if line and line.lower() not in [i.lower() for i in items]:
            items.append(line)
    if len(items) > max_items or any(len(i) > limit for i in items):
        errors[key] = f"{label}: at most {max_items} items of {limit} characters each."
    return items


def _raise(errors: dict) -> None:
    if errors:
        raise ValidationError(errors)


def _store_image(directory: Path, stem: str, data: bytes, filename: str) -> None:
    """Validate an uploaded picture, re-encode it as a clean JPEG (this drops hidden metadata) and save it."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", stem):
        raise ValueError("Invalid image name.")
    if Path(filename or "").suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
        raise ValidationError({"image": "Upload a JPG, PNG or WebP image."})
    if len(data) > MAX_IMAGE_BYTES:
        raise ValidationError({"image": "The image must be 2 MB or smaller."})
    try:
        probe = Image.open(io.BytesIO(data))
        if probe.width > 6000 or probe.height > 6000:
            raise ValidationError({"image": "The image is too large (maximum 6000 x 6000 pixels)."})
        probe.verify()
        picture = Image.open(io.BytesIO(data))
        picture.load()
    except ValidationError:
        raise
    except Exception:
        raise ValidationError({"image": "That file is not a valid image."}) from None
    picture = picture.convert("RGB")
    picture.thumbnail((1200, 1200))
    directory.mkdir(parents=True, exist_ok=True)
    for old in directory.glob(f"{stem}.*"):
        old.unlink()
    picture.save(directory / f"{stem}.jpg", "JPEG", quality=85)


# -------------------------------------------------------------- dashboard
def dashboard(token: str) -> dict:
    auth.require(token)
    courses = cat.all_courses()
    faculty = fdb.load_directory(published_only=False)["faculty"]
    achievements = content.list_achievements()
    linked = fdb.linked_course_ids()
    return {
        "courses_total": len(courses), "courses_published": sum(c["published"] for c in courses),
        "faculty_total": len(faculty), "faculty_published": sum(f["published"] for f in faculty),
        "achievements_total": len(achievements), "achievements_published": sum(a["published"] for a in achievements),
        "enquiries": content.enquiry_counts(), "drafts": content.pending_drafts(),
        "unlinked_courses": [c["name"] for c in courses if c["id"] not in linked],
        "course_problems": cat.problems(),
    }


# ------------------------------------------------------- site content forms
def get_form(token: str, keys: list[str]) -> dict:
    auth.require(token)
    values, drafted = content.form_values(keys)
    effective = content.effective_values()
    return {"values": values, "has_draft": drafted, "published": {k: effective[k] for k in keys}}


def save_content_draft(token: str, values: dict) -> None:
    user = auth.require(token)
    clean, errors = {}, {}
    for key, raw in values.items():
        field = content.FIELDS.get(key)
        if field is None:
            raise ValueError(f"Unknown setting '{key}'.")
        clean[key], message = content.validate_value(field, raw)
        if message:
            errors[key] = message
    _raise(errors)
    effective = content.effective_values()
    changed = {k: v for k, v in clean.items() if v != effective[k]}
    if changed:
        content.save_drafts(changed, user.email)                      # only what really differs becomes a draft
    unchanged = [k for k in clean if k not in changed]
    if unchanged:
        content.discard_drafts(unchanged)                             # editing a value back to the published one clears its draft
    auth.audit(user.email, "content_draft_saved", "site_content", "", ", ".join(sorted(changed)))


def publish_content(token: str, keys: list[str]) -> int:
    user = auth.require(token)
    count = content.publish_keys(keys, user.email)
    auth.audit(user.email, "content_published", "site_content", "", ", ".join(keys))
    return count


def discard_content_draft(token: str, keys: list[str]) -> None:
    user = auth.require(token)
    content.discard_drafts(keys)
    auth.audit(user.email, "content_draft_discarded", "site_content", "", ", ".join(keys))


# --------------------------------------------------------------- courses
def list_courses(token: str) -> list[dict]:
    auth.require(token)
    departments = fdb.course_departments()
    return [dict(c, department=departments.get(c["id"], "")) for c in cat.all_courses()]


def get_course(token: str, course_id: str) -> dict | None:
    auth.require(token)
    return next((c for c in list_courses(token) if c["id"] == course_id), None)


def _published_count(excluding: str | None = None) -> int:
    return sum(1 for c in cat.all_courses() if c["published"] and c["id"] != excluding)


def _publishable(course: dict) -> str | None:
    if course["tuition"] <= 0:
        return "Set the annual tuition fee under Fees and Eligibility before publishing this course."
    if course["seats"] <= 0:
        return "Set the seat capacity under Fees and Eligibility before publishing this course."
    return None


def save_course(token: str, form: dict, course_id: str | None = None, status: str = "keep") -> str:
    """Create or update a course's general details. status: 'draft', 'publish' or 'keep' (unchanged; drafts for new)."""
    user = auth.require(token)
    errors: dict = {}
    name = _text(form.get("name"), "Course name", 150, errors, "name", True)
    if name and len(name) < 3:
        errors["name"] = "Course name must be at least 3 characters."
    category = _text(form.get("category"), "Category", 60, errors, "category", True)
    group = _text(form.get("group"), "Programme group", 80, errors, "group", True)
    level = form.get("level")
    if level not in LEVELS:
        errors["level"] = "Choose Undergraduate or Postgraduate."
    years = _int(form.get("years"), "Duration (years)", 1, 8, errors, "years")
    overview = _text(form.get("overview"), "Description", 2000, errors, "overview")
    specialisations = _lines(form.get("specialisations"), "Specialisations", errors, "specialisations")
    subjects = _lines(form.get("subjects"), "Major subjects", errors, "subjects")
    careers = _lines(form.get("careers"), "Career opportunities", errors, "careers")
    higher = _lines(form.get("higher_studies"), "Higher-study options", errors, "higher_studies")
    documents = _lines(form.get("documents"), "Required documents", errors, "documents")
    department = (form.get("department") or "").strip()
    if department and department not in fdb.department_names():
        errors["department"] = "Choose one of the existing departments."
    if name and cat.course_name_taken(name, course_id):
        errors["name"] = f"A course named '{name}' already exists."
    _raise(errors)

    fields = dict(name=name, category=category, group=group, level=level, years=years, overview=overview,
                  specialisations=specialisations, subjects=subjects, careers=careers, higher_studies=higher,
                  documents=documents, is_sample=bool(form.get("is_sample", True)))
    if course_id is None:
        course_id = cat.new_course_id(name)
        cat.add_course(course_id, name, group=group, category=category, years=years, tuition=0, seats=0)
        cat.update_course(course_id, **{k: v for k, v in fields.items() if k not in ("name", "category", "group", "years")},
                          published=False)
        action = "course_created"
    else:
        if not any(c["id"] == course_id for c in cat.all_courses()):
            raise ValidationError({"name": "That course no longer exists."})
        cat.update_course(course_id, **fields)
        action = "course_updated"
    fdb.set_course_department(course_id, department or None)
    if status == "publish":
        set_course_published(token, course_id, True)
    elif status == "draft":
        set_course_published(token, course_id, False)
    auth.audit(user.email, action, "course", course_id, name)
    return course_id


def set_course_published(token: str, course_id: str, published: bool) -> None:
    user = auth.require(token)
    course = next((c for c in cat.all_courses() if c["id"] == course_id), None)
    if course is None:
        raise ValidationError({"course": "That course no longer exists."})
    if published:
        problem = _publishable(course)
        if problem:
            raise ValidationError({"course": problem})
    elif course["published"] and _published_count(excluding=course_id) == 0:
        raise ValidationError({"course": "At least one course must stay published, because the public site needs a catalogue."})
    cat.update_course(course_id, published=published)
    auth.audit(user.email, "course_published" if published else "course_unpublished", "course", course_id, course["name"])


def delete_course(token: str, course_id: str, confirm: str) -> None:
    user = auth.require(token)
    course = next((c for c in cat.all_courses() if c["id"] == course_id), None)
    if course is None:
        raise ValidationError({"course": "That course no longer exists."})
    if (confirm or "").strip() != course_id:
        raise ValidationError({"confirm": f"Type the course id '{course_id}' exactly to confirm."})
    if course["published"] and _published_count(excluding=course_id) == 0:
        raise ValidationError({"course": "At least one course must stay published, so this one cannot be deleted."})
    cat.delete_course_row(course_id)
    fdb.set_course_department(course_id, None)
    auth.audit(user.email, "course_deleted", "course", course_id, course["name"])


def save_course_terms(token: str, course_id: str, terms: dict) -> None:
    """Fees, seats and eligibility of one course."""
    user = auth.require(token)
    course = next((c for c in cat.all_courses() if c["id"] == course_id), None)
    if course is None:
        raise ValidationError({"course": "That course no longer exists."})
    errors: dict = {}
    tuition = _int(terms.get("tuition"), "Annual tuition fee", 0, 10_000_000, errors, "tuition")
    seats = _int(terms.get("seats"), "Seat capacity", 0, 100_000, errors, "seats")
    min_pct = _int(terms.get("min_pct"), "Minimum marks (%)", 0, 100, errors, "min_pct")
    class12 = _text(terms.get("class12"), "Class 12 requirement", 300, errors, "class12")
    degree = _text(terms.get("degree"), "Bachelor's degree requirement", 300, errors, "degree")
    diploma = _text(terms.get("diploma"), "Diploma pathway", 500, errors, "diploma")
    mode = _text(terms.get("admission_mode"), "Admission mode", 300, errors, "admission_mode")
    if course["published"] and tuition == 0:
        errors["tuition"] = "A published course needs an annual fee above 0. Unpublish it first to clear the fee."
    if course["published"] and seats == 0:
        errors["seats"] = "A published course needs a seat capacity above 0."
    required, one_of = list(terms.get("required_all") or []), list(terms.get("one_of") or [])
    if any(s not in SUBJECTS for s in required + one_of):
        errors["required_all"] = "Choose subjects from the list."
    rule: dict = {}
    if course["level"] == "Postgraduate":
        if not degree:
            errors["degree"] = "Describe the bachelor's degree requirement for this postgraduate course."
    else:
        if not class12:
            errors["class12"] = "Describe the Class 12 requirement."
        if terms.get("any_stream"):
            rule = {"any_stream": True}
        elif (terms.get("unverified_note") or "").strip():
            rule = {"unverified": _text(terms.get("unverified_note"), "Note", 300, errors, "unverified_note")}
        elif not required and not one_of:
            errors["required_all"] = "Choose the required subjects, or tick 'Any Class 12 stream is accepted'."
        else:
            if required:
                rule["all"] = required
            if one_of:
                rule["one_of"] = [one_of]
    _raise(errors)
    cat.update_course(course_id, tuition=tuition, seats=seats, min_pct=min_pct, class12=class12 or None,
                      degree=degree or None, diploma=diploma or None, admission_mode=mode, req12=rule)
    auth.audit(user.email, "course_terms_updated", "course", course_id,
               f"tuition {tuition}, seats {seats}, min {min_pct}%")


# --------------------------------------------------------------- faculty
def list_faculty(token: str) -> dict:
    auth.require(token)
    return {"faculty": fdb.load_directory(published_only=False)["faculty"], "departments": fdb.department_names()}


def save_faculty(token: str, form: dict, faculty_id: int | None = None, status: str = "keep") -> int:
    user = auth.require(token)
    errors: dict = {}
    name = _text(form.get("name"), "Full name", 120, errors, "name", True)
    designation = _text(form.get("designation"), "Designation", 60, errors, "designation", True)
    post = _text(form.get("post"), "Administrative post", 80, errors, "post")
    department = (form.get("department") or "").strip()
    if department not in fdb.department_names():
        errors["department"] = "Choose one of the existing departments."
    qualifications = _text(form.get("qualifications"), "Qualifications", 200, errors, "qualifications")
    specialization = _text(form.get("specialization"), "Specialization", 120, errors, "specialization")
    teaching = _int(form.get("teaching_years", 0), "Years of teaching", 0, 60, errors, "teaching_years")
    industry = _int(form.get("industry_years", 0), "Years of industry experience", 0, 60, errors, "industry_years")
    interests = _text(form.get("research_interests"), "Research interests", 300, errors, "research_interests")
    description = _text(form.get("description"), "Profile description", 1500, errors, "description")
    email = _text(form.get("email"), "Official email", 120, errors, "email")
    if email and not _EMAIL.match(email):
        errors["email"] = "Enter a valid email address."
    phone = _text(form.get("phone"), "Phone", 30, errors, "phone")
    if phone and not re.fullmatch(r"\+?[\d\s().-]{7,25}", phone):
        errors["phone"] = "Enter a valid phone number."
    office = _text(form.get("office"), "Office location", 120, errors, "office")
    hours = _text(form.get("consultation_hours"), "Consultation hours", 120, errors, "consultation_hours")
    subjects = _lines(form.get("subjects"), "Subjects taught", errors, "subjects")
    existing = fdb.load_directory(published_only=False)["faculty"]
    if name and any(f["name"].lower() == name.lower() and f["department"] == department and f["id"] != faculty_id for f in existing):
        errors["name"] = f"{name} already has a profile in {department}."
    _raise(errors)
    current = next((f for f in existing if f["id"] == faculty_id), None)
    if faculty_id is not None and current is None:
        raise ValidationError({"name": "That profile no longer exists."})
    published = {"publish": True, "draft": False}.get(status, current["published"] if current else False)
    rec = dict(name=name, designation=designation, post=post, qualifications=qualifications, specialization=specialization,
               teaching_years=teaching, industry_years=industry, research_interests=interests, description=description,
               email=email, phone=phone, office=office, consultation_hours=hours, is_sample=bool(form.get("is_sample", False)))
    new_id = fdb.save_faculty(rec, department, subjects, published, faculty_id)
    auth.audit(user.email, "faculty_updated" if faculty_id else "faculty_created", "faculty", new_id, name)
    return new_id


def set_faculty_published(token: str, faculty_id: int, published: bool) -> None:
    user = auth.require(token)
    fdb.set_faculty_published(faculty_id, published)
    auth.audit(user.email, "faculty_published" if published else "faculty_unpublished", "faculty", faculty_id)


def delete_faculty(token: str, faculty_id: int, confirm: str) -> None:
    user = auth.require(token)
    person = next((f for f in fdb.load_directory(published_only=False)["faculty"] if f["id"] == faculty_id), None)
    if person is None:
        raise ValidationError({"faculty": "That profile no longer exists."})
    if (confirm or "").strip() != person["name"]:
        raise ValidationError({"confirm": f"Type the name '{person['name']}' exactly to confirm."})
    slug = fdb.delete_faculty(faculty_id)
    for old in FACULTY_PHOTOS.glob(f"{slug}.*") if FACULTY_PHOTOS.exists() else []:
        old.unlink()
    auth.audit(user.email, "faculty_deleted", "faculty", faculty_id, person["name"])


def save_faculty_image(token: str, faculty_id: int, data: bytes, filename: str) -> None:
    user = auth.require(token)
    person = next((f for f in fdb.load_directory(published_only=False)["faculty"] if f["id"] == faculty_id), None)
    if person is None:
        raise ValidationError({"image": "Save the profile first, then add its photo."})
    _store_image(FACULTY_PHOTOS, person["slug"], data, filename)
    auth.audit(user.email, "faculty_photo_updated", "faculty", faculty_id)


# ---------------------------------------------------------- achievements
def list_achievements(token: str) -> list[dict]:
    auth.require(token)
    return content.list_achievements()


def save_achievement(token: str, form: dict, achievement_id: int | None = None, status: str = "keep") -> int:
    user = auth.require(token)
    clean, errors = content.clean_achievement(form)
    if not errors and content.title_taken(clean["title"], clean["achieved_on"], achievement_id):
        errors["title"] = "An achievement with this title and date already exists."
    _raise(errors)
    current = content.get_achievement(achievement_id) if achievement_id else None
    if achievement_id and current is None:
        raise ValidationError({"title": "That achievement no longer exists."})
    published = {"publish": True, "draft": False}.get(status, current["published"] if current else False)
    new_id = content.save_achievement(clean, published, user.email, achievement_id)
    auth.audit(user.email, "achievement_updated" if achievement_id else "achievement_created", "achievement", new_id, clean["title"])
    return new_id


def set_achievement_published(token: str, achievement_id: int, published: bool) -> None:
    user = auth.require(token)
    content.set_achievement_published(achievement_id, published, user.email)
    auth.audit(user.email, "achievement_published" if published else "achievement_unpublished", "achievement", achievement_id)


def delete_achievement(token: str, achievement_id: int, confirm: str) -> None:
    user = auth.require(token)
    item = content.get_achievement(achievement_id)
    if item is None:
        raise ValidationError({"title": "That achievement no longer exists."})
    if (confirm or "").strip() != item["title"]:
        raise ValidationError({"confirm": f"Type the title '{item['title']}' exactly to confirm."})
    content.delete_achievement(achievement_id)
    for old in content.ACHIEVEMENT_IMAGES.glob(f"{achievement_id}.*") if content.ACHIEVEMENT_IMAGES.exists() else []:
        old.unlink()
    auth.audit(user.email, "achievement_deleted", "achievement", achievement_id, item["title"])


def save_achievement_image(token: str, achievement_id: int, data: bytes, filename: str) -> None:
    user = auth.require(token)
    if content.get_achievement(achievement_id) is None:
        raise ValidationError({"image": "Save the achievement first, then add its picture."})
    _store_image(content.ACHIEVEMENT_IMAGES, str(achievement_id), data, filename)
    auth.audit(user.email, "achievement_image_updated", "achievement", achievement_id)


# ------------------------------------------------------------- enquiries
def list_enquiries(token: str, **filters) -> list[dict]:
    auth.require(token)
    return content.list_enquiries(**filters)


def get_enquiry(token: str, enquiry_id: int) -> dict | None:
    auth.require(token)
    return content.get_enquiry(enquiry_id)


def update_enquiry(token: str, enquiry_id: int, status: str, note: str) -> None:
    user = auth.require(token)
    if len(note or "") > 1000:
        raise ValidationError({"note": "The note must be at most 1000 characters."})
    content.set_enquiry_status(enquiry_id, status, note, user.email)
    auth.audit(user.email, "enquiry_status_changed", "enquiry", enquiry_id, status)


def export_enquiries_csv(token: str, **filters) -> str:
    user = auth.require(token)
    rows = content.list_enquiries(**filters)
    auth.audit(user.email, "enquiries_exported", "enquiry", "", f"{len(rows)} records")
    return content.enquiries_csv(rows)
