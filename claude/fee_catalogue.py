"""fee_catalogue.py - fee structures, scholarships, financial assistance, payment plans and refund policy.

ALL figures, rules, dates and scholarship terms here are ILLUSTRATIVE prototype data. They are not an
official fee schedule or scholarship offer. Nothing is copied from a real institution or a real
government scheme.

How it fits the existing project
  * Courses are NOT repeated here. Every record links to a stable course id from course_catalogue.py.
  * Annual tuition is read from COURSES[...]["tuition"] (single source), never typed again.
  * Information that is not available is stored as None and shown as "Not available". It is never guessed.
  * Calculations, validation and AI-ready records live in fee_logic.py.
"""
from data import COURSES
from course_catalogue import BSC_APPLIED, BSC_CORE, BTECH_CORE, BTECH_SPECIAL, OTHER

FEES_NOTICE = (
    "Note: This is illustrative prototype data, not an official fee schedule or scholarship offer. "
    "Actual fees, eligibility, availability, and refund conditions must be confirmed with the institution."
)

# Frequencies. The multiplier used by fee_logic: annual x years, per_semester x (2 x years), one_time x 1.
ANNUAL, SEMESTER, ONE_TIME = "annual", "per_semester", "one_time"
FREQUENCY_LABEL = {ANNUAL: "Every year", SEMESTER: "Every semester", ONE_TIME: "One time"}

# Component categories. tuition/academic/one_time = compulsory; optional is shown separately;
# hostel/mess/transport are facilities chosen by the student and are never part of the compulsory total.
TUITION, ACADEMIC, ONE_TIME_FEE, OPTIONAL = "tuition", "academic", "one_time", "optional"
HOSTEL, MESS, TRANSPORT = "hostel", "mess", "transport"
CATEGORY_LABEL = {
    TUITION: "Tuition",
    ACADEMIC: "Other compulsory academic charges",
    ONE_TIME_FEE: "One-time compulsory fees",
    OPTIONAL: "Optional expenses",
    HOSTEL: "Hostel",
    MESS: "Mess",
    TRANSPORT: "Transport",
}
COMPULSORY_CATEGORIES = (TUITION, ACADEMIC, ONE_TIME_FEE)
FACILITY_CATEGORIES = (HOSTEL, MESS, TRANSPORT)


def component(cid, label, category, frequency, amount, *, refundable=False, note=""):
    """One fee line. amount=None means the amount is not available (never guessed)."""
    return {"id": cid, "label": label, "category": category, "frequency": frequency,
            "amount": amount, "refundable": refundable, "note": note}


# ------------------------------------------------------------------ fee profiles
# Illustrative charges per profile. Tuition is not here: it comes from the course catalogue.
PROFILES = {
    "eng": dict(label="B.Tech programmes", development=12000, library=5000, exam=4000, insurance=1500,
                admission=5000, orientation=2000, deposit=10000, books=8000, training=10000),
    "sci": dict(label="B.Sc. programmes", development=6000, library=3000, exam=2500, insurance=1000,
                admission=3000, orientation=1500, deposit=5000, books=5000, training=6000),
    "ug": dict(label="Other undergraduate programmes", development=5000, library=2500, exam=2000,
               insurance=1000, admission=3000, orientation=1500, deposit=5000, books=4000, training=6000),
    "pg": dict(label="Postgraduate programmes", development=10000, library=4000, exam=3500, insurance=1500,
               admission=5000, orientation=2000, deposit=10000, books=6000, training=10000),
}

# Annual laboratory / practical fee per course (0 = the programme has no such charge).
LAB_FEE = {
    "btech-cse": 10000, "btech-it": 10000, "btech-aiml": 10000, "btech-ds": 10000,
    "btech-mech": 18000, "btech-civil": 15000, "btech-eee": 15000, "btech-ece": 15000,
    "btech-chem": 18000, "btech-engphy": 15000, "btech-aero": 20000, "btech-aerospace": 20000,
    "btech-biotech": 18000, "btech-robotics": 20000,
    "bsc-phy": 6000, "bsc-math": 0, "bsc-chem": 7000, "bsc-bio": 6000, "bsc-bot": 6000, "bsc-zoo": 6000,
    "bsc-stat": 3000, "bsc-cs": 5000, "bsc-biotech": 8000, "bsc-micro": 7000, "bsc-env": 5000,
    "bsc-ds": 5000,
    "bca": 4000, "bba": 0, "bcom": 0, "mca": 8000, "mba": 0,
}


def profile_for(course: dict) -> str:
    if course["level"] == "Postgraduate":
        return "pg"
    if course["id"].startswith("btech"):
        return "eng"
    if course["id"].startswith("bsc"):
        return "sci"
    return "ug"


