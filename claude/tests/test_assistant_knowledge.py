import unittest, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from assistant import knowledge

class TestAssistantKnowledge(unittest.TestCase):
    def test_get_all_courses(self):
        self.assertGreater(len(knowledge.get_all_courses()), 0)
    def test_find_course(self):
        self.assertIsNotNone(knowledge.find_course("btech-cse"))
        self.assertIsNotNone(knowledge.find_course("computer science"))
    def test_get_course_fee_details(self):
        fees = knowledge.get_course_fee_details("btech-cse")
        self.assertIn("1,50,000", fees["annual_tuition_formatted"])
    def test_get_course_eligibility(self):
        self.assertIsNotNone(knowledge.get_course_eligibility("btech-cse"))

if __name__ == "__main__":
    unittest.main()