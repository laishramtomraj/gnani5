import streamlit as st

import fee_logic as fl
import fees_ui as ui
from data import COURSES
from fee_catalogue import PAYMENT_PLANS

st.title("Fees & Scholarships", anchor=False)
ui.notice()

if ui.data_ok():
    ids = [c["id"] for c in COURSES]
    names = {c["id"]: c["name"] for c in COURSES}
    preset = st.session_state.get("fees_course_id")          # set by a course's "Fees & scholarships" tab

    def pick_course(key: str) -> str:
        return st.selectbox("Course", ids, index=ids.index(preset) if preset in ids else 0,
                            key=key, format_func=lambda i: names[i])

    fees_tab, sch_tab, aid_tab, plan_tab, refund_tab = st.tabs(
        ["Course fees", "Scholarships", "Financial assistance", "Payment schedule", "Refund policy"])

    with fees_tab:
        course_id = pick_course("fees_pick")
        options = ui.options_picker("fees", course_id)
        ui.render_breakdown(course_id, options)
        st.markdown("**Hostel, mess and transport options**")
        ui.render_facility_options(course_id)
        with st.expander("Compare compulsory fees across all courses"):
            st.dataframe(
                [{"Course": r["course"], "Years": r["years"],
                  "Tuition per year": fl.money(r["tuition_per_year"]),
                  "Compulsory, every year": fl.money(r["recurring_per_year"]),
                  "Compulsory, first year": fl.money(r["first_year"]),
                  "Compulsory, whole course": fl.money(r["compulsory_total"]),
                  "Refundable deposit": fl.money(r["refundable_deposit"])} for r in fl.fee_overview()],
                hide_index=True, width="stretch")
            st.caption("Compulsory charges exclude hostel, mess, transport and optional expenses.")

    with sch_tab:
        scope = st.radio("Show", ["All scholarships", "For one course"], horizontal=True, key="sch_scope")
        if scope == "For one course":
            course_id = pick_course("sch_pick")
            ui.render_scholarships(course_id)
            ui.render_estimator(course_id)
        else:
            ui.render_scholarships()
        ui.render_combination_rules()

    with aid_tab:
        ui.render_assistance()

    with plan_tab:
        course_id = pick_course("plan_pick")
        plan_id = st.radio("Payment plan", list(PAYMENT_PLANS), horizontal=True, key="plan_choice",
                           format_func=lambda p: PAYMENT_PLANS[p]["name"])
        options = ui.options_picker("plan", course_id)
        ui.render_schedule(course_id, plan_id, options)

    with refund_tab:
        ui.render_refund_policy()

    st.session_state.pop("fees_course_id", None)             # the preset is used once, then cleared