def build_structure(course: dict) -> dict:
    """Fee components of one course. Tuition comes straight from the course record."""
    p = PROFILES[profile_for(course)]
    comps = [
        component("tuition", "Tuition fee", TUITION, ANNUAL, course["tuition"],
                  note="Taken from the course catalogue."),
        component("development", "Academic development fee", ACADEMIC, ANNUAL, p["development"]),
    ]
    lab = LAB_FEE[course["id"]]
    if lab:
        comps.append(component("lab", "Laboratory / practical fee", ACADEMIC, ANNUAL, lab))
    comps += [
        component("library", "Library and digital resources", ACADEMIC, ANNUAL, p["library"]),
        component("insurance", "Student accident insurance", ACADEMIC, ANNUAL, p["insurance"]),
        component("exam", "Examination fee", ACADEMIC, SEMESTER, p["exam"],
                  note="Charged every semester."),
        component("admission", "Admission processing fee", ONE_TIME_FEE, ONE_TIME, p["admission"],
                  note="Charged once, in the first year."),
        component("orientation", "Orientation and ID card", ONE_TIME_FEE, ONE_TIME, p["orientation"]),
        component("caution", "Caution deposit", ONE_TIME_FEE, ONE_TIME, p["deposit"], refundable=True,
                  note="Refundable. See the refund policy."),
        component("books", "Books and study material (estimate)", OPTIONAL, ANNUAL, p["books"],
                  note="Estimate for items bought separately."),
        component("training", "Placement and skill-training programme", OPTIONAL, ANNUAL, p["training"],
                  note="Optional add-on."),
        component("fieldvisit", "Industry visit / field trip charges", OPTIONAL, ANNUAL, None,
                  note="Charges depend on the trips planned each year. Not available."),
    ]
    return {"course_id": course["id"], "profile": profile_for(course), "components": comps}


FEE_STRUCTURES = {c["id"]: build_structure(c) for c in COURSES}

# ---------------------------------------------------------------- facilities
# Same for every course. Shown separately from compulsory fees; the student chooses what applies.
ACCOMMODATION_OPTIONS = {
    "none": {"label": "No hostel", "components": []},
    "double": {"label": "Hostel, double sharing", "components": [
        component("hostel-double-rent", "Hostel rent, double sharing", HOSTEL, ANNUAL, 60000,
                  note="Rent only. Mess charges are separate."),
        component("hostel-registration", "Hostel registration fee", HOSTEL, ONE_TIME, 2000),
        component("hostel-deposit", "Hostel security deposit", HOSTEL, ONE_TIME, 10000, refundable=True,
                  note="Refundable. See the refund policy."),
    ]},
    "single": {"label": "Hostel, single room", "components": [
        component("hostel-single-rent", "Hostel rent, single room", HOSTEL, ANNUAL, 85000,
                  note="Rent only. Mess charges are separate."),
        component("hostel-registration", "Hostel registration fee", HOSTEL, ONE_TIME, 2000),
        component("hostel-deposit", "Hostel security deposit", HOSTEL, ONE_TIME, 10000, refundable=True,
                  note="Refundable. See the refund policy."),
    ]},
}
MESS_COMPONENTS = [
    component("mess", "Mess (meals) charges", MESS, ANNUAL, 48000,
              note="Separate from hostel rent. Can be taken with or without the hostel."),
]
TRANSPORT_OPTIONS = {
    "none": {"label": "No college transport", "components": []},
    "z1": {"label": "Transport, zone 1 (up to 10 km)", "components": [
        component("transport-z1", "College transport, zone 1", TRANSPORT, ANNUAL, 18000)]},
    "z2": {"label": "Transport, zone 2 (10 to 20 km)", "components": [
        component("transport-z2", "College transport, zone 2", TRANSPORT, ANNUAL, 26000)]},
    "z3": {"label": "Transport, zone 3 (20 to 30 km)", "components": [
        component("transport-z3", "College transport, zone 3", TRANSPORT, ANNUAL, 34000)]},
    "far": {"label": "Transport, beyond 30 km", "components": [
        component("transport-far", "College transport, beyond 30 km", TRANSPORT, ANNUAL, None,
                  note="Availability and charges not available.")]},
}

