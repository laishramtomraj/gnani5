import streamlit as st

import content_db
import faculty_db
from course_catalogue import GROUPS
from data import COURSES, DATA_NOTICE, format_inr

BY_ID = {c["id"]: c for c in COURSES}
ALL_GROUPS = list(GROUPS) + [g for g in dict.fromkeys(c["group"] for c in COURSES) if g not in GROUPS]
ALL = "All"
NOT_LISTED = "Not listed"


# ------------------------------------------------- departments and faculty
faculty_db.init_db()


@st.cache_data(show_spinner=False)
def _directory(stamp: float) -> dict:
    return faculty_db.load_directory()


directory = _directory(faculty_db.DB_PATH.stat().st_mtime)


# ---------------------------------------------------------------- helpers
def _open(course_id: str) -> None:
    st.query_params["course"] = course_id


def _close() -> None:
    st.query_params.clear()


def bullets(items: list[str] | None) -> None:
    if items:
        st.markdown("\n".join(f"- {i}" for i in items))
    else:
        st.caption(NOT_LISTED)


def register(course: dict, key: str, **kwargs) -> None:
    if st.button(key=key, **kwargs):
        st.session_state["selected_course"] = course["name"]      # carried into the registration form
        st.switch_page("views/admissions.py")


# ------------------------------------------------------------ course card
def card(c: dict) -> None:
    with st.container(border=True):
        st.caption(f"{c['group']} · {c['level']}".upper())
        st.markdown(f"#### {c['name']}")
        st.write(f"**Duration:** {c['years']} years")
        st.write(f"**Annual tuition (sample):** {format_inr(c['tuition'])}")
        st.write(f"**Sample seats:** {c['seats']}")
        b1, b2 = st.columns(2)
        b1.button("View details", key=f"detail_{c['id']}", on_click=_open, args=(c["id"],), width="stretch")
        with b2:
            register(c, f"reg_{c['id']}", label="Register", type="primary", width="stretch")


def grid(items: list[dict]) -> None:
    for i in range(0, len(items), 3):
        for col, c in zip(st.columns(3), items[i:i + 3]):
            with col:
                card(c)


# ------------------------------------------------------------ list view
def catalogue() -> None:
    st.title("Courses", anchor=False)
    if content_db.text("show_prototype_notice"):
        st.info(DATA_NOTICE, icon=":material/info:")

    f1, f2 = st.columns([3, 1])
    query = f1.text_input("Search", placeholder="e.g. Physics, Computer, MBA")
    level = f2.selectbox("Level", [ALL, "Undergraduate", "Postgraduate"])
    choice = st.pills("Category", [ALL] + ALL_GROUPS, selection_mode="single", default=ALL) or ALL

    results = [
        c for c in COURSES
        if (level == ALL or c["level"] == level)
        and (choice == ALL or c["group"] == choice)
        and query.lower().strip() in c["name"].lower()
    ]
    st.caption(f"{len(results)} programme(s) shown")

    cards_tab, table_tab = st.tabs(["Cards", "Compare table"])
    with cards_tab:
        if not results:
            st.warning("No programmes match your filters.")
        for group in ALL_GROUPS:
            items = [c for c in results if c["group"] == group]
            if items:
                st.subheader(f"{group} ({len(items)})", anchor=False)
                grid(items)
    with table_tab:
        st.dataframe(
            [
                {
                    "Course": c["name"],
                    "Category": c["group"],
                    "Level": c["level"],
                    "Duration": f"{c['years']} years",
                    "Annual tuition (sample)": format_inr(c["tuition"]),
                    "Total tuition (sample)": format_inr(c["tuition"] * c["years"]),
                    "Sample seats": c["seats"],
                }
                for c in results
            ],
            hide_index=True,
            width="stretch",
        )
    st.caption("Open a course with 'View details' to see eligibility, admission steps, careers and faculty.")


