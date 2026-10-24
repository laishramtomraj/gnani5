"""fees_ui.py - Streamlit rendering for fees, scholarships, assistance, payment schedules and refunds.

Used by views/fees.py (full section) and views/courses.py (the "Fees & scholarships" tab).
Display only: no payments are taken and nothing here confirms a payment.
"""
import streamlit as st

import fee_logic as fl
from fee_catalogue import (
    ACCOMMODATION_OPTIONS, CATEGORY_LABEL, COMBINATION_RULES, COMPULSORY_CATEGORIES, FACILITY_CATEGORIES,
    FEES_NOTICE, FEE_STRUCTURES, FINANCIAL_ASSISTANCE, FREQUENCY_LABEL, OPTIONAL, PAYMENT_PLANS,
    PAYMENT_TERMS, REFUND_POLICY, SCHOLARSHIPS, TRANSPORT_OPTIONS,
)
from fee_logic import NOT_AVAILABLE, money

STATUS_LABEL = {"illustrative": "Illustrative prototype", "details_unavailable": "Details not available"}


@st.cache_data(show_spinner=False)
def _problems(stamp: tuple) -> list[str]:
    return fl.validate()


def data_ok() -> bool:
    """Show a clear error (only in the fee areas) if the fee data is inconsistent."""
    problems = _problems(tuple((c["id"], c["name"], c["tuition"], c["years"], c["group"]) for c in fl.COURSES))
    if problems:
        st.error("The fee data has problems and cannot be shown:\n\n" + "\n".join(f"- {p}" for p in problems))
        return False
    return True


def notice() -> None:
    st.info(FEES_NOTICE, icon=":material/info:")


def _text(value) -> str:
    return NOT_AVAILABLE if value in (None, "", []) else str(value)


def _bullets(items) -> None:
    if items:
        st.markdown("\n".join(f"- {i}" for i in items))
    else:
        st.write(NOT_AVAILABLE)


def _table(rows: list[dict], total_label: str | None = None, total: int | None = None) -> None:
    data = [{"Charge": r["label"], "When charged": FREQUENCY_LABEL[r["frequency"]],
             "Amount": money(r["amount"]), "Times": str(r["times"]), "Total for course": money(r["total"]),
             "Note": r["note"] or ""} for r in rows]
    if total_label:
        data.append({"Charge": total_label, "When charged": "", "Amount": "", "Times": "",
                     "Total for course": money(total), "Note": ""})
    st.dataframe(data, hide_index=True, width="stretch")


# ------------------------------------------------------------ option picker
def options_picker(prefix: str, course_id: str) -> dict:
    """Widgets for hostel, mess, transport and optional items. Returns the options dict for fee_logic."""
    optional = {c["id"]: c["label"] for c in FEE_STRUCTURES[course_id]["components"] if c["category"] == OPTIONAL}
    a, b, c = st.columns(3)
    accommodation = a.selectbox("Hostel", list(ACCOMMODATION_OPTIONS), key=f"{prefix}_hostel",
                                format_func=lambda k: ACCOMMODATION_OPTIONS[k]["label"])
    transport = b.selectbox("Transport", list(TRANSPORT_OPTIONS), key=f"{prefix}_transport",
                            format_func=lambda k: TRANSPORT_OPTIONS[k]["label"])
    mess = c.toggle("Include mess (meals)", key=f"{prefix}_mess")
    chosen = st.multiselect("Optional expenses to include in the estimate", list(optional),
                            key=f"{prefix}_optional_{course_id}", format_func=lambda k: optional[k])
    return {"accommodation": accommodation, "mess": mess, "transport": transport, "optional": chosen}


