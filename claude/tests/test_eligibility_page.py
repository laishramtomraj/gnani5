"""Tests for the Eligibility Checker page's logic (eligibility_service.py). No Streamlit needed.

Run from the project folder (Windows or Mac/Linux):
    python -m unittest discover -s tests -v
"""
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import course_service  # noqa: E402
import eligibility_service as service  # noqa: E402
import registration_schema as schema  # noqa: E402
import registration_service  # noqa: E402

MEETS, NOT_MET, INSUFFICIENT = "meets", "does_not_meet", "insufficient"
ALL_COURSES = course_service.list_courses()


def answers_for(course, pct="75", subjects=("Physics", "Chemistry", "Mathematics"), **extra):
    route = service.routes_for(course)[0]
    base = {"route": route, "percentage": pct, "result_status": schema.RESULT_DECLARED,
            "subjects": list(subjects), "other_subjects": ""}
    base.update(extra)
    return base


class CheckOutcomeTests(unittest.TestCase):
    def test_course_with_checkable_subjects_meets(self):
        r = service.check_course("bsc-phy", answers_for(course_service.get_course("bsc-phy")))
        self.assertTrue(r["valid"])
        self.assertEqual(r["outcome"], MEETS)
        self.assertEqual(r["unmet"], [])
        self.assertEqual(r["unverified"], [])
        self.assertGreaterEqual(len(r["met"]), 3)

    def test_percentage_below_the_stored_minimum(self):
        r = service.check_course("bsc-phy", answers_for(course_service.get_course("bsc-phy"), pct="30"))
        self.assertEqual(r["outcome"], NOT_MET)
        self.assertTrue(any("below the stored minimum" in c["detail"] for c in r["unmet"]))

    def test_percentage_exactly_at_the_minimum_passes(self):
        course = course_service.get_course("bsc-phy")
        r = service.check_course("bsc-phy", answers_for(course, pct=str(course["min_pct"])))
        self.assertEqual(r["outcome"], MEETS)

    def test_missing_required_subject(self):
        r = service.check_course("bsc-phy", answers_for(course_service.get_course("bsc-phy"), subjects=("Physics",)))
        self.assertEqual(r["outcome"], NOT_MET)
        self.assertTrue(any("Mathematics" in c["detail"] for c in r["unmet"]))

    def test_extra_subjects_typed_in_the_other_box_count(self):
        course = course_service.get_course("bsc-phy")
        r = service.check_course("bsc-phy", answers_for(course, subjects=("Physics",), other_subjects="Mathematics"))
        self.assertEqual(r["outcome"], MEETS)

    def test_any_stream_course_needs_no_subjects(self):
        course = course_service.get_course("bca")
        self.assertFalse(service.inputs_needed(course, "class12")["subjects"])
        self.assertEqual(service.check_course("bca", answers_for(course, subjects=()))["outcome"], MEETS)

    def test_free_text_subject_wording_is_never_guessed(self):
        course = course_service.get_course("btech-cse")
        r = service.check_course("btech-cse", answers_for(course, pct="95"))
        self.assertEqual(r["outcome"], INSUFFICIENT)
        self.assertTrue(any("confirmation" in c["detail"] for c in r["unverified"]))

    def test_diploma_and_degree_routes_need_the_college_to_confirm(self):
        course = course_service.get_course("btech-cse")
        r = service.check_course("btech-cse", {"route": schema.ROUTE_DIPLOMA})
        self.assertEqual(r["outcome"], INSUFFICIENT)
        pg = course_service.get_course("mca")
        r = service.check_course("mca", answers_for(pg, pct="80"))
        self.assertIn(r["outcome"], (INSUFFICIENT, MEETS))
        self.assertNotEqual(service.check_course("mca", answers_for(pg, pct="5"))["outcome"], MEETS)

    def test_awaited_result_cannot_be_compared(self):
        course = course_service.get_course("bsc-phy")
        r = service.check_course("bsc-phy", answers_for(course, pct="95", result_status=schema.RESULT_AWAITED))
        self.assertEqual(r["outcome"], INSUFFICIENT)

    def test_blank_answers_never_give_a_positive_result(self):
        for course in ALL_COURSES:
            for route in service.routes_for(course):
                r = service.check_course(course["id"], {"route": route})
                self.assertTrue(r["valid"], course["id"])
                self.assertNotEqual(r["outcome"], MEETS, f"{course['id']} / {route}")

    def test_wrong_route_for_the_course(self):
        r = service.check_course("bsc-phy", {"route": schema.ROUTE_DEGREE})
        self.assertFalse(r["valid"])
        self.assertIn("route", r["errors"])

    def test_missing_course_or_route(self):
        self.assertIn("course", service.check_course(None, {})["errors"])
        self.assertIn("course", service.check_course("no-such-course", {})["errors"])
        self.assertIn("route", service.check_course("bsc-phy", {})["errors"])
        self.assertIn("route", service.check_course("bsc-phy", None)["errors"])


