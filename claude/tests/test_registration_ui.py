"""Page-level tests that drive the real Streamlit pages with Streamlit's AppTest (no browser needed).

Run from the project folder (Windows or Mac/Linux):
    python -m unittest discover -s tests -v
"""
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402

import course_service  # noqa: E402
import registration_db  # noqa: E402

THIS_YEAR = date.today().year
ADMISSIONS = str(ROOT / "views" / "admissions.py")
CSE = course_service.get_course("btech-cse")["name"]
PHYSICS = course_service.get_course("bsc-phy")["name"]
MCA = course_service.get_course("mca")["name"]


def page(path=ADMISSIONS):
    at = AppTest.from_file(path, default_timeout=60)
    return at


class AdmissionsPageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "ui_test.db"
        self.old_env = os.environ.get(registration_db.ENV_DB_PATH)
        os.environ[registration_db.ENV_DB_PATH] = str(self.db)

    def tearDown(self):
        if self.old_env is None:
            os.environ.pop(registration_db.ENV_DB_PATH, None)
        else:
            os.environ[registration_db.ENV_DB_PATH] = self.old_env
        self.tmp.cleanup()

    # ------------------------------------------------------------ helpers
    def start(self, course_name=None):
        at = page()
        if course_name:
            at.session_state["selected_course"] = course_name
        return at.run()

    def fill(self, at, **changes):
        v = dict(full_name="Asha Rao", email="asha@example.com", mobile="98765 43210", board="CBSE", stream="Science",
                 subjects=["Physics", "Chemistry", "Mathematics"], pct=82.5, year=THIS_YEAR)
        v.update(changes)
        at.text_input(key="f_full_name").input(v["full_name"])
        at.text_input(key="f_email").input(v["email"])
        at.text_input(key="f_mobile").input(v["mobile"])
        at.date_input(key="f_date_of_birth").set_value(date(2007, 5, 1))
        at.selectbox(key="f_class12_board").select(v["board"])
        at.selectbox(key="f_class12_stream").select(v["stream"])
        at.multiselect(key="f_class12_subjects").set_value(v["subjects"])
        at.number_input(key="f_class12_percentage").set_value(v["pct"])
        at.selectbox(key="f_class12_year").select(v["year"])
        at.checkbox(key="f_privacy_acknowledged").check()
        at.checkbox(key="f_declaration_accurate").check()
        return at.run()

    def registrations(self):
        if not self.db.exists():
            return []
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute("SELECT * FROM registrations").fetchall()

    def text_of(self, at):
        parts = []
        for group in (at.markdown, at.caption, at.error, at.warning, at.info, at.success, at.subheader, at.text):
            parts += [str(e.value) for e in group]
        return "\n".join(parts)

    def assertClean(self, at):
        self.assertEqual([e.value for e in at.exception], [], "the page raised an exception")

    # --------------------------------------------------------------- tests
    def test_page_loads_without_a_selected_course(self):
        at = self.start()
        self.assertClean(at)
        self.assertEqual([t.label for t in at.tabs], ["Register for a course", "Check registration status"])
        self.assertIsNone(at.selectbox(key="f_course_name").value)
        self.assertIn("Choose a course to see its details", self.text_of(at))
        self.assertEqual(len(at.text_input), 2 + 0, "only the status-lookup inputs show until a course is chosen")

    def test_selected_course_from_course_page_is_preselected_with_details(self):
        at = self.start(CSE)
        self.assertClean(at)
        self.assertEqual(at.selectbox(key="f_course_name").value, CSE)
        labels = [m.label for m in at.metric]
        for expected in ("Duration", "Annual tuition", "Total tuition", "Seat capacity"):
            self.assertIn(expected, labels)
        text = self.text_of(at)
        self.assertIn("Computer Science and Engineering", text)       # department
        self.assertIn("Seat availability is not recorded", text)       # never claims seats are open
        self.assertIn("Minimum marks", text)

    def test_changing_course_updates_details_and_the_site_wide_selection(self):
        at = self.start(CSE)
        before = {m.label: m.value for m in at.metric}
        at.selectbox(key="f_course_name").select(PHYSICS).run()
        self.assertClean(at)
        self.assertEqual(at.session_state["selected_course"], PHYSICS)
        after = {m.label: m.value for m in at.metric}
        self.assertNotEqual(before["Annual tuition"], after["Annual tuition"])
        self.assertIn("Physics", self.text_of(at))

    def test_applicable_fields_follow_the_selected_course(self):
        at = self.start(CSE)
        self.assertEqual(at.radio(key="f_qualification_route").options, ["Class 12 or equivalent", "Diploma (lateral entry)"])
        at.radio(key="f_qualification_route").set_value("diploma").run()
        self.assertTrue([t for t in at.text_input if t.key == "f_diploma_branch"])
        at.selectbox(key="f_course_name").select(PHYSICS).run()          # no diploma pathway stored
        self.assertClean(at)
        self.assertFalse([r for r in at.radio if r.key == "f_qualification_route"])
        self.assertEqual(at.session_state["reg_route"], "class12")
        self.assertTrue([s for s in at.selectbox if s.key == "f_class12_board"])
        at.selectbox(key="f_course_name").select(MCA).run()              # postgraduate: degree route
        self.assertClean(at)
        self.assertEqual(at.session_state["reg_route"], "degree")
        self.assertTrue([t for t in at.text_input if t.key == "f_degree_name"])
        self.assertFalse([s for s in at.selectbox if s.key == "f_class12_board"])

    def test_empty_form_shows_clear_errors_and_does_not_continue(self):
        at = self.start(CSE)
        at.button(key="reg_review_button").click().run()
        self.assertClean(at)
        self.assertEqual(at.session_state["reg_step"], "form")
        text = self.text_of(at)
        for message in ("Enter your full name.", "Enter your email address.", "Enter your mobile number.",
                        "Select the subjects you studied in Class 12.", "Tick the declaration"):
            self.assertIn(message, text)
        self.assertTrue([e for e in at.error if "Please check" in str(e.value)])
        self.assertEqual(self.registrations(), [])

    def test_invalid_values_keep_other_answers(self):
        at = self.start(CSE)
        self.fill(at, email="not-an-email", mobile="123")
        at.button(key="reg_review_button").click().run()
        self.assertEqual(at.session_state["reg_step"], "form")
        text = self.text_of(at)
        self.assertIn("Enter a valid email address", text)
        self.assertIn("10-digit Indian mobile number", text)
        self.assertEqual(at.text_input(key="f_full_name").value, "Asha Rao")      # entries are preserved
        self.assertEqual(at.number_input(key="f_class12_percentage").value, 82.5)

    def test_full_registration_flow(self):
        at = self.start(CSE)
        self.fill(at)
        at.button(key="reg_review_button").click().run()
        self.assertClean(at)
        self.assertEqual(at.session_state["reg_step"], "review")
        self.assertEqual(self.registrations(), [], "review must not save anything")
        text = self.text_of(at)
        self.assertIn("Nothing has been submitted yet", text)
        self.assertIn("Insufficient information to determine eligibility", text)  # CSE subject text needs the college
        self.assertIn("Asha Rao", text)
        self.assertIn("+91 98765 43210", text)

        token = at.session_state["reg_token"]
        at.button(key="reg_submit_button").click().run()
        self.assertClean(at)
        self.assertEqual(at.session_state["reg_step"], "done")
        reference = at.code[0].value
        self.assertRegex(reference, r"^REG-\d{4}-[A-Z2-9]{8}$")
        text = self.text_of(at)
        self.assertIn("Submitted", text)
        self.assertIn("not admission", text)
        self.assertNotIn("**Status:** Approved", text)
        rows = self.registrations()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["reference"], reference)
        self.assertEqual(rows[0]["status"], "Submitted")
        self.assertEqual(rows[0]["course_id"], "btech-cse")
        # personal details are no longer kept in the session once saved
        self.assertFalse([k for k in at.session_state.keys() if str(k).startswith("f_")])
        # a page rerun must not save a second copy
        at.run()
        self.assertEqual(len(self.registrations()), 1)
        self.assertEqual(at.session_state["reg_token"], token)

    def test_back_to_edit_keeps_entries(self):
        at = self.start(CSE)
        self.fill(at, full_name="Meera Iyer")
        at.button(key="reg_review_button").click().run()
        at.button(key="reg_back_button").click().run()
        self.assertClean(at)
        self.assertEqual(at.session_state["reg_step"], "form")
        self.assertEqual(at.text_input(key="f_full_name").value, "Meera Iyer")
        self.assertEqual(at.multiselect(key="f_class12_subjects").value, ["Physics", "Chemistry", "Mathematics"])
        self.assertTrue(at.checkbox(key="f_declaration_accurate").value)
        self.assertEqual(self.registrations(), [])

    def test_unmet_criteria_are_explained_and_need_acknowledgement(self):
        at = self.start(CSE)
        self.fill(at, pct=10.0)
        at.button(key="reg_review_button").click().run()
        self.assertEqual(at.session_state["reg_step"], "review")
        text = self.text_of(at)
        self.assertIn("Does not meet the stored criteria", text)
        self.assertIn("below the stored minimum", text)
        submit = at.button(key="reg_submit_button")
        self.assertTrue(submit.disabled)
        at.checkbox(key="f_eligibility_acknowledged").check().run()
        self.assertFalse(at.button(key="reg_submit_button").disabled)
        at.button(key="reg_submit_button").click().run()
        self.assertEqual(at.session_state["reg_step"], "done")
        row = self.registrations()[0]
        self.assertEqual(row["eligibility_outcome"], "does_not_meet")
        self.assertEqual(row["status"], "Submitted")

    def test_status_lookup_is_verified_and_generic_on_failure(self):
        at = self.start(CSE)
        self.fill(at)
        at.button(key="reg_review_button").click().run()
        at.button(key="reg_submit_button").click().run()
        reference = at.code[0].value

        def lookup(ref, email):
            at.text_input(key="reg_status_reference").input(ref)
            at.text_input(key="reg_status_email").input(email)
            [b for b in at.button if b.label == "Check status"][0].click().run()

        lookup(reference, "someone.else@example.com")
        self.assertTrue([e for e in at.error if "could not verify" in str(e.value)])
        self.assertNotIn("Asha", self.text_of(at))
        lookup("REG-2026-ZZZZZZZZ", "asha@example.com")
        self.assertTrue([e for e in at.error if "could not verify" in str(e.value)])        # same message
        lookup(reference, "ASHA@example.com")
        self.assertClean(at)
        text = self.text_of(at)
        self.assertIn(reference, text)
        self.assertIn("Status:** Submitted", text)
        self.assertIn("waiting for the college's review", text)
        self.assertNotIn("**Status:** Approved", text)


