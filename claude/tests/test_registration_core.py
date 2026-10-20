"""Tests for the registration rules and storage (no browser needed).

Run from the project folder (Windows or Mac/Linux):
    python -m unittest discover -s tests -v
"""
import json
import logging
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import course_service  # noqa: E402
import eligibility  # noqa: E402
import registration_db  # noqa: E402
import registration_schema as schema  # noqa: E402
import registration_service as service  # noqa: E402
import registration_validation as validation  # noqa: E402

THIS_YEAR = date.today().year


def valid_data(**changes):
    data = dict(
        full_name="Asha Rao", email="asha@example.com", mobile="98765 43210", date_of_birth=date(2007, 5, 1),
        gender=None, state=None, qualification_route="class12", class10_percentage=88.0,
        class12_board="CBSE", class12_stream="Science", class12_subjects=["Physics", "Chemistry", "Mathematics"],
        class12_other_subjects="", class12_result_status="Declared", class12_percentage=82.5, class12_year=THIS_YEAR,
        declaration_accurate=True, privacy_acknowledged=True,
    )
    data.update(changes)
    return data


def course_with_class12_text(text):
    return next(c for c in course_service.list_courses() if c.get("class12") == text)


class SchemaAndCourseData(unittest.TestCase):
    def test_routes_follow_the_course_record(self):
        for c in course_service.list_courses():
            routes = schema.qualification_routes(c)
            if c["level"] == "Postgraduate":
                self.assertEqual(routes, ["degree"], c["id"])
            else:
                self.assertEqual("diploma" in routes, bool(c["diploma"]), c["id"])
                self.assertEqual(routes[0], "class12")

    def test_course_lookup_and_summary_use_existing_data(self):
        cse = course_service.get_course("btech-cse")
        self.assertIs(course_service.get_course_by_name(cse["name"]), cse)
        summary = course_service.course_summary("btech-cse")
        self.assertEqual(summary["annual_tuition"], cse["tuition"])
        self.assertEqual(summary["total_tuition"], cse["tuition"] * cse["years"])
        self.assertEqual(summary["department"], "Computer Science and Engineering")
        self.assertIsNone(summary["seat_availability"], "availability is not recorded, so it must stay None")
        self.assertIsNone(course_service.get_course("no-such-course"))
        self.assertIsNone(course_service.course_summary("no-such-course"))

    def test_every_course_has_a_summary(self):
        for c in course_service.list_courses():
            self.assertIsNotNone(course_service.course_summary(c["id"]), c["id"])