# -------------------------------------------------------------- breakdown
def render_breakdown(course_id: str, options: dict | None = None) -> None:
    s = fl.cost_summary(course_id, options)
    rows = s["rows"]
    years = s["years"]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Compulsory charges, whole course", money(s["compulsory_total"]),
              help="Tuition, other compulsory academic charges and one-time fees over the full duration. "
                   "Refundable deposits are not counted as a cost.")
    m2.metric("Compulsory, every year", money(s["recurring_compulsory_per_year"]),
              help="Tuition and yearly and semester charges for one year, without one-time fees.")
    m3.metric("Refundable deposits", money(s["refundable_deposits_total"]),
              help="Paid once and refundable under the refund policy.")
    m4.metric("Estimate with your choices", money(s["estimated_cost"]),
              help="Compulsory charges plus the hostel, mess, transport and optional items you selected. "
                   "Refundable deposits are excluded.")
    st.caption(f"{years} years · {s['semesters']} semesters. Tuition is counted once, yearly items are "
               f"multiplied by {years}, semester items by {s['semesters']}, one-time items by 1.")

    st.markdown("**Compulsory charges**")
    comp = [r for r in rows if r["category"] in COMPULSORY_CATEGORIES and not r["refundable"]]
    _table(comp, "Total compulsory charges", s["compulsory_total"])

    dep = [r for r in rows if r["refundable"]]
    if dep:
        st.markdown("**Refundable deposits** (shown separately, not added to costs)")
        _table(dep, "Total refundable deposits", s["refundable_deposits_total"])

    fac = [r for r in rows if r["category"] in FACILITY_CATEGORIES and not r["refundable"]]
    if fac:
        st.markdown("**Hostel, mess and transport you selected**")
        _table(fac, "Total facilities", s["facilities_total"])
    else:
        st.caption("Hostel, mess and transport are not included. Choose them above to add them.")

    st.markdown("**Optional expenses** (shown separately)")
    opt = [r for r in rows if r["category"] == OPTIONAL]
    _table(opt)
    st.caption("Optional items are added to the estimate only when you select them. "
               f"Selected optional total: {money(s['optional_total'])}.")

    st.markdown("**Year by year**")
    st.dataframe(
        [{"Year": y["year"], "Compulsory": money(y["compulsory"]), "Facilities": money(y["facilities"]),
          "Optional": money(y["optional"]), "Refundable deposits": money(y["refundable_deposits"]),
          "Total to pay": money(y["total"])} for y in s["by_year"]],
        hide_index=True, width="stretch")

    st.write(f"**Estimated cost for the whole course (excluding refundable deposits):** {money(s['estimated_cost'])}")
    st.write(f"**Total cash paid over the course (including refundable deposits):** {money(s['cash_outlay'])}")
    if s["unavailable"]:
        st.warning("Amount not available, so not included in any total: " + "; ".join(s["unavailable"]) + ".",
                   icon=":material/warning:")
    st.caption("Fees may change from year to year. Any increase is not included in these figures.")


def render_facility_options(course_id: str) -> None:
    """Every hostel, mess and transport choice, separate from compulsory fees."""
    rows = fl.facility_rows(course_id)
    st.dataframe(
        [{"Option": r["option"], "Charge": r["label"], "When charged": FREQUENCY_LABEL[r["frequency"]],
          "Amount": money(r["amount"]), "Total for course": money(r["total"]),
          "Refundable": "Yes" if r["refundable"] else "No"} for r in rows],
        hide_index=True, width="stretch")
    st.caption("Facility charges are shown for the course duration and are never part of the compulsory total.")


