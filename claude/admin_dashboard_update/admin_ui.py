"""admin_ui.py - the private administrator dashboard (Streamlit).

Reached at  /?admin  (Streamlit has no separate login route). It never draws the public header, footer or
navigation. Every action goes through admin_service, which checks the session on the server for each call.
"""
from __future__ import annotations

import sqlite3

import streamlit as st

import admin_auth as auth
import admin_service as svc
import catalogue_db as cat
import content_db as content
import faculty_db as fdb
from course_catalogue import GROUPS
from data import COLLEGE, format_inr

SECTIONS = ["Dashboard Overview", "College Information", "Courses and Specialisations", "Fees and Eligibility", "Faculty",
            "College Achievements", "Contact Information", "Registration and Admission Enquiries", "Website Content",
            "Account and Security"]
NEW = "New"
SUBJECT_LABEL = lambda s: s.title()


# ================================================================ helpers
def flash(kind: str, message: str) -> None:
    st.session_state.setdefault("admin_flash", []).append((kind, message))


def show_flash() -> None:
    for kind, message in st.session_state.pop("admin_flash", []):
        getattr(st, kind)(message, icon={"success": ":material/check_circle:", "error": ":material/error:",
                                         "warning": ":material/warning:", "info": ":material/info:"}[kind])


def call(fn, *args, label: str = "Saving...", **kwargs):
    """Run an operation with a loading indicator and friendly errors -> (succeeded, result)."""
    try:
        with st.spinner(label):
            return True, fn(*args, **kwargs)
    except svc.ValidationError as error:
        for message in error.errors.values():
            st.error(message, icon=":material/error:")
    except PermissionError:
        st.session_state.pop("admin_token", None)
        flash("warning", "Your session has ended. Please sign in again.")
        st.rerun()
    except sqlite3.Error:
        st.error("The change could not be saved because the database is busy or unavailable. "
                 "Nothing was lost; please try again in a moment.", icon=":material/error:")
    except ValueError as error:
        st.error(str(error), icon=":material/error:")
    return False, None


def nonce(name: str) -> int:
    return st.session_state.setdefault(f"nonce_{name}", 0)


def bump(name: str) -> None:
    st.session_state[f"nonce_{name}"] = nonce(name) + 1


def pick_with_next(key: str) -> None:
    """Apply a pending selection (set by a save) before the select box is created."""
    pending = st.session_state.pop(f"{key}_next", None)
    if pending is not None:
        st.session_state[key] = pending


def money(value: int) -> str:
    return format_inr(value) if value else "-"


def choice_with_new(label: str, existing: list[str], current: str, key: str) -> str:
    """A select box of existing values plus an optional box for a new one (forms cannot show boxes conditionally)."""
    options = list(dict.fromkeys(([current] if current else []) + existing))
    chosen = st.selectbox(label, options, index=options.index(current) if current in options else 0, key=f"{key}_sel")
    new_value = st.text_input(f"...or type a new {label.lower()}", key=f"{key}_new")
    return new_value.strip() or chosen