class ExistingPagesStillWork(unittest.TestCase):
    """The registration work must not break the pages that already existed.

    Pages are run through app.py (with its navigation), exactly like the real website."""

    def site(self, page_path=None):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
        at.run()
        if page_path:
            at.switch_page(page_path).run()
        return at

    def test_each_existing_page_runs(self):
        for name in ("home", "courses", "faculty", "about", "contact", "admissions"):
            at = self.site(f"views/{name}.py")
            self.assertEqual([e.value for e in at.exception], [], name)

    def test_course_detail_page_still_opens(self):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
        at.query_params["course"] = "btech-cse"
        at.run()
        at.switch_page("views/courses.py")
        at.query_params["course"] = "btech-cse"
        at.run()
        self.assertEqual([e.value for e in at.exception], [])
        self.assertTrue([b for b in at.button if b.label == "Register for This Course"])

    def test_register_button_on_a_course_page_preselects_that_course(self):
        at = self.site("views/courses.py")
        card_button = [b for b in at.button if b.key == "reg_btech-cse"][0]
        card_button.click().run()
        self.assertEqual(at.session_state["selected_course"], CSE)       # existing behaviour, unchanged
        at.switch_page("views/admissions.py").run()                       # what st.switch_page does in the browser
        self.assertEqual([e.value for e in at.exception], [])
        self.assertEqual(at.selectbox(key="f_course_name").value, CSE)


if __name__ == "__main__":
    unittest.main()