# ---------------------------------------------------------- scholarships
def render_scholarship(s: dict) -> None:
    with st.expander(f"{s['name']}  ·  {fl.award_text(s)}"):
        st.badge(STATUS_LABEL[s["status"]], color="orange" if s["status"] == "illustrative" else "gray")
        st.write(f"**Type:** {s['kind'].capitalize()}")
        st.write(f"**Award:** {fl.award_text(s)}")
        st.write(f"**Eligibility:** {_text(s['eligibility'])}")
        courses = fl.scholarship_courses(s["id"])
        if courses is None:
            st.write(f"**Eligible courses:** {NOT_AVAILABLE}")
        elif len(courses) == len(fl.COURSES):
            st.write("**Eligible courses:** All courses")
        else:
            st.write("**Eligible courses:** " + ", ".join(fl.COURSE_BY_ID[c]["name"] for c in courses))
        st.write(f"**Application deadline:** {fl.deadline_text(s)}")
        st.markdown("**Documents required**")
        _bullets(s["documents"])
        st.write(f"**Renewal conditions:** {_text(s['renewal'])}")
        st.write(f"**Combination rules:** {_text(s['combination'])}")


def render_scholarships(course_id: str | None = None) -> None:
    if course_id:
        found = fl.eligible_scholarships(course_id)
        st.markdown("**Institutional scholarships you may apply for**")
        for s in found["institutional"]:
            render_scholarship(s)
        st.markdown("**Government and regional schemes**")
        for s in found["details_unavailable"]:
            render_scholarship(s)
    else:
        kinds = ["All"] + sorted({s["kind"] for s in SCHOLARSHIPS})
        kind = st.selectbox("Type", kinds, key="sch_kind", format_func=str.capitalize)
        for s in SCHOLARSHIPS:
            if kind == "All" or s["kind"] == kind:
                render_scholarship(s)
    st.caption("Government and regional scheme details are not included here. Check the official "
               "notification of each scheme.")


def render_combination_rules() -> None:
    st.markdown("**How awards combine (illustrative)**")
    _bullets(COMBINATION_RULES["notes"])


def render_estimator(course_id: str) -> None:
    found = fl.eligible_scholarships(course_id)["institutional"]
    names = {s["id"]: f"{s['name']} ({fl.award_text(s)})" for s in found}
    st.markdown("**Scholarship estimator**")
    chosen = st.multiselect("Awards you expect to qualify for", list(names), key=f"est_{course_id}",
                            format_func=lambda k: names[k])
    if not chosen:
        st.caption("Pick the awards you expect to qualify for. This assumes you meet every criterion.")
        return
    e = fl.estimate_scholarships(course_id, chosen)
    st.dataframe(
        [{"Scholarship": i["name"], "Yearly value": money(i["requested"]), "Applied": money(i["applied"])}
         for i in e["items"]], hide_index=True, width="stretch")
    for r in e["rejected"]:
        st.warning(f"{r['name']}: {r['reason']}", icon=":material/warning:")
    if e["capped"]:
        st.warning(f"Total limited to {COMBINATION_RULES['max_total_pct_of_tuition']}% of tuition "
                   f"({money(e['cap'])} a year).", icon=":material/warning:")
    a, b, c = st.columns(3)
    a.metric("Scholarship per year", money(e["applied_total"]))
    b.metric("Tuition per year after awards", money(e["tuition_after_per_year"]))
    c.metric("Tuition over the course after awards", money(e["tuition_after_over_course"]),
             help="Assumes every award is renewed each year.")
    st.caption("Estimate only. Awards are subject to eligibility, selection and yearly renewal conditions. "
               "Other charges are not reduced.")


# ---------------------------------------------------- financial assistance
def render_assistance() -> None:
    for fa in FINANCIAL_ASSISTANCE:
        with st.container(border=True):
            st.markdown(f"**{fa['name']}**")
            st.badge(STATUS_LABEL[fa["status"]], color="orange" if fa["status"] == "illustrative" else "gray")
            st.write(fa["description"])
            st.write(f"**Eligibility:** {_text(fa['eligibility'])}")
            st.write(f"**Amount:** {_text(fa['amount_info'])}")
            st.write(f"**How to apply:** {_text(fa['how_to_apply'])}")
            st.markdown("**Documents**")
            _bullets(fa["documents"] or ["None listed"])
            st.markdown("**Conditions**")
            _bullets(fa["conditions"])