# ---------------------------------------------------------- detail view
def detail(c: dict) -> None:
    st.button("All courses", icon=":material/arrow_back:", on_click=_close, key="back_to_courses")
    st.title(c["name"], anchor=False)
    st.caption(f"{c['group']} · {c['level']} · Illustrative prototype data")
    if content_db.text("show_prototype_notice"):
        st.info(DATA_NOTICE, icon=":material/info:")

    total = c["tuition"] * c["years"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Duration", f"{c['years']} years")
    m2.metric("Annual tuition", format_inr(c["tuition"]), help="Illustrative prototype figure.")
    m3.metric("Total tuition", format_inr(total), help="Annual tuition × duration. Illustrative, not a guaranteed final cost.")
    m4.metric("Seats", c["seats"], help="Illustrative intake target, not confirmed seats or live availability.")
    st.caption(
        "Total tuition = annual tuition × duration. Hostel, transport, examination, registration and "
        "other charges are excluded, and fee increases may apply."
    )
    register(c, "detail_register", label="Register for This Course", type="primary")

    overview, eligibility, careers, department = st.tabs(
        ["Overview", "Eligibility & admission", "Careers & higher study", "Department & faculty"]
    )

    with overview:
        st.write(c["overview"])
        if c.get("specialisations"):
            st.markdown("**Specialisations**")
            bullets(c["specialisations"])
        st.markdown("**Major subjects**")
        bullets(c["subjects"])
        st.markdown("**Duration and semester structure**")
        st.write(f"{c['years']} years · {c['years'] * 2} semesters (two per year).")
        st.write(c["semesters"])

    with eligibility:
        if c["class12"]:
            st.write(f"**Class 12 subjects:** {c['class12']}")
        if c["degree"]:
            st.write(f"**Bachelor's degree:** {c['degree']}")
        st.write(f"**Minimum marks (illustrative):** {c['min_pct']}%")
        st.write(f"**Diploma pathway:** {c['diploma'] or 'No diploma pathway is listed for this course.'}")
        st.write(f"**Admission mode:** {c['admission_mode']}")
        st.markdown("**Admission procedure**")
        st.markdown("\n".join(f"{n}. {step}" for n, step in enumerate(c["procedure"], start=1)))
        st.markdown("**Required documents**")
        bullets(c["documents"])
        st.caption(
            "Eligibility, procedure and documents are illustrative defaults. The college confirms the "
            "final requirements, and registration approval and admission are decided only by the college."
        )

    with careers:
        st.markdown("**Career opportunities**")
        bullets(c["careers"])
        st.markdown("**Higher-study options**")
        bullets(c["higher_studies"])

    with department:
        dept = next((d for d in directory["departments"] if c["id"] in d["course_ids"]), None)
        if dept is None:
            st.warning("This course is not linked to a department yet.")
        else:
            st.write(f"**Department:** {dept['name']}")
            others = [n for n in dept["courses"] if n != c["name"]]
            if others:
                st.write("**Other programmes in this department:** " + ", ".join(others))
            st.markdown("**Related faculty**")
            members = [f for f in directory["faculty"] if f["department"] == dept["name"]]
            if not members:
                st.caption("No faculty listed for this department yet.")
            for f in members:
                with st.container(border=True):
                    st.markdown(f"**{f['name']}**")
                    st.caption(f["designation"] + (f" · {f['post']}" if f["post"] else ""))
                    st.write(f"Specialization: {f['specialization'] or NOT_LISTED}")
                    st.write(f"Subjects: {', '.join(f['subjects']) or NOT_LISTED}")
            st.page_link("views/faculty.py", label="Open the faculty directory", icon=":material/groups:")
            st.caption("Faculty profiles are fictional sample data for this prototype.")


# ------------------------------------------------------------------ page
course_id = st.query_params.get("course")
selected = BY_ID.get(course_id) if course_id else None

if selected:
    detail(selected)
else:
    if course_id:
        st.warning("That course was not found, so all courses are shown.")
    catalogue()
