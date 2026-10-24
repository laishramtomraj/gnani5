"""fee_logic.py - calculations, validation and AI-ready records for fee_catalogue.py (no Streamlit here).

All totals are computed from fee components. Nothing is typed in twice, so nothing can drift:
  * annual items are multiplied by the course duration in years,
  * per-semester items by 2 x years,
  * one-time items are counted once (refundable deposits are kept apart from costs),
  * tuition is read from the course record and counted once.
Amounts that are None ("Not available") are listed but never added to a total, and are reported.
"""
from collections.abc import Mapping
from datetime import date

from data import COURSES, format_inr
from fee_catalogue import (
    ACCOMMODATION_OPTIONS, ANNUAL, CATEGORY_LABEL, COMBINATION_RULES, COMPULSORY_CATEGORIES,
    FACILITY_CATEGORIES, FEE_STRUCTURES, FEES_NOTICE, FINANCIAL_ASSISTANCE, FREQUENCY_LABEL,
    MESS_COMPONENTS, ONE_TIME, OPTIONAL, PAYMENT_PLANS, PAYMENT_TERMS, REFUND_POLICY, SCHOLARSHIPS,
    SEMESTER, TRANSPORT_OPTIONS, TUITION, ADMISSION_DUE,
)

NOT_AVAILABLE = "Not available"


class _LiveCourses(Mapping):
    """Course lookup over the CURRENT course list (it changes when college.db changes)."""

    def __getitem__(self, course_id):
        for c in COURSES:
            if c["id"] == course_id:
                return c
        raise KeyError(course_id)

    def __iter__(self):
        return iter([c["id"] for c in COURSES])

    def __len__(self):
        return len(COURSES)


COURSE_BY_ID = _LiveCourses()
SCHOLARSHIP_BY_ID = {s["id"]: s for s in SCHOLARSHIPS}
LEVELS = {"Undergraduate", "Postgraduate"}


def money(value) -> str:
    """Indian rupee formatting, or 'Not available' for a missing value."""
    return NOT_AVAILABLE if value is None else format_inr(value)


def _course(course_id: str) -> dict:
    try:
        return COURSE_BY_ID[course_id]
    except KeyError:
        raise ValueError(f"Unknown course id: {course_id!r}") from None


# ------------------------------------------------------------------ options
def normalise_options(options: dict | None) -> dict:
    o = options or {}
    acc, trn = o.get("accommodation", "none"), o.get("transport", "none")
    if acc not in ACCOMMODATION_OPTIONS:
        raise ValueError(f"Unknown accommodation option: {acc!r}")
    if trn not in TRANSPORT_OPTIONS:
        raise ValueError(f"Unknown transport option: {trn!r}")
    return {"accommodation": acc, "mess": bool(o.get("mess", False)), "transport": trn,
            "optional": list(o.get("optional", []))}


def multiplier(frequency: str, years: int) -> int:
    if frequency == ANNUAL:
        return years
    if frequency == SEMESTER:
        return 2 * years
    if frequency == ONE_TIME:
        return 1
    raise ValueError(f"Unknown fee frequency: {frequency!r}")


def _row(comp: dict, years: int, selected: bool) -> dict:
    times = multiplier(comp["frequency"], years)
    amount = comp["amount"]
    return {**comp, "times": times, "selected": selected,
            "total": None if amount is None else amount * times}


def _amount_for_year(row: dict, year: int) -> int:
    """What a row contributes in a given year (1-based). One-time items fall in year 1 only."""
    if row["amount"] is None or not row["selected"]:
        return 0
    if row["frequency"] == ANNUAL:
        return row["amount"]
    if row["frequency"] == SEMESTER:
        return 2 * row["amount"]
    return row["amount"] if year == 1 else 0


def cost_rows(course_id: str, options: dict | None = None) -> list[dict]:
    """Every fee line that applies: compulsory, the chosen facilities, and all optional items
    (optional ones carry selected=False unless listed in options['optional'])."""
    course = _course(course_id)
    opts = normalise_options(options)
    years = course["years"]
    rows = []
    for comp in FEE_STRUCTURES[course_id]["components"]:
        selected = comp["category"] != OPTIONAL or comp["id"] in opts["optional"]
        rows.append(_row(comp, years, selected))
    facility = list(ACCOMMODATION_OPTIONS[opts["accommodation"]]["components"])
    if opts["mess"]:
        facility += MESS_COMPONENTS
    facility += TRANSPORT_OPTIONS[opts["transport"]]["components"]
    rows += [_row(c, years, True) for c in facility]
    return rows


