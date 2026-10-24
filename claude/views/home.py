import streamlit as st

import content_db
from components import section_header
from data import ACHIEVEMENTS, COURSES, DATA_IS_SAMPLE
from hero import render_hero

# ------------------------------------------------------------------ HERO
render_hero()

st.write("")

# --------------------------------------------------------------- PILLARS
section_header("Why us", content_db.text("home_why_heading"))
pillars = [
    (":material/school:", "Education", "Structured programmes built on academic depth and real-world relevance."),
    (":material/lightbulb:", "Innovation", "An environment that encourages projects, research and new ideas."),
    (":material/emoji_people:", "Student Development", "Mentoring and skill-building beyond the classroom."),
    (":material/rocket_launch:", "Opportunities", "Pathways to internships, careers and higher studies."),
]
for col, (icon, title, text) in zip(st.columns(4), pillars):
    with col.container(border=True):
        st.markdown(f"#### {icon} {title}")
        st.write(text)

st.write("")

# ---------------------------------------------------------- ACHIEVEMENTS
section_header("Highlights", content_db.text("home_achievements_heading"))
if ACHIEVEMENTS:
    shown = ACHIEVEMENTS[:4]
    for col, item in zip(st.columns(len(shown)), shown):
        with col.container(border=True):
            st.metric(item["label"], item["value"], help=item["source"] or None)
    if len(ACHIEVEMENTS) > len(shown):
        st.page_link("views/about.py", label="See all achievements", icon=":material/arrow_forward:")
else:
    for col, label in zip(st.columns(4), ["Placement statistic", "Accreditation", "Award or ranking", "Students enrolled"]):
        with col.container(border=True):
            st.metric(label, "—", help="Add verified data in data.py (ACHIEVEMENTS).")

st.write("")

# --------------------------------------------------------- COURSE PREVIEW
section_header("Programmes", content_db.text("home_programmes_heading"))
groups: dict[str, list[str]] = {}
for c in COURSES:
    groups.setdefault(c["category"], []).append(c["name"])

for col, (category, names) in zip(st.columns(len(groups)), groups.items()):
    with col.container(border=True):
        st.caption(category.upper())
        st.markdown(f"#### {len(names)} programmes")
        shown = ", ".join(names[:3])
        extra = f" and {len(names) - 3} more" if len(names) > 3 else ""
        st.write(shown + extra)
        st.page_link("views/courses.py", label="View details", icon=":material/arrow_forward:")