# ------------------------------------------------------------- payment plans
ADMISSION_DUE = "Within 10 days of the college confirming the admission (illustrative)"
PAYMENT_PLANS = {
    "semester": {
        "name": "Semester-wise (two instalments a year)", "instalments_per_year": 2,
        "due": {"odd": "Before the odd semester starts (illustrative: by 15 July)",
                "even": "Before the even semester starts (illustrative: by 15 January)"},
    },
    "annual": {
        "name": "Annual (one payment a year)", "instalments_per_year": 1,
        "due": {"odd": "Before the academic year starts (illustrative: by 15 July)"},
    },
}
PAYMENT_TERMS = {
    "late_fee": None,                 # not available
    "grace_period_days": None,        # not available
    "payment_modes": None,            # not available; this website has no payment gateway
    "note": ("This website does not accept payments and does not confirm payments. Payment modes, late "
             "fees and grace periods are not available and must be confirmed with the institution."),
}

# ------------------------------------------------------------- scholarships
# Rules for combining institutional awards (illustrative).
COMBINATION_RULES = {
    "max_total_pct_of_tuition": 75,
    "applies_to": "Tuition only. Other charges, deposits and facilities are not reduced.",
    "notes": [
        "Awards in the same exclusive group cannot be held together. The larger one applies.",
        "Percentage awards are calculated on the annual tuition shown for the course.",
        "The total of all institutional awards cannot exceed 75% of annual tuition.",
        "Government or regional scheme benefits follow that scheme's own rules and are not calculated here.",
    ],
}
ALL_UG = ["Undergraduate"]
STEM_GROUPS = [BSC_CORE, BSC_APPLIED, BTECH_CORE, BTECH_SPECIAL]


def scholarship(sid, name, kind, *, status="illustrative", award_type="none", award_value=None,
                award_cap=None, applies_to=None, criteria=None, eligibility=None, deadline=None,
                deadline_note=None, documents=None, renewal=None, exclusive_group=None, combination=None):
    return {"id": sid, "name": name, "kind": kind, "status": status, "award_type": award_type,
            "award_value": award_value, "award_cap": award_cap, "applies_to": applies_to,
            "criteria": criteria or {}, "eligibility": eligibility, "deadline": deadline,
            "deadline_note": deadline_note, "documents": documents, "renewal": renewal,
            "exclusive_group": exclusive_group, "combination": combination}


_APPLY_BY = "2027-06-30"
_APPLY_NOTE = "Illustrative application deadline for the next intake. Confirm with the institution."
_ALL = {"levels": None, "groups": None, "courses": None}      # no restriction
_UNAVAILABLE_DOCS = ["Not available. Check the official notification of the scheme."]
_GOV_COMBINATION = ("Not available. Depends on the scheme's own rules. Confirm with the institution and the "
                    "scheme administrator before accepting more than one benefit.")

