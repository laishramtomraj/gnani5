import unittest, sys
from unittest.mock import MagicMock
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from assistant import tts

class TestAssistantTTS(unittest.TestCase):
    def test_clean_text(self):
        clean = tts.clean_text_for_speech("## Title\n- **Bold item**")
        self.assertNotIn("**", clean)
        self.assertNotIn("##", clean)

    def test_mock_synthesize(self):
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.content = b"RIFFfakeaudio"
        post_fn = MagicMock(return_value=mock_res)
        audio = tts.synthesize_speech("Hello", "en", api_key="k", post_fn=post_fn)
        self.assertEqual(audio[:4], b"RIFF")

if __name__ == "__main__":
    unittest.main()