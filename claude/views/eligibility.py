import streamlit as st

import course_service
import eligibility_service as es
import registration_schema as schema
from eligibility import OUTCOME_MEETS, OUTCOME_NOT_MET

st.title("Eligibility Checker", anchor=False)
st.info(es.NOTICE, icon=":material/info:")
st.caption("Nothing you enter here is saved, logged or sent anywhere. No name or contact details are asked for.")

courses = course_service.list_courses()
names = {c["id"]: c["name"] for c in courses}
course_id = st.selectbox("Course", list(names), index=None, placeholder="Choose a course",
                         format_func=names.get, key="elig_course")
if not course_id:
    st.caption("Choose a course to see its stored requirements and check your answers against them.")
    st.stop()

course = course_service.get_course(course_id)
with st.expander("Stored requirements for this course", expanded=True):
    for line in es.describe_requirements(course):
        st.write(f"- {line}")

routes = es.routes_for(course)
if len(routes) > 1:
    route = st.radio("How are you applying?", routes, horizontal=True, format_func=schema.ROUTE_LABELS.get,
                     key=f"elig_route_{course_id}")
else:
    route = routes[0]
    st.write(f"**Qualification:** {schema.ROUTE_LABELS[route]}")

needs = es.inputs_needed(course, route)
answers: dict = {"route": route}
if needs["result_status"]:
    answers["result_status"] = st.radio("Class 12 result", [schema.RESULT_DECLARED, schema.RESULT_AWAITED],
                                        horizontal=True, key=f"elig_status_{course_id}")
if needs["percentage"]:
    awaited = answers.get("result_status") == schema.RESULT_AWAITED
    if awaited:
        st.caption("A percentage is not needed while your result is awaited.")
    else:
        answers["percentage"] = st.number_input("Your overall percentage", min_value=0.0, max_value=100.0,
                                                value=None, step=0.1, format="%.2f", key=f"elig_pct_{course_id}")
if needs["subjects"]:
    answers["subjects"] = st.multiselect("Subjects studied in Class 12", schema.CLASS12_SUBJECTS,
                                         key=f"elig_subj_{course_id}", placeholder="Choose all that apply")
if needs["other_subjects"]:
    answers["other_subjects"] = st.text_input("Other subjects (optional, separated by commas)", max_chars=es.MAX_TEXT,
                                              key=f"elig_other_{course_id}")

if st.button("Check eligibility", type="primary", key="elig_check"):
    st.session_state["elig_result"] = {"for": course_id, "data": es.check_course(course_id, answers)}

saved = st.session_state.get("elig_result")
result = saved["data"] if saved and saved["for"] == course_id else None
if result:
    if not result["valid"]:
        for message in result["errors"].values():
            st.error(message, icon=":material/error:")
        st.stop()
    box = {OUTCOME_MEETS: st.success, OUTCOME_NOT_MET: st.warning}.get(result["outcome"], st.info)
    box(f"**{result['label']}** for {result['course_name']}")
    st.write(result["explanation"])
    for title, items, icon in (("Met", result["met"], ":material/check_circle:"),
                               ("Not met", result["unmet"], ":material/cancel:"),
                               ("Needs confirmation or more information", result["unverified"], ":material/help:")):
        if items:
            st.markdown(f"**{title}**")
            for item in items:
                st.markdown(f"- {icon} **{item['criterion']}:** {item['detail']}")
    for note in result["notes"]:
        st.caption(note)
    st.markdown("**Next steps**")
    st.markdown("\n".join(f"- {step}" for step in result["next_steps"]))
    st.caption(result["notice"])
    if st.button("Register for this course", key="elig_register"):
        st.session_state["selected_course"] = course["name"]
        st.switch_page("views/admissions.py")