def _sum(rows, pred) -> int:
    return sum(r["total"] for r in rows if r["selected"] and r["total"] is not None and pred(r))


def cost_summary(course_id: str, options: dict | None = None) -> dict:
    course = _course(course_id)
    opts = normalise_options(options)
    rows = cost_rows(course_id, opts)
    years = course["years"]

    compulsory = _sum(rows, lambda r: r["category"] in COMPULSORY_CATEGORIES and not r["refundable"])
    facilities = _sum(rows, lambda r: r["category"] in FACILITY_CATEGORIES and not r["refundable"])
    optional = _sum(rows, lambda r: r["category"] == OPTIONAL)
    deposits = _sum(rows, lambda r: r["refundable"])
    tuition = _sum(rows, lambda r: r["category"] == TUITION)

    recurring_per_year = sum(
        _amount_for_year(r, 2) for r in rows
        if r["category"] in COMPULSORY_CATEGORIES and not r["refundable"] and r["frequency"] != ONE_TIME)

    by_year = []
    for y in range(1, years + 1):
        def part(pred):
            return sum(_amount_for_year(r, y) for r in rows if pred(r))
        c = part(lambda r: r["category"] in COMPULSORY_CATEGORIES and not r["refundable"])
        f = part(lambda r: r["category"] in FACILITY_CATEGORIES and not r["refundable"])
        o = part(lambda r: r["category"] == OPTIONAL)
        d = part(lambda r: r["refundable"])
        by_year.append({"year": y, "compulsory": c, "facilities": f, "optional": o,
                        "refundable_deposits": d, "total": c + f + o + d})

    unavailable = [r["label"] for r in rows if r["selected"] and r["amount"] is None]
    return {
        "course_id": course_id, "course_name": course["name"], "years": years,
        "semesters": 2 * years, "options": opts, "rows": rows,
        "tuition_total": tuition,
        "compulsory_total": compulsory,                 # tuition + other compulsory + one-time, no deposits
        "recurring_compulsory_per_year": recurring_per_year,
        "facilities_total": facilities, "optional_total": optional,
        "refundable_deposits_total": deposits,
        "estimated_cost": compulsory + facilities + optional,          # excludes refundable deposits
        "cash_outlay": compulsory + facilities + optional + deposits,  # what is paid in total
        "by_year": by_year, "unavailable": unavailable, "complete": not unavailable,
    }


def facility_rows(course_id: str) -> list[dict]:
    """All hostel, mess and transport choices with per-year and course-duration amounts."""
    years = _course(course_id)["years"]
    out = []
    for key, opt in ACCOMMODATION_OPTIONS.items():
        for c in opt["components"]:
            out.append({**_row(c, years, True), "option": opt["label"]})
    for c in MESS_COMPONENTS:
        out.append({**_row(c, years, True), "option": "Mess"})
    for key, opt in TRANSPORT_OPTIONS.items():
        for c in opt["components"]:
            out.append({**_row(c, years, True), "option": opt["label"]})
    return out


def fee_overview() -> list[dict]:
    """One line per course for the comparison table. Every number comes from cost_summary."""
    out = []
    for c in COURSES:
        s = cost_summary(c["id"])
        out.append({"course_id": c["id"], "course": c["name"], "years": c["years"],
                    "tuition_per_year": c["tuition"], "recurring_per_year": s["recurring_compulsory_per_year"],
                    "first_year": s["by_year"][0]["compulsory"],
                    "compulsory_total": s["compulsory_total"],
                    "refundable_deposit": s["refundable_deposits_total"],
                    "cash_outlay": s["cash_outlay"]})
    return out


