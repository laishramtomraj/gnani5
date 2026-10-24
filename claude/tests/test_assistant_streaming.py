import unittest, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from assistant import backend

class TestAssistantStreaming(unittest.TestCase):
    def test_empty_message_validation(self):
        chunks = list(backend.stream_response("", "test_user"))
        self.assertEqual(chunks[0]["type"], "error")

    def test_chunks_arrive_in_order(self):
        events = list(backend.stream_response("Tell me about BCA", "test_user"))
        self.assertTrue(len([e for e in events if e.get("type") == "chunk"]) > 3)
        self.assertEqual(events[-1]["type"], "done")

if __name__ == "__main__":
    unittest.main()