class ValidationTests(unittest.TestCase):
    COURSE = course_service.get_course("bsc-phy")

    def test_invalid_percentages_are_rejected_without_a_result(self):
        for bad in ("abc", "-1", "101", "1e2", "nan", "7,5", "", None, True):
            r = service.check_course("bsc-phy", answers_for(self.COURSE, pct=bad))
            if bad in ("", None):
                self.assertTrue(r["valid"], bad)                    # blank = missing, not invalid
                self.assertEqual(r["outcome"], INSUFFICIENT, bad)
            else:
                self.assertFalse(r["valid"], bad)
                self.assertIsNone(r["outcome"], bad)
                self.assertIn("percentage", r["errors"], bad)

    def test_percentage_formats(self):
        for good, expected in (("75", 75.0), (" 75.5 ", 75.5), ("75%", 75.0), (0, 0.0), (100, 100.0)):
            self.assertEqual(service.parse_percentage(good), (expected, None))
        self.assertEqual(service.parse_percentage("  "), (None, None))

    def test_unknown_subject_or_status_is_rejected(self):
        self.assertIn("subjects", service.check_course("bsc-phy", answers_for(self.COURSE, subjects=("Astrology",)))["errors"])
        self.assertIn("result_status", service.check_course("bsc-phy", answers_for(self.COURSE, result_status="Maybe"))["errors"])

    def test_overlong_other_subjects_text(self):
        r = service.check_course("bsc-phy", answers_for(self.COURSE, other_subjects="x" * 201))
        self.assertIn("other_subjects", r["errors"])

    def test_inapplicable_answers_are_ignored(self):
        course = course_service.get_course("bca")
        a = answers_for(course, subjects=("Astrology",), other_subjects="x" * 500)     # BCA does not use subjects
        self.assertEqual(service.check_course("bca", a)["outcome"], MEETS)


class FormInputTests(unittest.TestCase):
    def test_the_form_only_asks_what_can_change_the_result(self):
        phy = service.inputs_needed(course_service.get_course("bsc-phy"), "class12")
        self.assertTrue(all([phy["percentage"], phy["result_status"], phy["subjects"], phy["other_subjects"]]))
        cse = service.inputs_needed(course_service.get_course("btech-cse"), "class12")
        self.assertTrue(cse["percentage"] and not cse["subjects"])
        dip = service.inputs_needed(course_service.get_course("btech-cse"), "diploma")
        self.assertFalse(any(dip.values()))
        pg = service.inputs_needed(course_service.get_course("mca"), "degree")
        self.assertTrue(pg["percentage"] and not pg["subjects"] and not pg["result_status"])

    def test_every_course_can_be_described_and_checked(self):
        for course in ALL_COURSES:
            lines = service.describe_requirements(course)
            self.assertTrue(lines and lines[0].startswith("You can apply with:"), course["id"])
            self.assertTrue(any(line.startswith("Minimum marks:") for line in lines), course["id"])
            for route in service.routes_for(course):
                self.assertTrue(service.check_course(course["id"], {"route": route})["valid"], course["id"])

    def test_stored_wording_is_quoted_not_reinterpreted(self):
        course = course_service.get_course("btech-cse")
        text = " ".join(service.describe_requirements(course))
        self.assertIn(course["class12"], text)
        self.assertIn("needs the college's confirmation", text)