class Validation(unittest.TestCase):
    cse = course_service.get_course("btech-cse")

    def errors(self, course=None, **changes):
        return validation.validate_registration(course or self.cse, valid_data(**changes))

    def test_valid_registration_has_no_errors(self):
        self.assertEqual(self.errors(), {})

    def test_required_fields(self):
        errs = validation.validate_registration(self.cse, {})
        for field in ("full_name", "email", "mobile", "qualification_route", "declaration_accurate", "privacy_acknowledged"):
            self.assertIn(field, errs)
        self.assertIn("course_id", validation.validate_registration(None, valid_data()))

    def test_optional_fields_may_be_empty(self):
        self.assertEqual(self.errors(date_of_birth=None, gender=None, state=None, class10_percentage=None,
                                     class12_other_subjects=None, entrance_exam_details=None), {})

    def test_email(self):
        for bad in ("a@b", "asha.example.com", "asha@@example.com", "a..b@example.com", "asha@example..com", " "):
            self.assertIn("email", self.errors(email=bad), bad)
        self.assertEqual(self.errors(email="  ASHA.Rao+test@Example.COM "), {})

    def test_mobile(self):
        for good in ("9876543210", "+91 98765 43210", "098765-43210", "919876543210"):
            self.assertEqual(self.errors(mobile=good), {}, good)
        for bad in ("12345", "5987654321", "98765432101", "abcdefghij"):
            self.assertIn("mobile", self.errors(mobile=bad), bad)
        self.assertEqual(validation.normalize_mobile("98765 43210"), "+919876543210")

    def test_name(self):
        self.assertEqual(self.errors(full_name="आशा शर्मा"), {})            # Hindi names are accepted
        self.assertEqual(self.errors(full_name="Mary-Ann O'Neil Jr."), {})
        for bad in ("A", "R2D2", "<script>", "x" * 101, "12345"):
            self.assertIn("full_name", self.errors(full_name=bad), bad)

    def test_percentages_and_years(self):
        for bad in (-1, 100.5, 101, "abc", True):
            self.assertIn("class12_percentage", self.errors(class12_percentage=bad), repr(bad))
        self.assertEqual(self.errors(class12_percentage=0), {})
        self.assertEqual(self.errors(class12_percentage=100), {})
        self.assertIn("class10_percentage", self.errors(class10_percentage=150))
        self.assertIn("class12_year", self.errors(class12_year=THIS_YEAR + 5))
        self.assertIn("class12_year", self.errors(class12_year=1980))

    def test_date_of_birth(self):
        self.assertIn("date_of_birth", self.errors(date_of_birth=date.today() + timedelta(days=1)))
        self.assertIn("date_of_birth", self.errors(date_of_birth=date(THIS_YEAR - 10, 1, 1)))
        self.assertIn("date_of_birth", self.errors(date_of_birth=date(1950, 1, 1)))

    def test_class12_route_needs_academic_fields(self):
        errs = self.errors(class12_board=None, class12_stream=None, class12_subjects=[], class12_year=None,
                           class12_percentage=None)
        for field in ("class12_board", "class12_stream", "class12_subjects", "class12_year", "class12_percentage"):
            self.assertIn(field, errs)

    def test_awaited_result_does_not_need_a_percentage(self):
        self.assertEqual(self.errors(class12_result_status="Awaited", class12_percentage=None), {})

    def test_diploma_route_only_when_course_has_one(self):
        diploma = dict(valid_data(), qualification_route="diploma", diploma_branch="Mechanical",
                       diploma_percentage=70, diploma_year=THIS_YEAR)
        self.assertEqual(validation.validate_registration(self.cse, diploma), {})
        no_diploma = next(c for c in course_service.list_courses() if not c["diploma"] and c["level"] == "Undergraduate")
        self.assertIn("qualification_route", validation.validate_registration(no_diploma, diploma))
        incomplete = dict(diploma, diploma_branch=None, diploma_percentage=None, diploma_year=None)
        errs = validation.validate_registration(self.cse, incomplete)
        for field in ("diploma_branch", "diploma_percentage", "diploma_year"):
            self.assertIn(field, errs)

    def test_degree_route_for_postgraduate(self):
        mca = course_service.get_course("mca")
        data = valid_data(qualification_route="degree", degree_name="BCA", degree_discipline="Computer Applications",
                          degree_percentage=65, degree_year=THIS_YEAR - 1)
        self.assertEqual(validation.validate_registration(mca, data), {})
        self.assertIn("qualification_route", validation.validate_registration(mca, valid_data()))
        errs = validation.validate_registration(mca, dict(data, degree_name=None, degree_percentage=None))
        self.assertIn("degree_name", errs)
        self.assertIn("degree_percentage", errs)

    def test_stale_answers_from_another_route_are_not_kept(self):
        data = valid_data(diploma_branch="Mechanical", diploma_percentage=70, diploma_year=THIS_YEAR)
        cleaned = validation.normalize(data)
        self.assertIsNone(cleaned["diploma_branch"])
        self.assertIsNone(cleaned["diploma_percentage"])


