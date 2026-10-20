"""registration_ui.py - the registration screens (Streamlit only).

This file only collects answers and shows results. Every rule (validation, eligibility, saving,
status lookup) lives in registration_service.py, so the same rules can be reused later.

Screens:  form -> review -> done   (plus a separate "Check registration status" tab)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

import streamlit as st

import course_service
import registration_schema as schema
import registration_service as service
from data import DATA_NOTICE, format_inr
from eligibility import CHECK_MET, CHECK_UNMET, OUTCOME_MEETS, OUTCOME_NOT_MET
from registration_service import LookupRefused, RegistrationStorageError, SubmissionRefused

K = "f_"                                    # every form widget key starts with this
NOT_LISTED = course_service.NOT_LISTED
LOOKUP_REFUSED_MESSAGE = (
    "We could not verify those details. Check the reference number and the email address you registered with. "
    "After several wrong attempts you need to wait 15 minutes before trying again."
)

PRIVACY_NOTICE = """
**How this prototype uses your details**

- **Purpose:** your answers are used only to process your registration for the course you selected.
- **What is collected:** only the answers in this form. No Aadhaar, PAN, bank details, passwords or document uploads are collected.
- **Where they are stored:** in a database file on the computer or server that runs this website. They are not sent to other services.
- **Who can see them:** anyone with access to that server. This prototype has no admissions-officer login yet.
- **Checking your status:** you need your reference number and the same email address you registered with.
- **This is a prototype:** it has not had a security or legal review. Use test details unless the college has confirmed that this site is ready for real student data.
"""


# ---------------------------------------------------------------- state helpers
def _init_state() -> None:
    ss = st.session_state
    ss.setdefault("reg_step", "form")
    ss.setdefault("reg_token", uuid.uuid4().hex)
    ss.setdefault("reg_errors", {})


def _keep_form_state() -> None:
    """Streamlit forgets a widget's value when the widget is not drawn (for example on the review screen).
    Re-saving the value each run keeps what the student typed, so 'Back to edit' shows it again."""
    ss = st.session_state
    for key in [k for k in ss.keys() if isinstance(k, str) and k.startswith(K)]:
        ss[key] = ss[key]


def _clear_form_state() -> None:
    ss = st.session_state
    for key in [k for k in ss.keys() if isinstance(k, str) and (k.startswith(K) or k in (
            "reg_route", "reg_course_id", "reg_errors", "reg_review_error"))]:
        del ss[key]


def _collect() -> dict:
    ss = st.session_state
    data = {f: ss.get(K + f) for f in schema.ALL_FIELDS if f != "qualification_route"}
    data["qualification_route"] = ss.get("reg_route")
    return data


def _selected_course() -> dict | None:
    return course_service.get_course_by_name(st.session_state.get(K + "course_name"))


# -------------------------------------------------------------------- callbacks
def _on_course_change() -> None:
    """Keep the website-wide 'selected course' (shown at the top of the page) in step with the form."""
    st.session_state["selected_course"] = st.session_state.get(K + "course_name")
    st.session_state["reg_errors"] = {}


def _on_review() -> None:
    ss = st.session_state
    course = _selected_course()
    review = service.review_registration(course["id"] if course else None, _collect())
    ss["reg_errors"] = review["errors"]
    if not review["errors"]:
        ss["reg_course_id"] = course["id"]
        ss.pop(K + "eligibility_acknowledged", None)
        ss.pop("reg_review_error", None)
        ss["reg_step"] = "review"


def _on_back() -> None:
    st.session_state["reg_step"] = "form"
    st.session_state.pop("reg_review_error", None)


def _on_submit() -> None:
    ss = st.session_state
    try:
        result = service.submit_registration(
            ss.get("reg_course_id"), _collect(), ss["reg_token"], bool(ss.get(K + "eligibility_acknowledged")))
    except SubmissionRefused as exc:
        if set(exc.errors) == {"eligibility_acknowledged"}:
            ss["reg_review_error"] = exc.errors["eligibility_acknowledged"]
        else:
            ss["reg_errors"] = exc.errors
            ss["reg_step"] = "form"
        return
    except RegistrationStorageError:
        ss["reg_review_error"] = ("Your registration could not be saved, so nothing was submitted. "
                                  "Please try again in a moment.")
        return
    _clear_form_state()                       # do not keep personal details in the session after saving
    ss["reg_result"] = result
    ss["reg_step"] = "done"


def _start_over() -> None:
    _clear_form_state()
    st.session_state.pop("reg_result", None)
    st.session_state["reg_token"] = uuid.uuid4().hex
    st.session_state["reg_step"] = "form"


# ---------------------------------------------------------------- field helpers
def _err(field: str) -> None:
    message = st.session_state.get("reg_errors", {}).get(field)
    if message:
        st.caption(f":red[{message}]")


def _label(field: str) -> str:
    return schema.FIELD_SPECS[field]["label"]


def _help(field: str) -> str:
    return schema.FIELD_SPECS[field]["help"]


def _text(field: str, **kwargs) -> None:
    st.text_input(_label(field), key=K + field, help=_help(field), **kwargs)
    _err(field)


def _select(field: str, options: list, **kwargs) -> None:
    st.selectbox(_label(field), options, index=None, placeholder="Choose an option",
                 key=K + field, help=_help(field), **kwargs)
    _err(field)


def _percent(field: str) -> None:
    st.number_input(_label(field), min_value=0.0, max_value=100.0, value=None, step=0.1,
                    format="%.2f", key=K + field, help=_help(field))
    _err(field)


def _when(iso_text: str) -> str:
    try:
        return datetime.fromisoformat(iso_text).strftime("%d %b %Y, %H:%M UTC")
    except (TypeError, ValueError):
        return iso_text or NOT_LISTED


# ------------------------------------------------------------------ form screen
def _course_panel(summary: dict) -> None:
    c1, c2, c3, c4 = st.columns(4)
    years = summary["duration_years"]
    c1.metric("Duration", f"{years} years" if years else NOT_LISTED)
    annual, total = summary["annual_tuition"], summary["total_tuition"]
    c2.metric("Annual tuition", format_inr(annual) if annual is not None else NOT_LISTED,
              help="Illustrative prototype figure.")
    c3.metric("Total tuition", format_inr(total) if total is not None else NOT_LISTED,
              help="Annual tuition x duration. Hostel, transport, examination and other charges are excluded.")
    capacity = summary["seat_capacity"]
    c4.metric("Seat capacity", capacity if capacity is not None else NOT_LISTED,
              help="Illustrative intake target, not confirmed seats.")
    availability = summary["seat_availability"]
    st.caption(f"Seats available now: {availability}" if availability is not None
               else "Seat availability is not recorded, so this site cannot say whether seats are open.")

    st.write(f"**Level and category:** {summary['level'] or NOT_LISTED} · {summary['group'] or NOT_LISTED}")
    st.write(f"**Department:** {summary['department'] or NOT_LISTED}")
    if summary["class12_requirement"]:
        st.write(f"**Class 12 subjects:** {summary['class12_requirement']}")
    if summary["degree_requirement"]:
        st.write(f"**Bachelor's degree:** {summary['degree_requirement']}")
    if summary["minimum_percentage"] is not None:
        st.write(f"**Minimum marks (illustrative):** {summary['minimum_percentage']}%")
    st.write(f"**Diploma pathway:** {summary['diploma_pathway'] or 'No diploma pathway is listed for this course.'}")
    st.write(f"**Admission mode:** {summary['admission_mode'] or NOT_LISTED}")
    st.caption("Eligibility details are illustrative defaults. The college confirms the final requirements.")


def _basic_section() -> None:
    with st.container(border=True):
        st.subheader("2. Basic information", anchor=False)
        _text("full_name", max_chars=100)
        left, right = st.columns(2)
        with left:
            _text("email", max_chars=254, placeholder="name@example.com")
        with right:
            _text("mobile", max_chars=20, placeholder="98765 43210")
        d1, d2, d3 = st.columns(3)
        with d1:
            st.date_input(_label("date_of_birth"), value=None, min_value=date(1950, 1, 1),
                          max_value=date.today(), format="DD/MM/YYYY", key=K + "date_of_birth",
                          help=_help("date_of_birth"))
            _err("date_of_birth")
        with d2:
            _select("gender", schema.GENDERS)
        with d3:
            _select("state", schema.STATES)


def _academic_section(course: dict, summary: dict) -> None:
    ss = st.session_state
    routes = schema.qualification_routes(course)
    with st.container(border=True):
        st.subheader("3. Academic qualifications", anchor=False)
        if len(routes) > 1:
            if ss.get(K + "qualification_route") not in routes:
                ss.pop(K + "qualification_route", None)
            route = st.radio(_label("qualification_route"), routes, horizontal=True,
                             format_func=schema.ROUTE_LABELS.get, key=K + "qualification_route",
                             help=_help("qualification_route"))
        else:
            route = routes[0]
            ss.pop(K + "qualification_route", None)
            st.write(f"**Qualification:** {schema.ROUTE_LABELS[route]}")
        ss["reg_route"] = route
        _err("qualification_route")

        if route == schema.ROUTE_CLASS12:
            if summary["class12_requirement"]:
                st.info(f"Stored Class 12 subject requirement: {summary['class12_requirement']}", icon=":material/menu_book:")
            b1, b2 = st.columns(2)
            with b1:
                _select("class12_board", schema.BOARDS)
            with b2:
                _select("class12_stream", schema.STREAMS)
            st.multiselect(_label("class12_subjects"), schema.CLASS12_SUBJECTS, key=K + "class12_subjects",
                           help=_help("class12_subjects"), placeholder="Choose all that apply")
            _err("class12_subjects")
            _text("class12_other_subjects", max_chars=200)
            r1, r2, r3 = st.columns(3)
            with r1:
                st.radio(_label("class12_result_status"), [schema.RESULT_DECLARED, schema.RESULT_AWAITED],
                         horizontal=True, key=K + "class12_result_status", help=_help("class12_result_status"))
                _err("class12_result_status")
            awaited = ss.get(K + "class12_result_status") == schema.RESULT_AWAITED
            with r2:
                if awaited:
                    st.caption("A percentage is not needed while your result is awaited.")
                else:
                    _percent("class12_percentage")
            with r3:
                years = list(range(date.today().year + 1, date.today().year - 16, -1))
                _select("class12_year", years)
        elif route == schema.ROUTE_DIPLOMA:
            st.info(f"Stored diploma pathway: {summary['diploma_pathway']}", icon=":material/menu_book:")
            _text("diploma_branch", max_chars=100)
            p1, p2 = st.columns(2)
            with p1:
                _percent("diploma_percentage")
            with p2:
                _select("diploma_year", list(range(date.today().year + 1, date.today().year - 16, -1)))
        elif route == schema.ROUTE_DEGREE:
            if summary["degree_requirement"]:
                st.info(f"Stored degree requirement: {summary['degree_requirement']}", icon=":material/menu_book:")
            _text("degree_name", max_chars=100)
            _text("degree_discipline", max_chars=100)
            p1, p2 = st.columns(2)
            with p1:
                _percent("degree_percentage")
            with p2:
                _select("degree_year", list(range(date.today().year + 1, date.today().year - 16, -1)))

        if route != schema.ROUTE_DEGREE:
            _percent("class10_percentage")
        if summary["mentions_entrance_test"]:
            _text("entrance_exam_details", max_chars=200)


def _documents_section(summary: dict) -> None:
    with st.container(border=True):
        st.subheader("4. Documents", anchor=False)
        documents = summary["documents"]
        if documents:
            st.write("The course data lists these documents for this course:")
            st.markdown("\n".join(f"- {item}" for item in documents))
        else:
            st.warning("No document list is stored for this course. Ask the admissions office which documents are needed.")
        st.caption("This prototype does not collect or store documents. The college confirms the documents it needs "
                   "during the later admission requirements, so keep them ready.")


def _declaration_section() -> None:
    with st.container(border=True):
        st.subheader("5. Declaration and consent", anchor=False)
        st.markdown(PRIVACY_NOTICE)
        st.checkbox("I have read the privacy notice above.", key=K + "privacy_acknowledged")
        _err("privacy_acknowledged")
        st.checkbox("I have reviewed my answers and, to the best of my knowledge, they are accurate.",
                    key=K + "declaration_accurate")
        _err("declaration_accurate")


def _render_form() -> None:
    ss = st.session_state
    st.caption("Step 1 of 3: Fill in the form")
    st.info(DATA_NOTICE, icon=":material/info:")
    errors = ss.get("reg_errors", {})
    if errors:
        st.error(f"Please check the {len(errors)} item(s) marked in red below.", icon=":material/error:")

    names = [c["name"] for c in course_service.list_courses()]
    if ss.get(K + "course_name") not in names:
        ss.pop(K + "course_name", None)
        if ss.get("selected_course") in names:            # started from a course page, or the banner above
            ss[K + "course_name"] = ss["selected_course"]

    with st.container(border=True):
        st.subheader("1. Course selection", anchor=False)
        st.selectbox("Course", names, index=None, placeholder="Choose the course you want to register for",
                     key=K + "course_name", on_change=_on_course_change)
        _err("course_id")
        course = _selected_course()
        summary = course_service.course_summary(course["id"]) if course else None
        if summary:
            _course_panel(summary)
        else:
            st.caption("Choose a course to see its details and continue with the form.")

    if not course:
        return
    _basic_section()
    _academic_section(course, summary)
    _documents_section(summary)
    _declaration_section()
    st.button("Review registration", type="primary", on_click=_on_review, key="reg_review_button")
    st.caption("You can check everything on the next screen before anything is submitted.")


# ---------------------------------------------------------------- review screen
def _show_eligibility(result: dict) -> None:
    box = {OUTCOME_MEETS: st.success, OUTCOME_NOT_MET: st.warning}.get(result["outcome"], st.info)
    box(f"**{result['label']}**")
    icons = {CHECK_MET: ":material/check_circle:", CHECK_UNMET: ":material/cancel:"}
    for check in result["checks"]:
        icon = icons.get(check["status"], ":material/help:")
        st.markdown(f"- {icon} **{check['criterion']}:** {check['detail']}")
    for note in result["notes"]:
        st.caption(note)
    st.caption(result["disclaimer"])


def _row(label: str, value) -> None:
    if value in (None, "", []):
        value = "Not provided"
    st.write(f"**{label}:** {value}")


def _pct(value) -> str | None:
    return f"{value:g}%" if isinstance(value, (int, float)) else None


def _render_review() -> None:
    ss = st.session_state
    review = service.review_registration(ss.get("reg_course_id"), _collect())
    if review["errors"] or review["course"] is None:
        ss["reg_errors"] = review["errors"]
        ss["reg_step"] = "form"
        st.rerun()
    course, d, eligibility = review["course"], review["cleaned"], review["eligibility"]

    st.caption("Step 2 of 3: Review your registration")
    st.info("Nothing has been submitted yet. Check your answers, then confirm.", icon=":material/fact_check:")

    with st.container(border=True):
        st.subheader("Course", anchor=False)
        _row("Course", course["name"])
        _row("Department", course_service.department_for(course["id"]) or NOT_LISTED)
    with st.container(border=True):
        st.subheader("Basic information", anchor=False)
        _row("Full name", d["full_name"])
        _row("Email address", d["email"])
        mobile = d["mobile"]
        _row("Mobile number", f"{mobile[:3]} {mobile[3:8]} {mobile[8:]}" if mobile.startswith("+91") else mobile)
        _row("Date of birth", d["date_of_birth"])
        _row("Gender", d["gender"])
        _row("State or region", d["state"])
    with st.container(border=True):
        st.subheader("Academic qualifications", anchor=False)
        route = d["qualification_route"]
        _row("Applying with", schema.ROUTE_LABELS.get(route))
        if route == schema.ROUTE_CLASS12:
            _row("Class 12 board", d["class12_board"])
            _row("Class 12 stream", d["class12_stream"])
            _row("Subjects", ", ".join(d["class12_subjects"] + ([d["class12_other_subjects"]] if d["class12_other_subjects"] else [])))
            _row("Class 12 result", d["class12_result_status"])
            _row("Class 12 percentage", _pct(d["class12_percentage"]))
            _row("Year of passing", d["class12_year"])
        elif route == schema.ROUTE_DIPLOMA:
            _row("Diploma branch", d["diploma_branch"])
            _row("Diploma percentage", _pct(d["diploma_percentage"]))
            _row("Year of passing", d["diploma_year"])
        elif route == schema.ROUTE_DEGREE:
            _row("Degree", d["degree_name"])
            _row("Discipline", d["degree_discipline"])
            _row("Degree percentage", _pct(d["degree_percentage"]))
            _row("Year of passing", d["degree_year"])
        if route != schema.ROUTE_DEGREE:
            _row("Class 10 percentage", _pct(d["class10_percentage"]))
        if d["entrance_exam_details"]:
            _row("Entrance examination", d["entrance_exam_details"])

    with st.container(border=True):
        st.subheader("Eligibility check", anchor=False)
        _show_eligibility(eligibility)
        needs_ack = eligibility["outcome"] == OUTCOME_NOT_MET
        if needs_ack:
            st.checkbox("I understand that my answers do not meet the stored criteria, and that the college makes the final decision.",
                        key=K + "eligibility_acknowledged")

    message = ss.get("reg_review_error")
    if message:
        st.error(message, icon=":material/error:")
    st.caption("Submitting a registration does not mean admission has been granted.")
    back, confirm = st.columns(2)
    back.button("Back to edit", on_click=_on_back, width="stretch", key="reg_back_button")
    confirm.button("Confirm and submit registration", type="primary", on_click=_on_submit, width="stretch",
                   key="reg_submit_button",
                   disabled=needs_ack and not ss.get(K + "eligibility_acknowledged"))


# ------------------------------------------------------------- confirmation
def _render_done() -> None:
    result = st.session_state.get("reg_result")
    if not result:
        st.session_state["reg_step"] = "form"
        st.rerun()
    st.caption("Step 3 of 3: Submitted")
    if result.get("already_submitted"):
        st.success("This registration was already submitted. It was not saved twice.", icon=":material/check_circle:")
    else:
        st.success("Your registration has been submitted.", icon=":material/check_circle:")
    with st.container(border=True):
        st.write("**Registration reference number**")
        st.code(result["reference"], language=None)
        st.write(f"**Course:** {result['course_name']}")
        st.write(f"**Status:** {result['status']}")
        st.write(f"**Submitted:** {_when(result['submitted_at'])}")
        st.caption(schema.STATUS_MEANINGS.get(result["status"], ""))
    st.warning("Save your reference number now. This prototype does not send confirmation emails, and you need the "
               "reference number together with your registered email address to check your status.",
               icon=":material/bookmark:")
    st.info("Submitting a registration is not admission. The college reviews registrations and approves them through "
            "its own process. Approved students then continue with the remaining admission requirements.",
            icon=":material/info:")
    st.button("Register for another course", on_click=_start_over, key="reg_again_button")


# ------------------------------------------------------------- status lookup
def _render_status_lookup() -> None:
    st.write("Enter the reference number you received and the email address you registered with.")
    with st.form("reg_status_form", clear_on_submit=False):
        reference = st.text_input("Registration reference number", placeholder="REG-2026-AB12CD34", max_chars=30,
                                  key="reg_status_reference")
        email = st.text_input("Registered email address", max_chars=254, key="reg_status_email")
        submitted = st.form_submit_button("Check status", type="primary")
    if not submitted:
        return
    try:
        info = service.check_registration_status(reference, email)
    except LookupRefused:
        st.error(LOOKUP_REFUSED_MESSAGE, icon=":material/lock:")
        return
    except RegistrationStorageError:
        st.error("The registration records could not be read right now. Please try again later.")
        return
    with st.container(border=True):
        st.markdown(f"#### {info['course_name']}")
        st.write(f"**Reference:** {info['reference']}")
        st.write(f"**Registered name:** {info['applicant_name']}")
        st.write(f"**Status:** {info['status']}")
        st.caption(info["status_meaning"])
        st.write(f"**Submitted:** {_when(info['submitted_at'])}")
        st.write(f"**Last updated:** {_when(info['updated_at'])}")
        st.markdown("**Status history**")
        for entry in info["history"]:
            line = f"- {_when(entry['changed_at'])}: {entry['status']}"
            st.markdown(line + (f" ({entry['note']})" if entry["note"] else ""))
    st.caption("Status changes are made only through the college's review process. This prototype has no "
               "admissions-officer screen yet, so a new registration stays 'Submitted'.")


# ----------------------------------------------------------------- entry point
def render_registration_portal() -> None:
    """Draw the registration area. Called from views/admissions.py."""
    _init_state()
    _keep_form_state()
    register_tab, status_tab = st.tabs(["Register for a course", "Check registration status"])
    with register_tab:
        step = st.session_state["reg_step"]
        if step == "done":
            _render_done()
        elif step == "review":
            _render_review()
        else:
            _render_form()
    with status_tab:
        _render_status_lookup()