# --------------------------------------------------------- payment schedule
def payment_schedule(course_id: str, plan_id: str, options: dict | None = None) -> dict:
    if plan_id not in PAYMENT_PLANS:
        raise ValueError(f"Unknown payment plan: {plan_id!r}")
    plan = PAYMENT_PLANS[plan_id]
    s = cost_summary(course_id, options)
    live = [r for r in s["rows"] if r["selected"] and r["amount"] is not None]
    one_time = sum(r["amount"] for r in live if r["frequency"] == ONE_TIME)
    annual = sum(r["amount"] for r in live if r["frequency"] == ANNUAL)
    per_sem = sum(r["amount"] for r in live if r["frequency"] == SEMESTER)

    instalments = []

    def add(when, due, amount, includes):
        instalments.append({"no": len(instalments) + 1, "when": when, "due": due,
                            "amount": amount, "includes": includes})

    add("On admission confirmation", ADMISSION_DUE, one_time,
        "One-time fees and refundable deposits (and hostel registration and deposit, if chosen)")
    for y in range(1, s["years"] + 1):
        if plan["instalments_per_year"] == 2:
            first = -(-annual // 2)                    # ceiling, so the two halves add back to the total
            add(f"Year {y}, semester {2 * y - 1}", plan["due"]["odd"], first + per_sem,
                "Half of the yearly charges and the semester examination fee")
            add(f"Year {y}, semester {2 * y}", plan["due"]["even"], annual - first + per_sem,
                "Other half of the yearly charges and the semester examination fee")
        else:
            add(f"Year {y}", plan["due"]["odd"], annual + 2 * per_sem,
                "All yearly charges and both semester examination fees")
    total = sum(i["amount"] for i in instalments)
    return {"course_id": course_id, "plan": plan_id, "plan_name": plan["name"], "instalments": instalments,
            "total": total, "matches_cost_summary": total == s["cash_outlay"],
            "unavailable": s["unavailable"], "late_fee": PAYMENT_TERMS["late_fee"],
            "grace_period_days": PAYMENT_TERMS["grace_period_days"],
            "payment_modes": PAYMENT_TERMS["payment_modes"]}


# ------------------------------------------------------------- scholarships
def scholarship_applies(s: dict, course: dict) -> bool | None:
    """True/False for institutional records; None when eligible courses are not available."""
    rule = s["applies_to"]
    if rule is None:
        return None
    return ((rule["levels"] is None or course["level"] in rule["levels"])
            and (rule["groups"] is None or course["group"] in rule["groups"])
            and (rule["courses"] is None or course["id"] in rule["courses"]))


def eligible_scholarships(course_id: str) -> dict:
    course = _course(course_id)
    inst = [s for s in SCHOLARSHIPS if scholarship_applies(s, course) is True]
    unknown = [s for s in SCHOLARSHIPS if scholarship_applies(s, course) is None]
    return {"institutional": inst, "details_unavailable": unknown}


def _courses_for(s: dict) -> list[str] | None:
    if s["applies_to"] is None:
        return None
    return [c["id"] for c in COURSES if scholarship_applies(s, c)]


def scholarship_courses(sid: str) -> list[str] | None:
    return _courses_for(SCHOLARSHIP_BY_ID[sid])


def annual_award(s: dict, course: dict) -> int | None:
    """Yearly value for the course, or None when the award amount is not available."""
    tuition, value = course["tuition"], s["award_value"]
    if tuition is None or value is None or s["award_type"] == "none":
        return None
    if s["award_type"] == "percent_tuition":
        amount = tuition * value // 100
        if s["award_cap"] is not None:
            amount = min(amount, s["award_cap"])
    elif s["award_type"] == "fixed_amount":
        amount = value
    else:
        return None
    return min(amount, tuition)


def award_text(s: dict) -> str:
    if s["award_type"] == "percent_tuition":
        cap = f", up to {money(s['award_cap'])} a year" if s["award_cap"] is not None else ""
        return f"{s['award_value']}% of annual tuition{cap}"
    if s["award_type"] == "fixed_amount":
        return f"{money(s['award_value'])} a year"
    return NOT_AVAILABLE


def deadline_text(s: dict) -> str:
    if s["deadline"]:
        d = date.fromisoformat(s["deadline"])
        return f"{d.day} {d.strftime('%b %Y')} (illustrative)"
    return s["deadline_note"] or NOT_AVAILABLE


def estimate_scholarships(course_id: str, scholarship_ids: list[str]) -> dict:
    """Apply the combination rules to the chosen awards. Assumes the student meets every criterion."""
    course = _course(course_id)
    tuition = course["tuition"]
    kept, rejected = {}, []
    for sid in dict.fromkeys(scholarship_ids):                      # de-duplicated, order kept
        s = SCHOLARSHIP_BY_ID.get(sid)
        if s is None:
            rejected.append({"id": sid, "name": sid, "reason": "Unknown scholarship."})
            continue
        amount = annual_award(s, course)
        if scholarship_applies(s, course) is not True or amount is None:
            rejected.append({"id": sid, "name": s["name"],
                             "reason": "Not available for this course or amount not available."})
            continue
        kept[sid] = amount

    for group in {SCHOLARSHIP_BY_ID[i]["exclusive_group"] for i in kept} - {None}:   # one per group
        members = sorted((i for i in kept if SCHOLARSHIP_BY_ID[i]["exclusive_group"] == group),
                         key=lambda i: (-kept[i], i))
        for loser in members[1:]:
            rejected.append({"id": loser, "name": SCHOLARSHIP_BY_ID[loser]["name"],
                             "reason": "Cannot be held together with "
                                       f"{SCHOLARSHIP_BY_ID[members[0]]['name']}. The larger award applies."})
            del kept[loser]

    cap = None if tuition is None else tuition * COMBINATION_RULES["max_total_pct_of_tuition"] // 100
    remaining = cap
    items = []
    for sid, amount in sorted(kept.items(), key=lambda kv: (-kv[1], kv[0])):
        applied = amount if remaining is None else min(amount, remaining)
        if remaining is not None:
            remaining -= applied
        items.append({"id": sid, "name": SCHOLARSHIP_BY_ID[sid]["name"], "requested": amount, "applied": applied})
    requested = sum(i["requested"] for i in items)
    applied = sum(i["applied"] for i in items)
    return {"course_id": course_id, "tuition": tuition, "cap": cap, "items": items, "rejected": rejected,
            "requested_total": requested, "applied_total": applied, "capped": applied < requested,
            "tuition_after_per_year": None if tuition is None else tuition - applied,
            "applied_over_course": applied * course["years"],
            "tuition_after_over_course": None if tuition is None else (tuition - applied) * course["years"]}


# --------------------------------------------------------------- validation
_CATEGORIES = set(CATEGORY_LABEL)
_FREQUENCIES = set(FREQUENCY_LABEL)
_KINDS = {"merit", "need", "sports", "achievement", "government", "regional"}
_AWARDS = {"percent_tuition", "fixed_amount", "none"}
_STATUSES = {"illustrative", "details_unavailable"}


def _check_components(owner: str, comps: list[dict], problems: list[str]) -> None:
    seen = set()
    for c in comps:
        where = f"{owner}/{c.get('id')}"
        if c["id"] in seen:
            problems.append(f"Duplicate fee component: {where}")
        seen.add(c["id"])
        if c["category"] not in _CATEGORIES:
            problems.append(f"{where}: unknown category {c['category']!r}")
        if c["frequency"] not in _FREQUENCIES:
            problems.append(f"{where}: unknown frequency {c['frequency']!r}")
        a = c["amount"]
        if a is not None and (not isinstance(a, int) or isinstance(a, bool) or a < 0):
            problems.append(f"{where}: amount must be a non-negative whole number or None, got {a!r}")
        if c["refundable"] and c["frequency"] != ONE_TIME:
            problems.append(f"{where}: refundable items must be one-time deposits")
        if not c["label"]:
            problems.append(f"{where}: missing label")


def validate() -> list[str]:
    """Return a list of problems. An empty list means the fee data is consistent."""
    problems: list[str] = []

    ids = [c["id"] for c in COURSES]
    if len(ids) != len(set(ids)):
        problems.append("Duplicate course ids in the course catalogue.")
    for cid in set(ids) - set(FEE_STRUCTURES):
        problems.append(f"Course has no fee structure: {cid}")
    for cid in set(FEE_STRUCTURES) - set(ids):
        problems.append(f"Fee structure for unknown course: {cid}")
    for cid, st in FEE_STRUCTURES.items():
        if cid not in COURSE_BY_ID:
            continue
        _check_components(cid, st["components"], problems)
        tuition = [c for c in st["components"] if c["category"] == TUITION]
        if len(tuition) != 1:
            problems.append(f"{cid}: expected exactly one tuition component, found {len(tuition)}")
        elif tuition[0]["amount"] != COURSE_BY_ID[cid]["tuition"]:
            problems.append(f"{cid}: tuition differs from the course catalogue")

    for key, opt in ACCOMMODATION_OPTIONS.items():
        _check_components(f"accommodation:{key}", opt["components"], problems)
    for key, opt in TRANSPORT_OPTIONS.items():
        _check_components(f"transport:{key}", opt["components"], problems)
    _check_components("mess", MESS_COMPONENTS, problems)

    names, sids = set(), set()
    for s in SCHOLARSHIPS:
        where = f"scholarship {s['id']}"
        if s["id"] in sids:
            problems.append(f"Duplicate scholarship id: {s['id']}")
        sids.add(s["id"])
        if s["name"] in names:
            problems.append(f"Duplicate scholarship name: {s['name']}")
        names.add(s["name"])
        if s["kind"] not in _KINDS:
            problems.append(f"{where}: unknown kind {s['kind']!r}")
        if s["status"] not in _STATUSES:
            problems.append(f"{where}: unknown status {s['status']!r}")
        if s["award_type"] not in _AWARDS:
            problems.append(f"{where}: unknown award type {s['award_type']!r}")
        v = s["award_value"]
        if s["award_type"] == "percent_tuition" and not (isinstance(v, int) and 0 < v <= 100):
            problems.append(f"{where}: percentage must be between 1 and 100")
        if s["award_type"] == "fixed_amount" and not (isinstance(v, int) and v > 0):
            problems.append(f"{where}: fixed amount must be a positive whole number")
        if s["award_type"] == "none" and v is not None:
            problems.append(f"{where}: award value given without an award type")
        if s["deadline"]:
            try:
                date.fromisoformat(s["deadline"])
            except ValueError:
                problems.append(f"{where}: deadline is not an ISO date")
        rule = s["applies_to"]
        if rule is not None:
            for cid in rule["courses"] or []:
                if cid not in COURSE_BY_ID:
                    problems.append(f"{where}: links to unknown course {cid!r}")
            for lv in rule["levels"] or []:
                if lv not in LEVELS:
                    problems.append(f"{where}: unknown level {lv!r}")
            groups = {c["group"] for c in COURSES}
            for g in rule["groups"] or []:
                if g not in groups:
                    problems.append(f"{where}: unknown course group {g!r}")
            if not _courses_for(s):
                problems.append(f"{where}: does not apply to any course")
        for lv in (s["criteria"].get("min_pct") or {}):
            if lv not in LEVELS:
                problems.append(f"{where}: unknown level in criteria {lv!r}")
        if s["status"] == "illustrative":
            for field in ("eligibility", "documents", "renewal", "combination", "deadline", "applies_to"):
                if not s[field]:
                    problems.append(f"{where}: illustrative scholarship is missing {field}")
            if s["award_type"] == "none":
                problems.append(f"{where}: illustrative scholarship has no award")
        else:
            if s["award_value"] is not None:
                problems.append(f"{where}: unavailable details must not carry an invented award")
            if s["deadline"] or s["applies_to"] is not None:
                problems.append(f"{where}: unavailable details must not carry invented deadlines or courses")

    fa_ids = set()
    for fa in FINANCIAL_ASSISTANCE:
        if fa["id"] in fa_ids:
            problems.append(f"Duplicate financial assistance id: {fa['id']}")
        fa_ids.add(fa["id"])
        for field in ("name", "description", "status", "conditions", "documents"):
            if fa.get(field) is None:
                problems.append(f"financial assistance {fa['id']}: missing {field}")

    for pid, p in PAYMENT_PLANS.items():
        if p["instalments_per_year"] not in (1, 2):
            problems.append(f"payment plan {pid}: instalments_per_year must be 1 or 2")
        if "odd" not in p["due"] or (p["instalments_per_year"] == 2 and "even" not in p["due"]):
            problems.append(f"payment plan {pid}: missing due dates")

    wids, last = set(), 100
    for w in REFUND_POLICY["windows"]:
        if w["id"] in wids:
            problems.append(f"Duplicate refund window: {w['id']}")
        wids.add(w["id"])
        for k in ("tuition_pct", "other_pct"):
            if w[k] is not None and not 0 <= w[k] <= 100:
                problems.append(f"refund window {w['id']}: {k} out of range")
        if w["tuition_pct"] is not None:
            if w["tuition_pct"] > last:
                problems.append(f"refund window {w['id']}: refund rises as time passes")
            last = w["tuition_pct"]

    try:
        recs = [r["id"] for r in retrieval_records()]
    except Exception as exc:                          # report bad data instead of crashing the validator
        problems.append(f"Records could not be built from the data: {exc}")
    else:
        if len(recs) != len(set(recs)):
            problems.append("Duplicate retrieval record ids.")
    return problems


# ------------------------------------------------- AI-ready retrieval records
def _record(rid, rtype, text, data, *, course_id=None, status="illustrative"):
    return {"id": rid, "type": rtype, "course_id": course_id, "status": status, "text": text,
            "data": data, "notice": FEES_NOTICE}


def retrieval_records() -> list[dict]:
    """Flat, JSON-friendly records for a future retrieval layer. Nothing here calls any AI service."""
    out = []
    for c in COURSES:
        cid = c["id"]
        for comp in FEE_STRUCTURES[cid]["components"]:
            when = FREQUENCY_LABEL[comp["frequency"]].lower()
            ref = " Refundable deposit." if comp["refundable"] else ""
            out.append(_record(
                f"fee:{cid}:{comp['id']}", "fee_component",
                f"{c['name']}: {comp['label']} is {money(comp['amount'])}, charged {when}.{ref}",
                {k: comp[k] for k in ("id", "label", "category", "frequency", "amount", "refundable")},
                course_id=cid, status="illustrative" if comp["amount"] is not None else "details_unavailable"))
        s = cost_summary(cid)
        out.append(_record(
            f"fee-summary:{cid}", "fee_summary",
            f"{c['name']} ({s['years']} years): compulsory charges over the course {money(s['compulsory_total'])}, "
            f"plus refundable deposits {money(s['refundable_deposits_total'])}. Hostel, mess, transport and "
            f"optional expenses are not included.",
            {k: s[k] for k in ("years", "tuition_total", "compulsory_total", "recurring_compulsory_per_year",
                               "refundable_deposits_total", "cash_outlay", "by_year")},
            course_id=cid))
    for group, opts in (("accommodation", ACCOMMODATION_OPTIONS), ("transport", TRANSPORT_OPTIONS)):
        for key, opt in opts.items():
            for comp in opt["components"]:
                out.append(_record(
                    f"facility:{group}:{key}:{comp['id']}", "facility_fee",
                    f"{opt['label']}: {comp['label']} is {money(comp['amount'])}, charged "
                    f"{FREQUENCY_LABEL[comp['frequency']].lower()}.",
                    {k: comp[k] for k in ("id", "label", "category", "frequency", "amount", "refundable")},
                    status="illustrative" if comp["amount"] is not None else "details_unavailable"))
    for comp in MESS_COMPONENTS:
        out.append(_record(f"facility:mess:{comp['id']}", "facility_fee",
                           f"{comp['label']} is {money(comp['amount'])}, charged every year.",
                           {k: comp[k] for k in ("id", "label", "category", "frequency", "amount", "refundable")}))
    for s in SCHOLARSHIPS:
        courses = _courses_for(s)
        out.append(_record(
            f"scholarship:{s['id']}", "scholarship",
            f"{s['name']} ({s['kind']}): award {award_text(s)}. Eligibility: {s['eligibility'] or NOT_AVAILABLE}. "
            f"Deadline: {deadline_text(s)}.",
            {**s, "course_ids": courses}, status=s["status"]))
    for fa in FINANCIAL_ASSISTANCE:
        out.append(_record(f"assistance:{fa['id']}", "financial_assistance",
                           f"{fa['name']}: {fa['description']}", fa, status=fa["status"]))
    for pid, p in PAYMENT_PLANS.items():
        out.append(_record(f"payment-plan:{pid}", "payment_plan",
                           f"{p['name']}: {p['instalments_per_year']} instalment(s) a year after the "
                           f"admission payment.", {"id": pid, **p}))
    out.append(_record("payment-terms", "payment_terms", PAYMENT_TERMS["note"], dict(PAYMENT_TERMS),
                       status="details_unavailable"))
    for w in REFUND_POLICY["windows"]:
        out.append(_record(f"refund:{w['id']}", "refund_rule",
                           f"{w['label']}: {w['tuition_pct']}% of tuition and {w['other_pct']}% of other "
                           f"compulsory academic charges refundable. {w['note']}", dict(w)))
    for w in REFUND_POLICY["facility_windows"]:
        out.append(_record(f"refund:{w['id']}", "refund_rule",
                           f"Hostel, mess and transport, {w['label'].lower()}: refund "
                           f"{'not available' if w['pct'] is None else str(w['pct']) + '%'}. {w['note']}",
                           dict(w), status="details_unavailable" if w["pct"] is None else "illustrative"))
    for i, text in enumerate(REFUND_POLICY["withdrawal_rules"], 1):
        out.append(_record(f"refund:withdrawal-rule-{i}", "refund_rule", text, {"rule": text}))
    for i, cc in enumerate(REFUND_POLICY["cancellation_conditions"], 1):
        out.append(_record(f"refund:cancellation-{i}", "refund_rule",
                           f"{cc['case']}: {cc['outcome']}", dict(cc)))
    return out