class Eligibility(unittest.TestCase):
    def test_subject_text_parser(self):
        parse = eligibility.parse_subject_requirement
        self.assertEqual(parse("Physics, Chemistry and Mathematics"), ("all", ["Physics", "Chemistry", "Mathematics"]))
        self.assertEqual(parse("Physics and Mathematics"), ("all", ["Physics", "Mathematics"]))
        self.assertEqual(parse("Mathematics"), ("all", ["Mathematics"]))
        self.assertEqual(parse("Biology and Chemistry"), ("all", ["Biology", "Chemistry"]))
        self.assertEqual(parse("Class 12 in any stream"), ("any", []))
        for vague in (
            "Physics, Chemistry and Mathematics or Biology",
            "Biology (Botany) and Chemistry",
            "Mathematics or other specified subjects",
            "Chemistry and Physics, plus Mathematics or Biology",
            "Biology and Chemistry, with Physics or Mathematics",
            "Any science stream (Physics, Chemistry, Biology or Mathematics)",
            "An accepted stream; Commerce preferred (accepted streams to be confirmed by the college)",
            "Physics, Mathematics and one of Chemistry / Computer Science / a technical vocational subject "
            "(programme-specific subject to be confirmed by the college)",
            "", None,
        ):
            self.assertEqual(parse(vague)[0], "unknown", vague)

    def check(self, course, **changes):
        return eligibility.check_eligibility(course, validation.normalize(valid_data(**changes)))

    def test_every_stored_subject_text_gets_a_defined_result(self):
        for c in course_service.list_courses():
            if c["level"] == "Undergraduate":
                result = self.check(c)
                self.assertIn(result["outcome"], (eligibility.OUTCOME_MEETS, eligibility.OUTCOME_NOT_MET,
                                                  eligibility.OUTCOME_INSUFFICIENT))

    def test_percentage_below_stored_minimum_does_not_meet(self):
        cse = course_service.get_course("btech-cse")
        result = self.check(cse, class12_percentage=cse["min_pct"] - 0.01)
        self.assertEqual(result["outcome"], eligibility.OUTCOME_NOT_MET)
        self.assertTrue(any("below" in c["detail"] for c in result["unmet"]))

    def test_percentage_at_minimum_is_not_unmet(self):
        cse = course_service.get_course("btech-cse")
        result = self.check(cse, class12_percentage=cse["min_pct"])
        self.assertNotEqual(result["outcome"], eligibility.OUTCOME_NOT_MET)

    def test_vague_subject_text_is_never_called_a_match(self):
        cse = course_service.get_course("btech-cse")            # stored subject text is vague
        result = self.check(cse)
        self.assertEqual(result["outcome"], eligibility.OUTCOME_INSUFFICIENT)
        self.assertTrue(result["unverified"])

    def test_plain_subject_list_can_meet(self):
        course = course_with_class12_text("Physics and Mathematics")
        self.assertEqual(self.check(course, class12_subjects=["Physics", "Mathematics"])["outcome"], eligibility.OUTCOME_MEETS)
        missing = self.check(course, class12_subjects=["Physics", "Chemistry"])
        self.assertEqual(missing["outcome"], eligibility.OUTCOME_NOT_MET)
        self.assertIn("Mathematics", missing["unmet"][0]["detail"])
        extra = self.check(course, class12_subjects=["Physics"], class12_other_subjects="mathematics, Art")
        self.assertEqual(extra["outcome"], eligibility.OUTCOME_MEETS)

    def test_any_stream_course_meets_with_enough_marks(self):
        course = course_with_class12_text("Class 12 in any stream")
        self.assertEqual(self.check(course, class12_stream="Commerce", class12_subjects=["Accountancy"],
                                    class12_percentage=course["min_pct"] + 5)["outcome"], eligibility.OUTCOME_MEETS)

    def test_result_awaited_is_insufficient_not_ineligible(self):
        course = course_with_class12_text("Physics and Mathematics")
        result = self.check(course, class12_result_status="Awaited", class12_percentage=None,
                            class12_subjects=["Physics", "Mathematics"])
        self.assertEqual(result["outcome"], eligibility.OUTCOME_INSUFFICIENT)

    def test_diploma_route_is_never_auto_confirmed(self):
        cse = course_service.get_course("btech-cse")
        data = validation.normalize(valid_data(qualification_route="diploma", diploma_branch="Mechanical",
                                               diploma_percentage=90, diploma_year=THIS_YEAR))
        self.assertEqual(eligibility.check_eligibility(cse, data)["outcome"], eligibility.OUTCOME_INSUFFICIENT)

    def test_postgraduate_marks_check(self):
        mca = course_service.get_course("mca")
        base = dict(qualification_route="degree", degree_name="BCA", degree_discipline="Computer Applications",
                    degree_year=THIS_YEAR - 1)
        low = eligibility.check_eligibility(mca, validation.normalize(valid_data(**base, degree_percentage=mca["min_pct"] - 1)))
        ok = eligibility.check_eligibility(mca, validation.normalize(valid_data(**base, degree_percentage=mca["min_pct"] + 10)))
        self.assertEqual(low["outcome"], eligibility.OUTCOME_NOT_MET)
        self.assertEqual(ok["outcome"], eligibility.OUTCOME_INSUFFICIENT)   # degree wording needs the college

    def test_structured_required_subjects_field_is_used_when_added(self):
        course = dict(course_service.get_course("btech-cse"), required_subjects=["Physics", "Mathematics"])
        self.assertEqual(eligibility.check_eligibility(course, validation.normalize(valid_data()))["outcome"],
                         eligibility.OUTCOME_MEETS)
        without = validation.normalize(valid_data(class12_subjects=["Chemistry"]))
        self.assertEqual(eligibility.check_eligibility(course, without)["outcome"], eligibility.OUTCOME_NOT_MET)


