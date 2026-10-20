import streamlit as st

from components import section_header
from data import ACHIEVEMENTS, COURSES, DATA_IS_SAMPLE, ILLUSTRATIVE_ACHIEVEMENTS
from hero import render_hero

# ------------------------------------------------------------------ HERO
render_hero()

st.write("")

# --------------------------------------------------------------- PILLARS
section_header("Why us", "Education That Prepares You for What's Next")
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
section_header(
    "Highlights",
    "Our Achievements",
    "A snapshot of academic, research, industry and student-life accomplishments. "
    "The figures below are illustrative prototype data and can be replaced with verified college information.",
)

achievements = ACHIEVEMENTS or ILLUSTRATIVE_ACHIEVEMENTS

for row_start in range(0, len(achievements), 3):
    row = achievements[row_start:row_start + 3]
    for col, item in zip(st.columns(3), row):
        with col.container(border=True):
            st.markdown(f"#### {item['icon']} {item['title']}")
            st.metric(item["title"], item["value"], label_visibility="collapsed")
            st.write(item["description"])

if not ACHIEVEMENTS:
    st.caption(
        "Illustrative prototype data only. Add verified achievements to "
        "`ACHIEVEMENTS` in `data.py` before publishing."
    )
st.write("")

# --------------------------------------------------------- COURSE PREVIEW
section_header("Programmes", "Explore Courses")
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
if DATA_IS_SAMPLE:
    st.caption("Programme list is illustrative sample data, not a claim about a real college.")

st.write("")

# ------------------------------------------------------------ REGISTER CTA
with st.container(border=True):
    left, right = st.columns([3, 1], vertical_alignment="center")
    with left:
        st.subheader("Ready to Begin?", anchor=False)
        st.write(
            "Choose a course, complete the registration form, and the admissions "
            "team will review your application."
        )
    with right:
        if st.button("Begin Registration", type="primary", width="stretch", key="cta_register"):
            st.switch_page("views/admissions.py")