SCHOLARSHIPS = [
    scholarship(
        "merit-a", "Academic Excellence Scholarship (Tier A)", "merit",
        award_type="percent_tuition", award_value=50, award_cap=75000, applies_to=_ALL,
        criteria={"min_pct": {"Undergraduate": 90, "Postgraduate": 80}},
        eligibility="Class 12 aggregate of 90% or more (undergraduate), or bachelor's-degree aggregate of "
                    "80% or more (postgraduate).",
        deadline=_APPLY_BY, deadline_note=_APPLY_NOTE,
        documents=["Class 12 or bachelor's mark sheet", "Admission confirmation", "Government photo ID"],
        renewal="Renewed each year if the student keeps a 75% year-end aggregate and 75% attendance.",
        exclusive_group="merit-tier",
        combination="Cannot be held with the Tier B merit scholarship. Can be combined with other awards "
                    "within the overall 75% limit."),
    scholarship(
        "merit-b", "Academic Excellence Scholarship (Tier B)", "merit",
        award_type="percent_tuition", award_value=25, award_cap=40000, applies_to=_ALL,
        criteria={"min_pct": {"Undergraduate": 80, "Postgraduate": 70}},
        eligibility="Class 12 aggregate of 80% or more (undergraduate), or bachelor's-degree aggregate of "
                    "70% or more (postgraduate). Applicants who qualify for Tier A receive Tier A.",
        deadline=_APPLY_BY, deadline_note=_APPLY_NOTE,
        documents=["Class 12 or bachelor's mark sheet", "Admission confirmation", "Government photo ID"],
        renewal="Renewed each year if the student keeps a 70% year-end aggregate and 75% attendance.",
        exclusive_group="merit-tier",
        combination="Cannot be held with the Tier A merit scholarship. Can be combined with other awards "
                    "within the overall 75% limit."),
    scholarship(
        "need-based", "Need-Based Fee Concession", "need",
        award_type="percent_tuition", award_value=30, award_cap=50000, applies_to=_ALL,
        criteria={"max_family_income": 300000, "min_pct": {"Undergraduate": 50, "Postgraduate": 50}},
        eligibility="Annual family income up to ₹3,00,000 and at least 50% in the qualifying examination.",
        deadline=_APPLY_BY, deadline_note=_APPLY_NOTE,
        documents=["Family income certificate", "Qualifying mark sheet", "Government photo ID",
                   "Proof of residence"],
        renewal="Income is re-verified every year. The student must keep 60% year-end marks and 75% attendance.",
        combination="Can be combined with merit, sports and achievement awards within the overall 75% limit."),
    scholarship(
        "sports", "Sports Excellence Scholarship", "sports",
        award_type="percent_tuition", award_value=20, award_cap=35000, applies_to=_ALL,
        eligibility="Represented the state or country in an organised sport in the last two years.",
        deadline=_APPLY_BY, deadline_note=_APPLY_NOTE,
        documents=["Participation or medal certificate", "Letter from the sports body", "Government photo ID"],
        renewal="Renewed each year if the student keeps representing the college team and 75% attendance.",
        combination="Can be combined with merit and need-based awards within the overall 75% limit."),
    scholarship(
        "achievement", "Olympiad and Innovation Achievement Award", "achievement",
        award_type="fixed_amount", award_value=25000, applies_to={"levels": ALL_UG, "groups": STEM_GROUPS,
                                                                  "courses": None},
        eligibility="Rank or award in a national-level science or mathematics olympiad, science fair or "
                    "hackathon. Open to undergraduate B.Sc. and B.Tech students.",
        deadline=_APPLY_BY, deadline_note=_APPLY_NOTE,
        documents=["Award or rank certificate", "Event details", "Admission confirmation"],
        renewal="Paid for the first year. Renewed if the student keeps a 70% year-end aggregate.",
        combination="Can be combined with other awards within the overall 75% limit."),
    scholarship(
        "pg-merit", "Postgraduate Merit Award", "merit",
        award_type="fixed_amount", award_value=20000, applies_to={"levels": None, "groups": None,
                                                                  "courses": ["mca", "mba"]},
        criteria={"min_pct": {"Postgraduate": 60}},
        eligibility="MCA and MBA applicants with at least 60% in the bachelor's degree who rank in the top "
                    "10% of the admitted batch.",
        deadline=_APPLY_BY, deadline_note=_APPLY_NOTE,
        documents=["Bachelor's mark sheets", "Admission confirmation"],
        renewal="Renewed for the second year if the student keeps a 65% aggregate in year one.",
        combination="Can be combined with other awards within the overall 75% limit."),
    scholarship(
        "inclusion", "Inclusion Support Concession", "need",
        award_type="percent_tuition", award_value=25, award_cap=40000, applies_to=_ALL,
        eligibility="Students with a disability certificate issued by a competent authority.",
        deadline=_APPLY_BY, deadline_note=_APPLY_NOTE,
        documents=["Disability certificate", "Admission confirmation", "Government photo ID"],
        renewal="Renewed each year with 75% attendance and progression to the next year.",
        combination="Can be combined with other awards within the overall 75% limit."),
    # Government and regional entries. Deliberately generic: no real scheme details are stated.
    scholarship(
        "gov-central", "Central government scholarship schemes", "government", status="details_unavailable",
        eligibility=None, documents=_UNAVAILABLE_DOCS, renewal=None, combination=_GOV_COMBINATION,
        deadline_note="Not available. Deadlines are set by each scheme."),
    scholarship(
        "gov-state", "State government scholarships and fee reimbursement", "regional",
        status="details_unavailable", eligibility=None, documents=_UNAVAILABLE_DOCS, renewal=None,
        combination=_GOV_COMBINATION, deadline_note="Not available. Deadlines are set by each scheme."),
    scholarship(
        "gov-welfare", "Category-based and welfare scholarships (government or regional)", "government",
        status="details_unavailable", eligibility=None, documents=_UNAVAILABLE_DOCS, renewal=None,
        combination=_GOV_COMBINATION, deadline_note="Not available. Deadlines are set by each scheme."),
]