class Storage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "registrations_test.db"
        self.old_env = os.environ.get(registration_db.ENV_DB_PATH)
        os.environ[registration_db.ENV_DB_PATH] = str(self.db)
        self.n = 0

    def tearDown(self):
        if self.old_env is None:
            os.environ.pop(registration_db.ENV_DB_PATH, None)
        else:
            os.environ[registration_db.ENV_DB_PATH] = self.old_env
        self.tmp.cleanup()

    def token(self):
        self.n += 1
        return f"test-token-{self.n:08d}-abcdef"

    def submit(self, course_id="btech-cse", token=None, ack=False, **changes):
        return service.submit_registration(course_id, valid_data(**changes), token or self.token(), ack)

    def rows(self, sql="SELECT * FROM registrations", args=()):
        if not self.db.exists():                     # nothing has been saved yet
            return []
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(sql, args).fetchall()

    def test_submit_saves_a_submitted_registration_with_a_reference(self):
        result = self.submit()
        self.assertRegex(result["reference"], r"^REG-\d{4}-[A-Z2-9]{8}$")
        self.assertEqual(result["status"], "Submitted")
        self.assertFalse(result["already_submitted"])
        (row,) = self.rows()
        self.assertEqual(row["course_id"], "btech-cse")
        self.assertEqual(row["status"], "Submitted")
        self.assertEqual(row["mobile"], "+919876543210")
        self.assertEqual(json.loads(row["class12_subjects"]), ["Physics", "Chemistry", "Mathematics"])
        self.assertEqual(row["eligibility_outcome"], eligibility.OUTCOME_INSUFFICIENT)
        self.assertEqual(len(self.rows("SELECT * FROM status_history")), 1)

    def test_data_survives_a_restart(self):
        reference = self.submit()["reference"]
        code = ("import sys; sys.path.insert(0, %r); import registration_db as r; "
                "print(r.lookup_status(%r, 'asha@example.com')['status'])" % (str(ROOT), reference))
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                             env=dict(os.environ), cwd=str(ROOT))
        self.assertEqual(out.stdout.strip(), "Submitted", out.stderr)

    def test_same_token_never_creates_a_second_registration(self):
        token = self.token()
        first = self.submit(token=token)
        second = self.submit(token=token)
        self.assertEqual(first["reference"], second["reference"])
        self.assertTrue(second["already_submitted"])
        self.assertEqual(len(self.rows()), 1)

    def test_references_are_unique(self):
        refs = {self.submit()["reference"] for _ in range(150)}
        self.assertEqual(len(refs), 150)

    def test_invalid_answers_are_refused_and_nothing_is_saved(self):
        with self.assertRaises(service.SubmissionRefused) as caught:
            self.submit(email="not-an-email")
        self.assertIn("email", caught.exception.errors)
        with self.assertRaises(service.SubmissionRefused):
            self.submit(course_id="no-such-course")
        self.assertFalse(self.db.exists() and self.rows())

    def test_unmet_criteria_need_an_acknowledgement(self):
        with self.assertRaises(service.SubmissionRefused) as caught:
            self.submit(class12_percentage=10)
        self.assertIn("eligibility_acknowledged", caught.exception.errors)
        self.assertEqual(self.rows(), [])
        self.submit(class12_percentage=10, ack=True)
        (row,) = self.rows()
        self.assertEqual(row["eligibility_outcome"], eligibility.OUTCOME_NOT_MET)
        self.assertEqual(row["eligibility_acknowledged"], 1)
        self.assertEqual(row["status"], "Submitted")           # not meeting the criteria is not a rejection

    def test_a_record_cannot_choose_its_own_status(self):
        record = dict(validation.normalize(valid_data()), course_id="btech-cse", course_name="X",
                      eligibility_outcome="insufficient", status="Approved")
        registration_db.create_registration(record, self.token())
        self.assertEqual(self.rows()[0]["status"], "Submitted")

    def test_status_lookup_needs_reference_and_matching_email(self):
        ref = self.submit()["reference"]
        other = self.submit(full_name="Ravi Kumar", email="ravi@example.com")["reference"]
        info = service.check_registration_status(ref, "ASHA@example.com ")
        self.assertEqual(info["status"], "Submitted")
        self.assertEqual(info["course_name"], course_service.get_course("btech-cse")["name"])
        self.assertNotIn("email", info)
        self.assertNotIn("mobile", info)
        for ref_try, mail in ((ref, "ravi@example.com"), (other, "asha@example.com"), (ref, ""), ("REG-2026-ZZZZZZZZ", "asha@example.com"),
                              ("garbage", "asha@example.com"), (other.lower().replace("reg", "xyz"), "ravi@example.com")):
            with self.assertRaises(registration_db.LookupRefused, msg=(ref_try, mail)):
                service.check_registration_status(ref_try, mail)

    def test_repeated_wrong_attempts_lock_the_reference(self):
        ref = self.submit()["reference"]
        for _ in range(registration_db.MAX_FAILED_LOOKUPS):
            with self.assertRaises(registration_db.LookupRefused):
                service.check_registration_status(ref, "wrong@example.com")
        with self.assertRaises(registration_db.LookupRefused) as caught:
            service.check_registration_status(ref, "asha@example.com")       # correct, but locked
        self.assertEqual(caught.exception.reason, "locked")
        past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(timespec="seconds")
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE registrations SET locked_until = ?", (past,))
        self.assertEqual(service.check_registration_status(ref, "asha@example.com")["status"], "Submitted")

    def test_global_throttle_stops_guessing(self):
        ref = self.submit()["reference"]
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with sqlite3.connect(self.db) as conn:
            conn.executemany("INSERT INTO lookup_failures (failed_at) VALUES (?)", [(now,)] * registration_db.THROTTLE_MAX_FAILURES)
        with self.assertRaises(registration_db.LookupRefused) as caught:
            service.check_registration_status(ref, "asha@example.com")
        self.assertEqual(caught.exception.reason, "throttled")

    def test_submission_does_not_approve_and_only_the_separate_function_changes_status(self):
        ref = self.submit()["reference"]
        self.assertEqual(service.check_registration_status(ref, "asha@example.com")["status"], "Submitted")
        with self.assertRaises(ValueError):
            registration_db.record_status_change(ref, "Accepted!", "officer")
        with self.assertRaises(ValueError):
            registration_db.record_status_change(ref, "Approved", " ")
        registration_db.record_status_change(ref, "Under review", "officer-1", "Documents received.")
        info = service.check_registration_status(ref, "asha@example.com")
        self.assertEqual(info["status"], "Under review")
        self.assertEqual([h["status"] for h in info["history"]], ["Submitted", "Under review"])

    def test_sql_text_is_stored_as_text(self):
        record = dict(validation.normalize(valid_data()), course_id="btech-cse", course_name="X",
                      eligibility_outcome="insufficient", full_name="Robert'); DROP TABLE registrations;--")
        registration_db.create_registration(record, self.token())
        self.assertEqual(self.rows()[0]["full_name"], "Robert'); DROP TABLE registrations;--")
        self.assertEqual(len(self.rows()), 1)

    def test_personal_details_are_not_logged(self):
        with self.assertLogs("registration", level="DEBUG") as logs:
            ref = self.submit(full_name="Zubin Mehta", email="zubin.secret@example.com", mobile="9123456789")["reference"]
            with self.assertRaises(registration_db.LookupRefused):
                service.check_registration_status(ref, "wrong@example.com")
            service.check_registration_status(ref, "zubin.secret@example.com")
            registration_db.record_status_change(ref, "Under review", "officer")
        text = " ".join(logs.output)
        for secret in ("Zubin", "zubin.secret", "9123456789", "wrong@example.com"):
            self.assertNotIn(secret, text)
        self.assertIn(ref, text)

    def test_future_assistant_can_reuse_the_functions(self):
        review = service.review_registration("btech-cse", valid_data())
        self.assertEqual(review["errors"], {})
        self.assertEqual(review["eligibility"]["outcome"], eligibility.OUTCOME_INSUFFICIENT)
        self.assertEqual(self.rows() if self.db.exists() else [], [], "review must not save anything")
        self.assertIn("class12_subjects", schema.FIELD_SPECS)


if __name__ == "__main__":
    unittest.main()
