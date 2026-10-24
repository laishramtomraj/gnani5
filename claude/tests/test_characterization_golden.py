"""tests/test_characterization_golden.py - Golden baseline characterization tests.

Captures baseline behavior for representative queries across:
- Course lookups & aliases
- Fees, seats, eligibility
- Course comparisons
- Budget filtering
- Faculty queries
- Multilingual responses (Hindi & Hinglish)
- Safe fallback on unstored information
"""
import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import assistant_engine
import faculty_db


class TestCharacterizationGolden(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        faculty_db.init_db()
        cls.directory = faculty_db.load_directory()

    def setUp(self):
        self.state = assistant_engine.new_state()

    def test_golden_bca_overview(self):
        reply = assistant_engine.respond("BCA", self.state, self.directory)
        self.assertIn("BCA", reply.text)
        self.assertIn("Note: This is illustrative prototype data.", reply.text)
        self.assertEqual(reply.lang, "en")
        self.assertIsNotNone(reply.link)

    def test_golden_bca_fees(self):
        reply = assistant_engine.respond("BCA fees", self.state, self.directory)
        self.assertIn("70,000", reply.text)
        self.assertIn("BCA", reply.text)
        self.assertIn("annual tuition", reply.text.lower())

    def test_golden_eligibility_pcm(self):
        reply = assistant_engine.respond("Am I eligible for B.Tech CSE with 78% and PCM?", self.state, self.directory)
        self.assertIn("B.Tech Computer Science & Engineering", reply.text)
        self.assertIn("78%", reply.text)
        self.assertIn("Physics", reply.text)

    def test_golden_course_comparison(self):
        reply = assistant_engine.respond("Compare BCA and BBA", self.state, self.directory)
        self.assertIn("BCA", reply.text)
        self.assertIn("BBA", reply.text)

    def test_golden_budget_filter(self):
        reply = assistant_engine.respond("Courses under 1 lakh per year", self.state, self.directory)
        self.assertIn("1,00,000", reply.text)

    def test_golden_faculty_physics(self):
        reply = assistant_engine.respond("Faculty in Physics department", self.state, self.directory)
        self.assertTrue("Physics" in reply.text or "faculty" in reply.text.lower())

    def test_golden_hindi_devanagari(self):
        # BCA ki fees in Hindi
        reply = assistant_engine.respond("BCA \u0915\u0940 \u092b\u0940\u0938 \u0915\u093f\u0924\u0928\u0940 \u0939\u0948?", self.state, self.directory)
        self.assertEqual(reply.lang, "hi")
        self.assertIn("70,000", reply.text)

    def test_golden_hinglish(self):
        reply = assistant_engine.respond("BCA ki fees kitni hai?", self.state, self.directory)
        self.assertEqual(reply.lang, "hn")
        self.assertIn("70,000", reply.text)

    def test_golden_unstored_fallback(self):
        reply = assistant_engine.respond("What is the hostel scholarship deadline?", self.state, self.directory)
        self.assertIn("verified information", reply.text.lower())
        self.assertIn("admissions office", reply.text.lower())


if __name__ == "__main__":
    unittest.main()