# ============================================================ login / shell
def login_view() -> None:
    st.title(f":material/admin_panel_settings: {COLLEGE.get('name') or 'College'} administration")
    show_flash()
    with st.form("admin_login"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary")
    if submitted:
        token = auth.login(email, password)
        if token:
            st.session_state["admin_token"] = token
            st.session_state["admin_section"] = SECTIONS[0]
            st.rerun()
        st.error("Invalid email or password, or the account is temporarily locked.", icon=":material/error:")
    st.caption("Authorised staff only. Sessions end after a period of inactivity.")
    if auth.admin_count() == 0:
        st.info("No administrator account exists yet. Create the first one on the server with `python create_admin.py`.",
                icon=":material/info:")


def shell(user: auth.AdminUser, token: str) -> None:
    with st.sidebar:
        st.markdown(f"### :material/admin_panel_settings: {COLLEGE.get('name') or 'College'}")
        st.caption(f"Signed in as {user.email}")
        st.radio("Admin sections", SECTIONS, key="admin_section", label_visibility="collapsed")
        st.divider()
        st.link_button("View public site", "/", icon=":material/open_in_new:", width="stretch")
        if st.button("Logout", icon=":material/logout:", width="stretch", key="admin_logout"):
            auth.logout(token)
            for key in [k for k in st.session_state if k.startswith(("admin", "nonce_", "course_", "faculty_", "ach_", "enq_"))]:
                st.session_state.pop(key, None)
            flash("success", "You have been signed out.")
            st.rerun()
    show_flash()
    SECTION_FUNCTIONS[st.session_state["admin_section"]](token)


def run() -> None:
    token = st.session_state.get("admin_token")
    user = auth.validate(token) if token else None
    if user is None:
        if token:                                                  # a session existed but is no longer valid
            flash("warning", "Your session has ended. Please sign in again.")
        st.session_state.pop("admin_token", None)
        login_view()
    else:
        shell(user, token)


# ============================================================== dashboard
def dashboard_section(token: str) -> None:
    st.title("Dashboard", anchor=False)
    ok, d = call(svc.dashboard, token, label="Loading...")
    if not ok:
        return
    cols = st.columns(4)
    cols[0].metric("Courses", d["courses_total"], f"{d['courses_published']} published", delta_color="off", delta_arrow="off")
    cols[1].metric("Faculty", d["faculty_total"], f"{d['faculty_published']} published", delta_color="off", delta_arrow="off")
    cols[2].metric("Achievements", d["achievements_total"], f"{d['achievements_published']} published", delta_color="off", delta_arrow="off")
    cols[3].metric("Enquiries", d["enquiries"]["total"], f"{d['enquiries']['new']} new", delta_color="off", delta_arrow="off")
    if d["drafts"]:
        st.warning(f"{d['drafts']} content setting(s) have unpublished draft changes.", icon=":material/edit_note:")
    if d["unlinked_courses"]:
        st.warning("These courses are not linked to a department yet, so they show no faculty: "
                   + ", ".join(d["unlinked_courses"]), icon=":material/link_off:")
    if d["course_problems"]:
        st.error("Some course records have unusable values and are hidden from the site: " + ", ".join(d["course_problems"]))
    if d["enquiries"]["total"] == 0:
        st.info("No enquiries or registrations have been recorded. The public site does not yet have a form that saves "
                "submissions; see 'Registration and Admission Enquiries'.", icon=":material/inbox:")
    st.subheader("Recent administrator activity", anchor=False)
    ok, rows = call(auth.recent_audit, token, 8, label="Loading...")
    if ok:
        st.dataframe([{"When (UTC)": r["ts"].replace("T", " ")[:19], "Who": r["actor"], "Action": r["action"].replace("_", " "),
                       "Item": r["detail"] or r["entity_id"]} for r in rows], hide_index=True, width="stretch")


# ===================================================== draft / publish forms
def _preview_college(v: dict) -> None:
    with st.container(border=True):
        st.markdown(f"### :material/account_balance: {v['name']}")
        if v.get("description"):
            st.write(v["description"])
        left, right = st.columns(2)
        if v.get("vision"):
            left.markdown("**Vision**")
            left.write(v["vision"])
        if v.get("mission"):
            right.markdown("**Mission**")
            right.write(v["mission"])
        for label, key in (("Address", "address"), ("Phone", "phone"), ("Email", "email"), ("Office hours", "office_hours")):
            st.caption(f"{label}: {v.get(key) or 'To be added'}")


def _preview_contact(v: dict) -> None:
    items = [("Address", "address"), ("General enquiries", "phone"), ("Admissions helpline", "admissions_phone"),
             ("General email", "email"), ("Admissions email", "admissions_email"), ("Office hours", "office_hours")]
    for col, (label, key) in zip(st.columns(3), items[:3]):
        with col.container(border=True):
            st.markdown(f"**{label}**")
            st.write(v.get(key) or "To be added")
    for col, (label, key) in zip(st.columns(3), items[3:]):
        with col.container(border=True):
            st.markdown(f"**{label}**")
            st.write(v.get(key) or "To be added")
    links = [(n, v[k]) for n, k in (("Facebook", "facebook"), ("Instagram", "instagram"), ("LinkedIn", "linkedin"),
                                    ("YouTube", "youtube"), ("X", "x_twitter")) if v.get(k)]
    if links:
        st.markdown(" · ".join(f"[{n}]({u})" for n, u in links))


def _preview_website(v: dict) -> None:
    with st.container(border=True):
        st.title(v["home_headline"], anchor=False)
        st.write(v["home_intro"])
        st.markdown(f"**{v['home_why_heading']}**")
        st.markdown(f"**{v['home_achievements_heading']}**")
        st.markdown(f"**{v['home_programmes_heading']}**")
        if v.get("accreditations_text"):
            st.caption("About Us, accreditations: " + v["accreditations_text"])
        st.caption("Prototype-data notices are " + ("shown." if v["show_prototype_notice"] else "hidden."))


def content_form(token: str, name: str, title: str, keys: list[str], preview, intro: str = "") -> None:
    st.title(title, anchor=False)
    if intro:
        st.caption(intro)
    ok, data = call(svc.get_form, token, keys, label="Loading...")
    if not ok:
        return
    if data["has_draft"]:
        st.warning("You have unpublished draft changes. Visitors still see the published version.", icon=":material/edit_note:")
    suffix = f"{name}_{nonce(name)}"
    with st.form(f"form_{suffix}"):
        inputs: dict = {}
        for key in keys:
            field, value = content.FIELDS[key], data["values"][key]
            widget_key = f"{key}_{suffix}"
            if field.kind == "bool":
                inputs[key] = st.checkbox(field.label, value=bool(value), help=field.help or None, key=widget_key)
            elif field.kind == "area":
                inputs[key] = st.text_area(field.label, value=value, max_chars=field.max_len, help=field.help or None,
                                           height=110, key=widget_key)
            else:
                inputs[key] = st.text_input(field.label, value=value, max_chars=field.max_len, help=field.help or None, key=widget_key)
        c1, c2, c3 = st.columns(3)
        draft = c1.form_submit_button("Save draft", width="stretch")
        publish = c2.form_submit_button("Save and publish", type="primary", width="stretch")
        cancel = c3.form_submit_button("Cancel (undo edits)", width="stretch")
    if cancel:
        bump(name)
        st.rerun()
    if draft or publish:
        ok, _ = call(svc.save_content_draft, token, inputs)
        if ok and publish:
            ok, _ = call(svc.publish_content, token, keys, label="Publishing...")
        if ok:
            flash("success", "Published. The public site now shows these changes." if publish
                  else "Draft saved. It is not visible to visitors until you publish it.")
            bump(name)
            st.rerun()
    if data["has_draft"] and st.button("Discard unpublished draft", key=f"discard_{suffix}", icon=":material/undo:"):
        ok, _ = call(svc.discard_content_draft, token, keys)
        if ok:
            flash("success", "The draft was discarded.")
            bump(name)
            st.rerun()
    with st.expander("Preview (shows the draft if there is one)", expanded=False):
        preview(data["values"])


def college_section(token: str) -> None:
    content_form(token, "college", "College information", content.FORM_COLLEGE, _preview_college,
                 "Address, phones, emails and office hours here are the same fields as in Contact Information.")


def contact_section(token: str) -> None:
    content_form(token, "contact", "Contact information", content.FORM_CONTACT, _preview_contact,
                 "These details appear on the Contact page and in the site footer.")


def website_section(token: str) -> None:
    content_form(token, "website", "Website content", content.FORM_WEBSITE, _preview_website,
                 "Homepage headline and introduction, section headings and About Us text.")


# ================================================================ courses
def _course_table(courses: list[dict]) -> None:
    st.dataframe([{"ID": c["id"], "Course": c["name"], "Group": c["group"], "Level": c["level"], "Years": c["years"],
                   "Annual fee": money(c["tuition"]), "Seats": str(c["seats"]) if c["seats"] else "-", "Department": c["department"] or "(none)",
                   "Status": "Published" if c["published"] else "Draft"} for c in courses], hide_index=True, width="stretch")


def courses_section(token: str) -> None:
    st.title("Courses and specialisations", anchor=False)
    ok, courses = call(svc.list_courses, token, label="Loading...")
    if not ok:
        return
    f1, f2 = st.columns([3, 1])
    q = f1.text_input("Search by name or id", key="course_q").strip().lower()
    status = f2.selectbox("Status", ["All", "Published", "Draft"], key="course_status")
    shown = [c for c in courses if (not q or q in c["name"].lower() or q in c["id"])
             and (status == "All" or (c["published"] == (status == "Published")))]
    _course_table(shown)
    if not shown:
        st.info("No courses match your search.")
    labels = {f"{c['name']} ({c['id']})": c["id"] for c in courses}
    pick_with_next("course_pick")
    label = st.selectbox("Choose a course to edit, or add a new one", [NEW] + list(labels), key="course_pick")
    current = next((c for c in courses if c["id"] == labels.get(label)), None)
    cid = current["id"] if current else NEW
    suffix = f"{cid}_{nonce('course')}"
    st.subheader(f"Edit: {current['name']}" if current else "Add a new course", anchor=False)
    if current:
        st.caption(f"Status: {'Published' if current['published'] else 'Draft (not visible to visitors)'} · "
                   f"Fees and eligibility are managed under 'Fees and Eligibility'.")

    categories = sorted({c["category"] for c in courses} | {"Engineering", "Science", "Computing", "Management & Commerce"})
    groups = list(dict.fromkeys(list(GROUPS) + [c["group"] for c in courses]))
    departments = [""] + fdb.department_names()
    get = lambda k, d="": (current[k] if current else d)
    with st.form(f"course_form_{suffix}"):
        name = st.text_input("Course name *", value=get("name"), max_chars=150, key=f"cn_{suffix}")
        category = choice_with_new("Category", categories, get("category", "Science"), f"cat_{suffix}")
        group = choice_with_new("Programme group", groups, get("group", "Other programmes"), f"grp_{suffix}")
        c1, c2 = st.columns(2)
        level = c1.selectbox("Degree level *", svc.LEVELS, index=svc.LEVELS.index(get("level", "Undergraduate")), key=f"lv_{suffix}")
        years = c2.number_input("Duration (years) *", min_value=1, max_value=8, step=1, value=int(get("years", 3)), key=f"yr_{suffix}")
        department = st.selectbox("Department", departments, index=departments.index(fdb.department_of_course(cid) or "") if current else 0,
                                  format_func=lambda d: d or "(none yet)", key=f"dp_{suffix}")
        specialisations = st.text_area("Specialisations (one per line)", value="\n".join(get("specialisations", [])), height=90, key=f"sp_{suffix}")
        overview = st.text_area("Description", value=get("overview"), max_chars=2000, height=110, key=f"ov_{suffix}")
        with st.expander("Additional course information"):
            subjects = st.text_area("Major subjects (one per line)", value="\n".join(get("subjects", [])), height=90, key=f"su_{suffix}")
            careers = st.text_area("Career opportunities (one per line)", value="\n".join(get("careers", [])), height=90, key=f"ca_{suffix}")
            higher = st.text_area("Higher-study options (one per line)", value="\n".join(get("higher_studies", [])), height=90, key=f"hi_{suffix}")
            documents = st.text_area("Required documents (one per line)", value="\n".join(get("documents", [])), height=90, key=f"do_{suffix}")
        is_sample = st.checkbox("This course's details are illustrative sample data", value=bool(get("is_sample", False)), key=f"sm_{suffix}")
        published = bool(current and current["published"])
        b1, b2, b3 = st.columns(3)
        first = b1.form_submit_button("Save changes" if published else "Save draft", width="stretch")
        second = b2.form_submit_button("Save and unpublish" if published else "Save and publish", type="primary", width="stretch")
        cancel = b3.form_submit_button("Cancel (undo edits)", width="stretch")
    if cancel:
        bump("course")
        st.rerun()
    if first or second:
        form = dict(name=name, category=category, group=group, level=level, years=years, department=department,
                    specialisations=specialisations, overview=overview, subjects=subjects, careers=careers,
                    higher_studies=higher, documents=documents, is_sample=is_sample)
        status_value = ("keep" if first else "draft") if published else ("draft" if first else "publish")
        ok, new_id = call(svc.save_course, token, form, current["id"] if current else None, status_value)
        if ok:
            flash("success", f"Saved '{name}'." + ("" if (published and first) or second and not published else " It is saved as a draft."))
            st.session_state["course_pick_next"] = next((k for k, v in {f"{name} ({new_id})": new_id}.items()), NEW)
            bump("course")
            st.rerun()
    if current:
        c1, c2 = st.columns(2)
        if c1.button("Unpublish this course" if current["published"] else "Publish this course", key=f"cpub_{suffix}",
                     icon=":material/visibility_off:" if current["published"] else ":material/visibility:", width="stretch"):
            ok, _ = call(svc.set_course_published, token, current["id"], not current["published"])
            if ok:
                flash("success", "Unpublished." if current["published"] else "Published. Visitors can now see this course.")
                st.rerun()
        with st.expander("Delete this course permanently"):
            st.warning("This removes the course and its department link for good and cannot be undone. "
                       "Consider unpublishing instead, which hides it but keeps the details.", icon=":material/warning:")
            confirm = st.text_input(f"Type the course id ({current['id']}) to confirm", key=f"cdel_{suffix}")
            if st.button("Delete permanently", key=f"cdelbtn_{suffix}", type="primary", disabled=confirm.strip() != current["id"],
                         icon=":material/delete:"):
                ok, _ = call(svc.delete_course, token, current["id"], confirm)
                if ok:
                    flash("success", f"Deleted '{current['name']}'.")
                    st.session_state["course_pick_next"] = NEW
                    bump("course")
                    st.rerun()


# ======================================================== fees & eligibility
def fees_section(token: str) -> None:
    st.title("Fees and eligibility", anchor=False)
    ok, courses = call(svc.list_courses, token, label="Loading...")
    if not ok:
        return
    labels = {f"{c['name']} ({c['id']})": c["id"] for c in courses}
    label = st.selectbox("Course", list(labels), key="fees_pick")
    c = next(x for x in courses if x["id"] == labels[label])
    suffix = f"{c['id']}_{nonce('fees')}"
    pg = c["level"] == "Postgraduate"
    rule = c.get("req12") or {}
    st.caption(f"{c['level']} · {c['years']} years · {'Published' if c['published'] else 'Draft'}")
    with st.form(f"fees_form_{suffix}"):
        f1, f2, f3 = st.columns(3)
        tuition = f1.number_input("Annual tuition fee (₹) *", min_value=0, max_value=10_000_000, step=1000, value=int(c["tuition"]), key=f"tu_{suffix}")
        seats = f2.number_input("Seat capacity *", min_value=0, max_value=100_000, step=1, value=int(c["seats"]), key=f"se_{suffix}")
        min_pct = f3.number_input("Minimum marks (%)", min_value=0, max_value=100, step=1, value=int(c["min_pct"]), key=f"mp_{suffix}")
        st.caption(f"Total tuition for {c['years']} years: {format_inr(int(tuition) * c['years'])} (annual fee x duration; "
                   "hostel, transport, examination and other charges are not included).")
        class12 = st.text_input("Class 12 requirement (as shown to students)", value=c["class12"] or "", max_chars=300, key=f"c12_{suffix}", disabled=pg)
        degree = st.text_input("Bachelor's degree requirement (postgraduate courses)", value=c["degree"] or "", max_chars=300, key=f"deg_{suffix}", disabled=not pg)
        diploma = st.text_area("Diploma pathway / lateral entry", value=c["diploma"] or "", max_chars=500, height=70, key=f"dip_{suffix}")
        mode = st.text_input("Admission mode", value=c["admission_mode"] or "", max_chars=300, key=f"am_{suffix}")
        st.markdown("**Required Class 12 subjects** (used by the assistant's eligibility check)")
        any_stream = st.checkbox("Any Class 12 stream is accepted", value=bool(rule.get("any_stream")), key=f"as_{suffix}", disabled=pg)
        required = st.multiselect("All of these subjects are required", svc.SUBJECTS, default=rule.get("all", []), format_func=SUBJECT_LABEL,
                                  key=f"ra_{suffix}", disabled=pg)
        one_of = st.multiselect("At least one of these subjects is required", svc.SUBJECTS,
                                default=(rule.get("one_of") or [[]])[0], format_func=SUBJECT_LABEL, key=f"oo_{suffix}", disabled=pg)
        note = st.text_input("...or a note if the subject requirement is not fixed yet", value=rule.get("unverified", ""), max_chars=300,
                             key=f"un_{suffix}", disabled=pg)
        if pg:
            st.caption("Postgraduate courses use the bachelor's-degree requirement instead of Class 12 subjects.")
        b1, b2 = st.columns(2)
        save = b1.form_submit_button("Save fees and eligibility", type="primary", width="stretch")
        cancel = b2.form_submit_button("Cancel (undo edits)", width="stretch")
    if cancel:
        bump("fees")
        st.rerun()
    if save:
        terms = dict(tuition=tuition, seats=seats, min_pct=min_pct, class12=class12, degree=degree, diploma=diploma,
                     admission_mode=mode, any_stream=any_stream, required_all=required, one_of=one_of, unverified_note=note)
        ok, _ = call(svc.save_course_terms, token, c["id"], terms)
        if ok:
            flash("success", f"Saved fees and eligibility for '{c['name']}'." + ("" if c["published"] else " It is still a draft."))
            bump("fees")
            st.rerun()
    st.caption("Fees are stored as one annual amount per course; semester-wise fees are not part of the current data.")


# ================================================================= faculty
def faculty_section(token: str) -> None:
    st.title("Faculty", anchor=False)
    ok, data = call(svc.list_faculty, token, label="Loading...")
    if not ok:
        return
    people, departments = data["faculty"], data["departments"]
    st.dataframe([{"Name": f["name"], "Designation": f["designation"], "Post": f["post"] or "", "Department": f["department"],
                   "Status": "Published" if f["published"] else "Draft"} for f in people], hide_index=True, width="stretch")
    labels = {f"{f['name']} - {f['department']} (#{f['id']})": f["id"] for f in people}
    pick_with_next("faculty_pick")
    label = st.selectbox("Choose a profile to edit, or add a new one", [NEW] + list(labels), key="faculty_pick")
    current = next((f for f in people if f["id"] == labels.get(label)), None)
    suffix = f"{current['id'] if current else NEW}_{nonce('faculty')}"
    st.subheader(f"Edit: {current['name']}" if current else "Add a faculty profile", anchor=False)
    get = lambda k, d="": (current[k] if current and current[k] is not None else d)
    designations = list(dict.fromkeys(list(svc.DESIGNATIONS) + ([current["designation"]] if current else [])))
    with st.form(f"faculty_form_{suffix}"):
        name = st.text_input("Full name *", value=get("name"), max_chars=120, key=f"fn_{suffix}")
        c1, c2 = st.columns(2)
        designation = c1.selectbox("Designation *", designations, index=designations.index(get("designation", designations[0])), key=f"fd_{suffix}")
        other_designation = c2.text_input("...or another designation", key=f"fo_{suffix}")
        department = st.selectbox("Department *", departments, index=departments.index(get("department", departments[0])), key=f"fp_{suffix}")
        post = st.text_input("Administrative post (HOD, Dean, Director...)", value=get("post"), max_chars=80, key=f"fq_{suffix}")
        qualifications = st.text_input("Qualifications", value=get("qualifications"), max_chars=200, key=f"fl_{suffix}")
        e1, e2 = st.columns(2)
        teaching = e1.number_input("Years of teaching", min_value=0, max_value=60, step=1, value=int(get("teaching_years", 0) or 0), key=f"ft_{suffix}")
        industry = e2.number_input("Years of industry experience", min_value=0, max_value=60, step=1, value=int(get("industry_years", 0) or 0), key=f"fi_{suffix}")
        specialization = st.text_input("Specialization", value=get("specialization"), max_chars=120, key=f"fs_{suffix}")
        subjects = st.text_area("Subjects taught (one per line)", value="\n".join(get("subjects", [])), height=90, key=f"fu_{suffix}")
        interests = st.text_input("Research interests", value=get("research_interests"), max_chars=300, key=f"fr_{suffix}")
        description = st.text_area("Profile description", value=get("description"), max_chars=1500, height=110, key=f"fx_{suffix}")
        with st.expander("Official contact details (shown on the public profile)"):
            email = st.text_input("Official institutional email", value=get("email"), max_chars=120, key=f"fe_{suffix}")
            phone = st.text_input("Phone", value=get("phone"), max_chars=30, key=f"fh_{suffix}")
            office = st.text_input("Office location", value=get("office"), max_chars=120, key=f"fo2_{suffix}")
            hours = st.text_input("Consultation hours", value=get("consultation_hours"), max_chars=120, key=f"fc_{suffix}")
        photo = st.file_uploader("Profile photo (JPG, PNG or WebP, up to 2 MB)", type=["jpg", "jpeg", "png", "webp"], key=f"fph_{suffix}")
        is_sample = st.checkbox("This profile is illustrative sample data", value=bool(get("is_sample", False)), key=f"fsm_{suffix}")
        published = bool(current and current["published"])
        b1, b2, b3 = st.columns(3)
        first = b1.form_submit_button("Save changes" if published else "Save draft", width="stretch")
        second = b2.form_submit_button("Save and unpublish" if published else "Save and publish", type="primary", width="stretch")
        cancel = b3.form_submit_button("Cancel (undo edits)", width="stretch")
    if cancel:
        bump("faculty")
        st.rerun()
    if first or second:
        form = dict(name=name, designation=other_designation.strip() or designation, department=department, post=post,
                    qualifications=qualifications, teaching_years=teaching, industry_years=industry, specialization=specialization,
                    subjects=subjects, research_interests=interests, description=description, email=email, phone=phone,
                    office=office, consultation_hours=hours, is_sample=is_sample)
        status_value = ("keep" if first else "draft") if published else ("draft" if first else "publish")
        ok, new_id = call(svc.save_faculty, token, form, current["id"] if current else None, status_value)
        if ok and photo is not None:
            ok, _ = call(svc.save_faculty_image, token, new_id, photo.getvalue(), photo.name, label="Saving photo...")
        if ok:
            flash("success", f"Saved {name}.")
            st.session_state["faculty_pick_next"] = f"{name} - {department} (#{new_id})"
            bump("faculty")
            st.rerun()
    if current:
        if st.button("Unpublish this profile" if current["published"] else "Publish this profile", key=f"fpub_{suffix}",
                     icon=":material/visibility_off:" if current["published"] else ":material/visibility:"):
            ok, _ = call(svc.set_faculty_published, token, current["id"], not current["published"])
            if ok:
                flash("success", "Profile updated.")
                st.rerun()
        with st.expander("Remove this profile permanently"):
            st.warning("This deletes the profile and its photo for good. Unpublishing hides it without deleting.", icon=":material/warning:")
            confirm = st.text_input(f"Type the full name ({current['name']}) to confirm", key=f"fdel_{suffix}")
            if st.button("Delete permanently", key=f"fdelbtn_{suffix}", type="primary", disabled=confirm.strip() != current["name"],
                         icon=":material/delete:"):
                ok, _ = call(svc.delete_faculty, token, current["id"], confirm)
                if ok:
                    flash("success", f"Removed {current['name']}.")
                    st.session_state["faculty_pick_next"] = NEW
                    bump("faculty")
                    st.rerun()


# ============================================================= achievements
def _achievement_preview(values: dict, image=None) -> None:
    with st.container(border=True):
        st.caption("PREVIEW - how this appears on the website")
        if image is not None:
            st.image(image, width=220)
        st.metric(values.get("title") or "(title)", values.get("highlight") or (values.get("achieved_on") or "")[:4] or values.get("category") or "-")
        if values.get("description"):
            st.write(values["description"])
        st.caption(" · ".join(x for x in (values.get("category"), values.get("achieved_on")) if x))


def achievements_section(token: str) -> None:
    st.title("College achievements", anchor=False)
    ok, items = call(svc.list_achievements, token, label="Loading...")
    if not ok:
        return
    if items:
        st.dataframe([{"Title": a["title"], "Highlight": a["highlight"], "Category": a["category"], "Date": a["achieved_on"],
                       "Status": "Published" if a["published"] else "Draft"} for a in items], hide_index=True, width="stretch")
    else:
        st.info("No achievements have been added yet. Nothing is shown on the public site until you add and publish some.", icon=":material/emoji_events:")
    labels = {f"{a['title']} (#{a['id']})": a["id"] for a in items}
    pick_with_next("ach_pick")
    label = st.selectbox("Choose an achievement to edit, or add a new one", [NEW] + list(labels), key="ach_pick")
    current = next((a for a in items if a["id"] == labels.get(label)), None)
    suffix = f"{current['id'] if current else NEW}_{nonce('ach')}"
    st.subheader(f"Edit: {current['title']}" if current else "Add an achievement", anchor=False)
    get = lambda k: (current[k] if current else "")
    existing_image = content.achievement_image(current["id"]) if current else None
    with st.form(f"ach_form_{suffix}"):
        title = st.text_input("Title *", value=get("title"), max_chars=150, key=f"at_{suffix}")
        c1, c2, c3 = st.columns(3)
        highlight = c1.text_input("Highlight value (for example A+ or 95%)", value=get("highlight"), max_chars=40, key=f"ah_{suffix}")
        category = c2.text_input("Category", value=get("category") or "General", max_chars=60, key=f"ac_{suffix}")
        achieved_on = c3.text_input("Date (2024, 2024-06 or 2024-06-30)", value=get("achieved_on"), max_chars=10, key=f"ad_{suffix}")
        description = st.text_area("Description", value=get("description"), max_chars=1000, height=110, key=f"ax_{suffix}")
        picture = st.file_uploader("Picture (optional, JPG, PNG or WebP, up to 2 MB)", type=["jpg", "jpeg", "png", "webp"], key=f"ai_{suffix}")
        published = bool(current and current["published"])
        b1, b2, b3, b4 = st.columns(4)
        preview = b1.form_submit_button("Preview", width="stretch")
        first = b2.form_submit_button("Save changes" if published else "Save draft", width="stretch")
        second = b3.form_submit_button("Save and unpublish" if published else "Save and publish", type="primary", width="stretch")
        cancel = b4.form_submit_button("Cancel (undo edits)", width="stretch")
    values = dict(title=title, highlight=highlight, category=category, achieved_on=achieved_on, description=description)
    if cancel:
        bump("ach")
        st.rerun()
    if preview:
        _achievement_preview(values, picture if picture is not None else existing_image)
    if first or second:
        status_value = ("keep" if first else "draft") if published else ("draft" if first else "publish")
        ok, new_id = call(svc.save_achievement, token, values, current["id"] if current else None, status_value)
        if ok and picture is not None:
            ok, _ = call(svc.save_achievement_image, token, new_id, picture.getvalue(), picture.name, label="Saving picture...")
        if ok:
            flash("success", f"Saved '{title}'.")
            st.session_state["ach_pick_next"] = f"{title.strip()} (#{new_id})"
            bump("ach")
            st.rerun()
    if current:
        if st.button("Unpublish" if current["published"] else "Publish", key=f"apub_{suffix}",
                     icon=":material/visibility_off:" if current["published"] else ":material/visibility:"):
            ok, _ = call(svc.set_achievement_published, token, current["id"], not current["published"])
            if ok:
                flash("success", "Achievement updated.")
                st.rerun()
        with st.expander("Delete this achievement permanently"):
            confirm = st.text_input(f"Type the title ({current['title']}) to confirm", key=f"adel_{suffix}")
            if st.button("Delete permanently", key=f"adelbtn_{suffix}", type="primary", disabled=confirm.strip() != current["title"],
                         icon=":material/delete:"):
                ok, _ = call(svc.delete_achievement, token, current["id"], confirm)
                if ok:
                    flash("success", f"Deleted '{current['title']}'.")
                    st.session_state["ach_pick_next"] = NEW
                    bump("ach")
                    st.rerun()


# ================================================================ enquiries
def enquiries_section(token: str) -> None:
    st.title("Registration and admission enquiries", anchor=False)
    st.info("The public website does not yet have a registration or enquiry form that saves submissions, so this list stays "
            "empty until one is added. A future form should save through `content_db.submit_enquiry()`. "
            "Nothing here is demonstration data.", icon=":material/info:")
    f1, f2, f3 = st.columns([2, 1, 1])
    search = f1.text_input("Search name, email, phone, course or reference", key="enq_q")
    status = f2.selectbox("Status", ["All"] + list(content.STATUSES), key="enq_status")
    courses = {c["name"]: c["id"] for c in cat.all_courses()}
    course = f3.selectbox("Course", ["All"] + list(courses), key="enq_course")
    d1, d2 = st.columns(2)
    start, end = d1.date_input("From date", value=None, key="enq_from"), d2.date_input("To date", value=None, key="enq_to")
    filters = dict(search=search, status=None if status == "All" else status, course=courses.get(course),
                   date_from=start.isoformat() if start else None, date_to=end.isoformat() if end else None)
    ok, rows = call(svc.list_enquiries, token, label="Loading...", **filters)
    if not ok:
        return
    if not rows:
        st.caption("No records match.")
        return
    st.dataframe([{"Ref": r["ref"], "Received (UTC)": r["created_at"].replace("T", " ")[:16], "Name": r["name"], "Course": r["course_name"],
                   "Status": r["status"]} for r in rows], hide_index=True, width="stretch")
    pick = st.selectbox("Open a record", [r["ref"] for r in rows], key="enq_pick")
    record = next(r for r in rows if r["ref"] == pick)
    with st.container(border=True):
        st.markdown(f"**{record['ref']}** · {record['name']}")
        st.write(f"Email: {record['email'] or '-'}  \nPhone: {record['phone'] or '-'}  \nCourse: {record['course_name'] or '-'}")
        st.write(record["message"] or "(no message)")
        st.caption(f"Received {record['created_at'].replace('T', ' ')[:16]} UTC · last updated by {record['updated_by'] or '-'}")
    with st.form(f"enq_form_{record['id']}"):
        new_status = st.selectbox("Status", list(content.STATUSES), index=content.STATUSES.index(record["status"]))
        note = st.text_area("Internal note (not shown to the applicant)", value=record["admin_note"] or "", max_chars=1000, height=80)
        if st.form_submit_button("Update status", type="primary"):
            ok, _ = call(svc.update_enquiry, token, record["id"], new_status, note)
            if ok:
                flash("success", "Status updated.")
                st.rerun()
    st.markdown("**Export**")
    if st.button("Prepare CSV export of the records above", key="enq_prepare", icon=":material/download:"):
        ok, csv_text = call(svc.export_enquiries_csv, token, label="Preparing...", **filters)
        if ok:
            st.session_state["enq_csv"] = csv_text
    if st.session_state.get("enq_csv"):
        st.download_button("Download CSV", st.session_state["enq_csv"], file_name="enquiries.csv", mime="text/csv", icon=":material/file_download:")
        st.caption("This file contains applicants' personal information. Store and share it carefully.")


# ============================================================ account/security
def account_section(token: str) -> None:
    st.title("Account and security", anchor=False)
    user = auth.validate(token)
    st.write(f"Signed in as **{user.email}**" + (f" ({user.name})" if user.name else ""))
    st.caption(f"Sessions end after {auth.IDLE_MINUTES} minutes without activity, and after at most {auth.MAX_SESSION_HOURS} hours.")
    st.subheader("Change password", anchor=False)
    with st.form(f"pw_form_{nonce('pw')}"):
        current = st.text_input("Current password", type="password")
        new = st.text_input("New password", type="password", help="At least 12 characters, with letters and numbers.")
        again = st.text_input("Repeat the new password", type="password")
        if st.form_submit_button("Change password", type="primary"):
            if new != again:
                st.error("The new passwords do not match.", icon=":material/error:")
            else:
                ok, _ = call(auth.change_password, token, current, new)
                if ok:
                    flash("success", "Password changed. Your other sessions were signed out.")
                    bump("pw")
                    st.rerun()
    if st.button("Sign out all my other sessions", icon=":material/devices:"):
        ok, count = call(auth.logout_other_sessions, token)
        if ok:
            flash("success", f"{count} other session(s) ended.")
            st.rerun()
    st.subheader("Administrators", anchor=False)
    ok, admins = call(auth.list_admins, token, label="Loading...")
    if ok:
        st.dataframe([{"Email": a["email"], "Name": a["name"], "Active": bool(a["is_active"]), "Last sign-in (UTC)": (a["last_login"] or "never").replace("T", " ")[:19]}
                      for a in admins], hide_index=True, width="stretch")
        st.caption("New administrators are created on the server with `python create_admin.py`; there is no sign-up page.")
    st.subheader("Activity log", anchor=False)
    ok, rows = call(auth.recent_audit, token, 40, label="Loading...")
    if ok:
        st.dataframe([{"When (UTC)": r["ts"].replace("T", " ")[:19], "Who": r["actor"], "Action": r["action"].replace("_", " "),
                       "Item": r["detail"] or r["entity_id"]} for r in rows], hide_index=True, width="stretch")


SECTION_FUNCTIONS = {
    "Dashboard Overview": dashboard_section, "College Information": college_section,
    "Courses and Specialisations": courses_section, "Fees and Eligibility": fees_section, "Faculty": faculty_section,
    "College Achievements": achievements_section, "Contact Information": contact_section,
    "Registration and Admission Enquiries": enquiries_section, "Website Content": website_section,
    "Account and Security": account_section,
}