# --------------------------------------------------------- financial assistance
FINANCIAL_ASSISTANCE = [
    {"id": "fa-instalments", "name": "Instalment payment plans", "status": "illustrative",
     "description": "Tuition and other charges can be paid semester by semester or once a year. "
                    "See the payment schedule for the instalment amounts of each course.",
     "eligibility": "Open to all admitted students.", "amount_info": "No separate charge listed.",
     "how_to_apply": "Choose the plan when confirming admission.",
     "documents": [], "conditions": ["Late fee and grace period: not available."]},
    {"id": "fa-loan", "name": "Education loan facilitation", "status": "details_unavailable",
     "description": "The institution may provide fee structure letters and bonafide certificates to "
                    "support an education-loan application with a bank of the student's choice.",
     "eligibility": None, "amount_info": None,
     "how_to_apply": "Not available. Contact the admissions office.",
     "documents": ["Admission confirmation", "Fee structure letter (from the institution)"],
     "conditions": ["Partner banks, interest rates and loan limits: not available.",
                    "Loan approval is decided only by the lending bank."]},
    {"id": "fa-hardship", "name": "Emergency hardship support", "status": "illustrative",
     "description": "A review committee may allow a deferred instalment for a student whose family faces "
                    "a sudden financial hardship.",
     "eligibility": "Enrolled students with a documented hardship.",
     "amount_info": "Maximum deferral period and any support amount: not available.",
     "how_to_apply": "Written request to the college office before the instalment due date.",
     "documents": ["Written request", "Supporting documents for the hardship"],
     "conditions": ["Each case is reviewed individually.", "A deferral does not cancel the fee."]},
    {"id": "fa-workstudy", "name": "Campus work-study programme", "status": "illustrative",
     "description": "Part-time campus work (library, laboratories, office) for students who need income "
                    "while studying.",
     "eligibility": "Enrolled students in good academic standing.",
     "amount_info": "Up to 10 hours a week (illustrative). Hourly rate: not available.",
     "how_to_apply": "Apply to the student affairs office after the first semester.",
     "documents": ["Application form", "Recent mark sheet"],
     "conditions": ["Work hours must not clash with classes.", "Availability depends on openings."]},
]

# ------------------------------------------------------------- refund policy
# Percentages are of the tuition and other compulsory academic charges paid for the period.
REFUND_POLICY = {
    "status": "illustrative",
    "windows": [
        {"id": "not-approved", "label": "Registration not approved by the college",
         "tuition_pct": 100, "other_pct": 100,
         "note": "Everything paid is returned, including one-time fees."},
        {"id": "30-before", "label": "30 or more days before the programme starts",
         "tuition_pct": 100, "other_pct": 100,
         "note": "The admission processing fee is not refunded."},
        {"id": "1-29-before", "label": "1 to 29 days before the programme starts",
         "tuition_pct": 90, "other_pct": 90,
         "note": "The admission processing fee is not refunded."},
        {"id": "day-1-14", "label": "Day 1 to day 14 after the programme starts",
         "tuition_pct": 70, "other_pct": 50,
         "note": "Applies to the first instalment paid."},
        {"id": "day-15-30", "label": "Day 15 to day 30 after the programme starts",
         "tuition_pct": 50, "other_pct": 25,
         "note": "Applies to the first instalment paid."},
        {"id": "after-30", "label": "After day 30 of the programme",
         "tuition_pct": 0, "other_pct": 0,
         "note": "No refund for the current period. Instalments not yet due are cancelled if the "
                 "withdrawal is recorded before their due date."},
    ],
    "facility_windows": [
        {"id": "fac-before", "label": "Before moving into the hostel or using the transport",
         "pct": 100, "note": "Registration fee is not refunded."},
        {"id": "fac-after", "label": "After moving in or using the service",
         "pct": None, "note": "Refund of unused months: not available."},
    ],
    "refundable_items": [
        "Caution deposit (all courses).",
        "Hostel security deposit (hostel residents).",
    ],
    "deposit_conditions": ("Deposits are returned after the student leaves, once dues are cleared and any "
                           "damage or loss is deducted."),
    "non_refundable_items": [
        "Admission processing fee (except when the college does not approve the registration).",
        "Orientation and ID card charge once issued.",
        "Examination fees once the semester's examination process has started.",
        "Hostel registration fee.",
    ],
    "withdrawal_rules": [
        "A withdrawal must be requested in writing to the college.",
        "The date the college receives the request decides the refund window.",
        "Refunds are calculated on amounts actually paid.",
        "Scholarship benefits for a withdrawn period may be adjusted. Details: not available.",
    ],
    "cancellation_conditions": [
        {"case": "The college does not approve the registration",
         "outcome": "Full refund of everything paid."},
        {"case": "The college cancels or does not start the programme",
         "outcome": "Full refund of everything paid, including one-time fees."},
        {"case": "Documents or eligibility cannot be verified",
         "outcome": "Refund of amounts paid, less the admission processing fee."},
        {"case": "The student withdraws", "outcome": "Refund as per the withdrawal windows above."},
        {"case": "Removal from the programme for disciplinary reasons",
         "outcome": "No refund for the current period. Deposits are returned after dues and deductions."},
    ],
    "processing_time_days": None,     # not available
    "refund_mode": None,              # not available
}
