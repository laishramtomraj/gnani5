import io

import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps

import content_db
import faculty_db
from data import BASE_DIR
from faculty_seed import SAMPLE_NOTICE

PHOTO_DIR = BASE_DIR / "assets" / "faculty"        # optional real photos: assets/faculty/<slug>.jpg
NAVY, TEAL = (11, 31, 63), (25, 167, 160)
NONE = "None listed"
ALL_DEPTS, ALL = "All departments", "All"


# ------------------------------------------------------------------ data
@st.cache_data(show_spinner=False)
def load(stamp: float) -> dict:
    return faculty_db.load_directory()


faculty_db.init_db()
directory = load(faculty_db.DB_PATH.stat().st_mtime)
people = directory["faculty"]


# ---------------------------------------------------------------- photos
def _initials(name: str) -> str:
    words = [w for w in name.split() if w.lower() not in {"dr.", "mr.", "ms.", "prof."}]
    return "".join(w[0] for w in words[:2]).upper()


@st.cache_data(show_spinner=False)
def _avatar(initials: str, photo: str | None, mtime: float | None, size: int = 320) -> bytes:
    """Round profile picture: the real photo if supplied, else an initials placeholder."""
    if photo:
        img = ImageOps.fit(Image.open(photo).convert("RGB"), (size, size))
    else:
        img = Image.new("RGB", (size, size), NAVY)
        draw = ImageDraw.Draw(img)
        draw.ellipse([14, 14, size - 15, size - 15], outline=TEAL, width=8)
        try:
            font = ImageFont.load_default(size=int(size * 0.34))
        except TypeError:                              # very old Pillow
            font = ImageFont.load_default()
        box = draw.textbbox((0, 0), initials, font=font)
        draw.text(((size - (box[2] - box[0])) / 2 - box[0], (size - (box[3] - box[1])) / 2 - box[1]),
                  initials, font=font, fill="white")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    img = img.convert("RGBA")
    img.putalpha(mask)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def avatar_for(f: dict) -> bytes:
    photo = next(PHOTO_DIR.glob(f"{f['slug']}.*"), None) if PHOTO_DIR.exists() else None
    return _avatar(_initials(f["name"]), str(photo) if photo else None,
                   photo.stat().st_mtime if photo else None)


# ---------------------------------------------------------------- helpers
def bullets(text: str | None) -> None:
    items = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if items:
        st.markdown("\n".join(f"- {i}" for i in items))
    else:
        st.caption(NONE)


def experience(f: dict) -> str:
    t, i = f["teaching_years"], f["industry_years"]
    return f"{t if t is not None else '-'} yrs teaching · {i if i is not None else '-'} yrs industry"


# ------------------------------------------------------- detailed profile
@st.dialog("Faculty profile", width="large")
def profile_dialog(f: dict) -> None:
    pic, head = st.columns([1, 4], vertical_alignment="center")
    pic.image(avatar_for(f), width=110)
    with head:
        st.subheader(f["name"], anchor=False)
        st.write(f["designation"] + (f" · {f['post']}" if f["post"] else ""))
        st.caption(f["department"])
        if f["is_sample"]:
            st.badge("Sample data", color="orange")

    overview, teaching, contact = st.tabs(["Overview", "Teaching & research", "Contact"])
    with overview:
        if f.get("description"):
            st.write(f["description"])
        st.write(f"**Qualifications:** {f['qualifications'] or NONE}")
        st.write(f"**Specialization:** {f['specialization'] or NONE}")
        st.write(f"**Experience:** {experience(f)}")
        st.write(f"**Programmes taught in this department:** {', '.join(f['courses']) or NONE}")
        st.write(f"**Certifications:**")
        bullets(f["certifications"])
        st.write("**Achievements:**")
        bullets(f["achievements"])
    with teaching:
        st.write("**Subjects taught**")
        bullets("\n".join(f["subjects"]))
        st.write(f"**Research interests and expertise:** {f['research_interests'] or NONE}")
        st.write("**Research publications**")
        bullets(f["publications"])
        st.write("**Patents**")
        bullets(f["patents"])
        st.write("**Projects**")
        bullets(f["projects"])
    with contact:
        st.write("**Official email:** " + (f"[{f['email']}](mailto:{f['email']})" if f["email"] else NONE))
        st.write(f"**Phone:** {f['phone'] or NONE}")
        st.write(f"**Office location:** {f['office'] or NONE}")
        st.write(f"**Consultation hours:** {f['consultation_hours'] or NONE}")
        if f["is_sample"]:
            st.caption("Sample contact details for the prototype. They are not real.")


# ------------------------------------------------------------------- card
def card(f: dict) -> None:
    with st.container(border=True):
        pic, head = st.columns([1, 3], vertical_alignment="center")
        pic.image(avatar_for(f), width=72)
        with head:
            st.markdown(f"**{f['name']}**")
            st.caption(f["designation"] + (f" · {f['post']}" if f["post"] else ""))
        st.caption(f["department"].upper())
        st.write(f"**Qualifications:** {f['qualifications'] or NONE}")
        st.write(f"**Specialization:** {f['specialization'] or NONE}")
        st.write(f"**Experience:** {experience(f)}")
        shown = ", ".join(f["subjects"][:3]) or NONE
        st.write(f"**Subjects:** {shown}" + (f" +{len(f['subjects']) - 3} more" if len(f["subjects"]) > 3 else ""))
        if st.button("View profile", key=f"view_{f['slug']}", width="stretch"):
            profile_dialog(f)


def grid(items: list[dict]) -> None:
    for i in range(0, len(items), 3):
        row = items[i:i + 3]
        for col, f in zip(st.columns(3), row):
            with col:
                card(f)


# ------------------------------------------------------------------- page
st.title("Faculty", anchor=False)
if content_db.text("show_prototype_notice") and any(f["is_sample"] for f in people):
    st.info(SAMPLE_NOTICE, icon=":material/info:")

c1, c2, c3, c4 = st.columns([2, 2, 1.5, 2])
query = c1.text_input("Search by name", placeholder="e.g. Menon").strip().casefold()
dept = c2.selectbox("Department", [ALL_DEPTS] + [d["name"] for d in directory["departments"]])

in_dept = [f for f in people if dept == ALL_DEPTS or f["department"] == dept]
rank = ["Professor", "Associate Professor", "Assistant Professor", "Lecturer"]
present = {f["designation"] for f in people}
designation = c3.selectbox("Designation", [ALL] + [d for d in rank if d in present] + sorted(present - set(rank)))
specialization = c4.selectbox("Specialization", [ALL] + sorted({f["specialization"] for f in in_dept if f["specialization"]}))

results = [
    f for f in in_dept
    if query in f["name"].casefold()
    and (designation == ALL or f["designation"] == designation)
    and (specialization == ALL or f["specialization"] == specialization)
]

if dept != ALL_DEPTS:
    info = next(d for d in directory["departments"] if d["name"] == dept)
    st.subheader(dept, anchor=False)
    st.write("**Programmes:** " + (", ".join(info["courses"]) or NONE))

st.caption(f"{len(results)} faculty member(s) shown")

if not results:
    st.warning("No faculty members match your search and filters.")
elif dept == ALL_DEPTS:
    for d in directory["departments"]:                 # organised by department
        group = [f for f in results if f["department"] == d["name"]]
        if group:
            st.subheader(d["name"], anchor=False)
            grid(group)
else:
    grid(results)
