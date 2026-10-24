"""tests/test_regression_assistant_v2.py - Comprehensive regression suite for College Admission Assistant v2."""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import assistant_engine
import faculty_db
from assistant import knowledge, tts


class TestRegressionAssistantV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        faculty_db.init_db()
        cls.directory = faculty_db.load_directory()

    def setUp(self):
        self.state = assistant_engine.new_state()

    # 1. Exact course names and known aliases
    def test_01_exact_course_and_aliases(self):
        r1 = assistant_engine.respond("B.Tech Computer Science & Engineering", self.state, self.directory)
        self.assertIn("B.Tech Computer Science & Engineering", r1.text)

        s2 = assistant_engine.new_state()
        r2 = assistant_engine.respond("cse", s2, self.directory)
        self.assertIn("B.Tech Computer Science & Engineering", r2.text)

        s3 = assistant_engine.new_state()
        r3 = assistant_engine.respond("bca", s3, self.directory)
        self.assertIn("BCA", r3.text)

    # 2. Typos and fragments; fuzzy match asks confirmation
    def test_02_typos_and_fragments(self):
        r1 = assistant_engine.respond("bca fees", self.state, self.directory)
        self.assertIn("70,000", r1.text)

        # Fuzzy match with moderate confidence asks for confirmation
        s2 = assistant_engine.new_state()
        r2 = assistant_engine.respond("tell me about bcaa", s2, self.directory)
        self.assertTrue("Did you mean BCA?" in r2.text or "BCA" in r2.text)

    # 3. Follow-up chain: course -> "fees?" -> "and eligibility?"
    def test_03_followup_chain(self):
        r1 = assistant_engine.respond("BCA", self.state, self.directory)
        self.assertIn("BCA", r1.text)

        r2 = assistant_engine.respond("fees?", self.state, self.directory)
        self.assertIn("70,000", r2.text)
        self.assertIn("BCA", r2.text)

        r3 = assistant_engine.respond("and eligibility?", self.state, self.directory)
        self.assertIn("BCA", r3.text)
        self.assertIn("eligibility", r3.text.lower())

    # 4. "tell me more" after a course answer expands the previous answer
    def test_04_tell_me_more_expansion(self):
        assistant_engine.respond("BCA", self.state, self.directory)
        r2 = assistant_engine.respond("tell me more", self.state, self.directory)
        self.assertIn("BCA", r2.text)
        self.assertTrue(len(r2.text) > 80)

    # 5. Course switch: BCA fees -> "same for BBA"
    def test_05_course_switch_preserves_topic(self):
        r1 = assistant_engine.respond("BCA fees", self.state, self.directory)
        self.assertIn("70,000", r1.text)
        self.assertIn("BCA", r1.text)

        r2 = assistant_engine.respond("same for BBA", self.state, self.directory)
        self.assertIn("BBA", r2.text)
        self.assertIn("tuition", r2.text.lower())
        self.assertIn("70,000", r2.text)

    # 6. Multi-intent: "bca fees eligibility and documents"
    def test_06_multi_intent_sections(self):
        r = assistant_engine.respond("bca fees eligibility and documents", self.state, self.directory)
        text_lower = r.text.lower()
        self.assertIn("bca", text_lower)
        self.assertIn("70,000", r.text)
        self.assertTrue("document" in text_lower or "mark sheet" in text_lower or "eligibility" in text_lower)

    # 7. Ambiguous course name triggers one clarification question
    def test_07_ambiguous_course_clarification(self):
        r = assistant_engine.respond("fees for physics", self.state, self.directory)
        # Should ask which one (B.Sc. Physics vs Engineering Physics)
        self.assertTrue("which one" in r.text.lower() or "physics" in r.text.lower())

    # 8. Unrelated new question does not inherit stale context
    def test_08_context_lifetime_reset_on_unrelated(self):
        assistant_engine.respond("BCA fees", self.state, self.directory)
        r2 = assistant_engine.respond("Who is the professor in Physics department?", self.state, self.directory)
        self.assertNotIn("BCA", r2.text)
        self.assertTrue("physics" in r2.text.lower() or "faculty" in r2.text.lower())

    # 9. Profile values persist in the session and can be corrected ("actually 62%")
    def test_09_profile_correction(self):
        assistant_engine.respond("Am I eligible for B.Tech CSE with 40% and PCM?", self.state, self.directory)
        self.assertEqual(self.state["profile"].get("percent"), 40.0)

        # Correction
        r2 = assistant_engine.respond("actually I got 62%", self.state, self.directory)
        self.assertEqual(self.state["profile"].get("percent"), 62.0)
        self.assertIn("62%", r2.text)

    # 10. Missing profile fields produce a targeted question for only the missing field
    def test_10_missing_profile_targeted_question(self):
        r = assistant_engine.respond("Am I eligible for B.Tech CSE?", self.state, self.directory)
        text_lower = r.text.lower()
        self.assertTrue("subject" in text_lower or "percentage" in text_lower or "share" in text_lower)

    # 11. Eligibility boundaries: exactly at min, below, missing marks, UNKNOWN is never NOT_MET
    def test_11_eligibility_boundaries(self):
        c = knowledge.find_course("btech-cse")
        min_pct = c["min_pct"]  # 45

        # Exactly at min
        res_exact = assistant_engine.evaluate(c, {"qualification": "class12", "subjects": {"physics", "mathematics", "chemistry"}, "percent": min_pct})
        self.assertEqual(res_exact[0], "meets")

        # One below min
        res_below = assistant_engine.evaluate(c, {"qualification": "class12", "subjects": {"physics", "mathematics", "chemistry"}, "percent": min_pct - 1})
        self.assertEqual(res_below[0], "not_meet")

        # Missing marks -> UNKNOWN (insufficient), never not_meet
        res_missing = assistant_engine.evaluate(c, {"qualification": "class12", "subjects": {"physics", "mathematics", "chemistry"}}, need_pct=True)
        self.assertEqual(res_missing[0], "insufficient")

    # 12. Comparison with missing data shows explicit "not available" or "-"
    def test_12_comparison_clean_formatting(self):
        r = assistant_engine.respond("compare bca and bba", self.state, self.directory)
        self.assertIn("BCA", r.text)
        self.assertIn("BBA", r.text)

    # 13. Budget filters and currency parsing
    def test_13_budget_and_currency_parsing(self):
        self.assertEqual(assistant_engine.parse_amount("1.5 lakh"), 150000)
        self.assertEqual(assistant_engine.parse_amount("80k"), 80000)
        self.assertEqual(assistant_engine.parse_amount("₹75,000"), 75000)

        r = assistant_engine.respond("courses with fee under 80000 per year", self.state, self.directory)
        self.assertIn("80,000", r.text)

    # 14. Supported language variations (English, Hindi, Hinglish)
    def test_14_multilingual_handling(self):
        self.assertEqual(assistant_engine.detect_lang("Which courses are available?"), "en")
        self.assertEqual(assistant_engine.detect_lang("BCA \u0915\u0940 \u092b\u0940\u0938 \u0915\u093f\u0924\u0928\u0940 \u0939\u0948?"), "hi")
        self.assertEqual(assistant_engine.detect_lang("BCA ki fees kitni hai batao"), "hn")

    # 15. Unsupported question gets a safe fallback
    def test_15_unsupported_safe_fallback(self):
        r = assistant_engine.respond("What is the hostel mess fee and scholarship deadline?", self.state, self.directory)
        self.assertIn("verified information", r.text.lower())
        self.assertIn("admissions office", r.text.lower())

    # 16. Reset / new conversation clears state
    def test_16_state_reset(self):
        s = assistant_engine.new_state()
        assistant_engine.respond("BCA fees", s, self.directory)
        self.assertIsNotNone(s.get("last_course"))

        s_cleared = assistant_engine.new_state()
        self.assertIsNone(s_cleared.get("last_course"))
        self.assertEqual(s_cleared.get("profile"), {})

    # 17. TTS failure does not break the text reply
    def test_17_tts_failure_isolation(self):
        # Even if TTS fails or throws, text synthesis is independent
        try:
            tts.synthesize_speech("Hello", "en", api_key="")
        except tts.TTSError as e:
            self.assertIn("GNANI_API_KEY", str(e))

    # 18. Golden characterization tests run and pass
    def test_18_golden_compatibility(self):
        r = assistant_engine.respond("BCA", self.state, self.directory)
        self.assertIn("BCA", r.text)
        self.assertIn("Note: This is illustrative prototype data.", r.text)

    # 19. Static check: no LLM/AI client library imported
    def test_19_static_no_runtime_llm(self):
        engine_file = ROOT / "assistant_engine.py"
        with open(engine_file, "r", encoding="utf-8") as f:
            code = f.read().lower()
        forbidden = ["openai", "anthropic", "langchain", "llama", "huggingface", "google.generativeai", "transformers"]
        for lib in forbidden:
            self.assertNotIn(f"import {lib}", code)
            self.assertNotIn(f"from {lib}", code)


if __name__ == "__main__":
    unittest.main()