# --------------------------------------------------------------- schedule
def render_schedule(course_id: str, plan_id: str, options: dict | None = None) -> None:
    sch = fl.payment_schedule(course_id, plan_id, options)
    st.dataframe(
        [{"No.": i["no"], "Payment": i["when"], "Due": i["due"], "Amount": money(i["amount"]),
          "Includes": i["includes"]} for i in sch["instalments"]],
        hide_index=True, width="stretch")
    st.write(f"**Total of all payments:** {money(sch['total'])}")
    if not sch["matches_cost_summary"]:
        st.error("The instalments do not add up to the cost summary. Please report this.")
    if sch["unavailable"]:
        st.warning("Not included because the amount is not available: " + "; ".join(sch["unavailable"]) + ".",
                   icon=":material/warning:")
    st.write(f"**Late fee:** {money(sch['late_fee'])}  ·  **Grace period:** "
             f"{NOT_AVAILABLE if sch['grace_period_days'] is None else str(sch['grace_period_days']) + ' days'}"
             f"  ·  **Payment modes:** {_text(sch['payment_modes'])}")
    st.caption(PAYMENT_TERMS["note"])


# ----------------------------------------------------------------- refunds
def render_refund_policy() -> None:
    st.caption("Illustrative policy. Percentages apply to amounts actually paid for the period.")
    st.markdown("**Withdrawal and refund windows**")
    st.dataframe(
        [{"When the request is received": w["label"], "Tuition refunded": f"{w['tuition_pct']}%",
          "Other academic charges refunded": f"{w['other_pct']}%", "Note": w["note"]}
         for w in REFUND_POLICY["windows"]], hide_index=True, width="stretch")
    st.markdown("**Hostel, mess and transport**")
    st.dataframe(
        [{"When": w["label"], "Refunded": NOT_AVAILABLE if w["pct"] is None else f"{w['pct']}%",
          "Note": w["note"]} for w in REFUND_POLICY["facility_windows"]], hide_index=True, width="stretch")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Refundable charges**")
        _bullets(REFUND_POLICY["refundable_items"])
        st.write(REFUND_POLICY["deposit_conditions"])
    with c2:
        st.markdown("**Non-refundable charges**")
        _bullets(REFUND_POLICY["non_refundable_items"])
    st.markdown("**Withdrawal rules**")
    _bullets(REFUND_POLICY["withdrawal_rules"])
    st.markdown("**Cancellation conditions**")
    st.dataframe([{"Situation": c["case"], "Outcome": c["outcome"]} for c in REFUND_POLICY["cancellation_conditions"]],
                 hide_index=True, width="stretch")
    days, mode = REFUND_POLICY["processing_time_days"], REFUND_POLICY["refund_mode"]
    st.write(f"**Refund processing time:** {NOT_AVAILABLE if days is None else str(days) + ' days'}  ·  "
             f"**Refund mode:** {_text(mode)}")


# ------------------------------------------------------- course detail tab
def _open_fees(course_id: str) -> None:
    st.session_state["fees_course_id"] = course_id


def render_course_tab(course_id: str) -> None:
    """The 'Fees & scholarships' tab inside a course's detail view."""
    if not data_ok():
        return
    notice()
    render_breakdown(course_id)
    st.markdown("**Scholarships for this course**")
    found = fl.eligible_scholarships(course_id)
    st.dataframe(
        [{"Scholarship": s["name"], "Award": fl.award_text(s), "Deadline": fl.deadline_text(s)}
         for s in found["institutional"]]
        + [{"Scholarship": s["name"], "Award": NOT_AVAILABLE, "Deadline": NOT_AVAILABLE}
           for s in found["details_unavailable"]],
        hide_index=True, width="stretch")
    if st.button("Hostel, payment schedule, scholarships and refunds", icon=":material/payments:",
                 key=f"fees_open_{course_id}", on_click=_open_fees, args=(course_id,)):
        st.switch_page("views/fees.py")