class ConsistencyWithRegistrationTests(unittest.TestCase):
    """This page must give the same outcome as the registration review for the same answers."""

    def registration_data(self, course, pct, subjects):
        year = __import__("datetime").date.today().year
        return {"full_name": "Test Student", "email": "t@example.com", "mobile": "9876543210",
                "qualification_route": schema.ROUTE_CLASS12, "class12_board": "CBSE", "class12_stream": "Science",
                "class12_subjects": list(subjects), "class12_result_status": schema.RESULT_DECLARED,
                "class12_percentage": pct, "class12_year": year,
                "declaration_accurate": True, "privacy_acknowledged": True}

    def test_same_outcome_as_the_registration_review(self):
        for course in ALL_COURSES:
            if schema.ROUTE_CLASS12 not in service.routes_for(course) or course.get("degree"):
                continue
            for pct in (30, 80):
                subjects = ("Physics", "Chemistry", "Mathematics")
                review = registration_service.review_registration(course["id"], self.registration_data(course, pct, subjects))
                self.assertEqual(review["errors"], {}, course["id"])
                page = service.check_course(course["id"], {"route": schema.ROUTE_CLASS12, "percentage": str(pct),
                                                           "result_status": schema.RESULT_DECLARED,
                                                           "subjects": list(subjects), "other_subjects": ""})
                self.assertEqual(page["outcome"], review["eligibility"]["outcome"], f"{course['id']} at {pct}%")


class ResultContentTests(unittest.TestCase):
    def result(self, **kw):
        course = course_service.get_course("bsc-phy")
        return service.check_course("bsc-phy", answers_for(course, **kw))

    def test_result_has_explanation_next_steps_and_the_notice(self):
        for r in (self.result(), self.result(pct="1"), self.result(subjects=()),):
            self.assertTrue(r["explanation"])
            self.assertGreaterEqual(len(r["next_steps"]), 2)
            self.assertEqual(r["notice"], service.NOTICE)
            self.assertIn("made only by the college", " ".join(r["next_steps"]))

    def test_notice_text_is_exact(self):
        self.assertEqual(service.NOTICE,
                         "Eligibility results are indicative only and are based on the illustrative criteria available in "
                         "this prototype. Meeting the listed criteria does not guarantee admission. Please confirm the "
                         "official requirements with the college.")

    def test_no_misleading_wording(self):
        text = " ".join(str(v) for r in (self.result(), self.result(pct="1")) for v in r.values()).lower()
        for banned in ("admission guaranteed", "officially eligible", "admission confirmed", "you are admitted"):
            self.assertNotIn(banned, text)

    def test_not_met_next_steps_do_not_imply_another_course_is_available(self):
        steps = " ".join(self.result(pct="1")["next_steps"])
        self.assertIn("does not mean any course is available to you", steps)


class PrivacyTests(unittest.TestCase):
    def test_service_writes_and_logs_nothing(self):
        source = (ROOT / "eligibility_service.py").read_text(encoding="utf-8")
        for forbidden in ("sqlite3", "registration_db", "open(", "write_text", ".write(", "logging", "print(",
                          "requests", "st.session_state"):
            self.assertNotIn(forbidden, source, forbidden)

    def test_checking_creates_no_files_and_touches_no_registration_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "never_created.db"
            old = os.environ.get("COLLEGE_REGISTRATIONS_DB")
            os.environ["COLLEGE_REGISTRATIONS_DB"] = str(db)
            try:
                service.check_course("bsc-phy", answers_for(course_service.get_course("bsc-phy")))
            finally:
                if old is None:
                    os.environ.pop("COLLEGE_REGISTRATIONS_DB", None)
                else:
                    os.environ["COLLEGE_REGISTRATIONS_DB"] = old
            self.assertFalse(db.exists())

    def test_nothing_personal_is_requested(self):
        page = (ROOT / "views" / "eligibility.py").read_text(encoding="utf-8").lower()
        for field in ("full name", "email", "mobile", "phone", "aadhaar", "password", "date of birth"):
            self.assertNotIn(f'"{field}', page, field)


if __name__ == "__main__":
    unittest.main()
