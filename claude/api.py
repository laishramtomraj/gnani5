"""
api.py - Lightweight read-only HTTP API & static server for the College Assistant.

Local development:
    python api.py

Deployment:
    Set GNANI_API_KEY in your hosting provider's Environment Variables / Secrets.
    The server automatically uses the platform-assigned PORT.
"""

from __future__ import annotations

import json
import os
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from config import get_gnani_api_key


# --------------------------------------------------------------------
# Project setup
# --------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from assistant import backend, knowledge, tts  # noqa: E402

FRONTEND_DIR = ROOT_DIR / "frontend"
FEEDBACK_LOG = ROOT_DIR / "assistant" / "feedback.jsonl"


# Validate the Gnani API key when the API starts.
# Locally: loaded from .env through config.py
# Deployment: loaded from hosting platform environment variables/secrets
GNANI_API_KEY = get_gnani_api_key()


# --------------------------------------------------------------------
# HTTP request handler
# --------------------------------------------------------------------

class CollegeAPIHandler(SimpleHTTPRequestHandler):
    server_version = "CollegeAssistantAPI/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def _send_json(self, data: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(data).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", 0))

        if content_length <= 0:
            return {}

        raw = self.rfile.read(content_length).decode("utf-8", errors="replace")

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        url = urlparse(self.path)
        path = url.path

        if path == "/api/health":
            self._send_json({
                "status": "ok",
                "service": "College Admission Assistant API",
                "gnani_key_configured": bool(GNANI_API_KEY),
            })
            return

        if path == "/api/courses":
            courses = knowledge.get_all_courses()

            summary = [
                {
                    "id": course["id"],
                    "name": course["name"],
                    "category": course["category"],
                    "tuition": course["tuition"],
                }
                for course in courses
            ]

            self._send_json({
                "courses": summary,
                "count": len(summary),
            })
            return

        if path in ("/", ""):
            self.path = "/index.html"
        elif path.startswith("/frontend/"):
            self.path = path.replace("/frontend/", "/", 1)

        super().do_GET()

    def do_POST(self) -> None:
        url = urlparse(self.path)
        path = url.path

        if path == "/api/chat/stream":
            self._handle_chat_stream()
        elif path == "/api/chat/clear":
            self._handle_chat_clear()
        elif path == "/api/chat/feedback":
            self._handle_chat_feedback()
        elif path == "/api/tts":
            self._handle_tts()
        else:
            self._send_json(
                {"error": "Endpoint not found"},
                status=HTTPStatus.NOT_FOUND,
            )

    # ----------------------------------------------------------------
    # Chat endpoints
    # ----------------------------------------------------------------

    def _handle_chat_stream(self) -> None:
        payload = self._read_json_body()
        prompt = payload.get("prompt", "")
        session_id = payload.get("session_id", "default_session")

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.close_connection = True

        try:
            for event in backend.stream_response(prompt, session_id):
                event_line = f"data: {json.dumps(event)}\n\n"
                self.wfile.write(event_line.encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            try:
                error_event = {
                    "type": "error",
                    "message": "The assistant is temporarily unavailable.",
                }

                self.wfile.write(
                    f"data: {json.dumps(error_event)}\n\n".encode("utf-8")
                )
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _handle_chat_clear(self) -> None:
        payload = self._read_json_body()
        session_id = payload.get("session_id", "default_session")

        backend.clear_session(session_id)

        self._send_json({
            "status": "cleared",
            "session_id": session_id,
        })

    def _handle_chat_feedback(self) -> None:
        payload = self._read_json_body()
        session_id = payload.get("session_id", "anonymous")
        vote = payload.get("vote", "")
        query = payload.get("query", "")

        FEEDBACK_LOG.parent.mkdir(parents=True, exist_ok=True)

        with open(FEEDBACK_LOG, "a", encoding="utf-8") as file:
            file.write(
                json.dumps({
                    "timestamp": backend.time.time(),
                    "session_id": session_id,
                    "vote": vote,
                    "query": query[:120],
                }) + "\n"
            )

        self._send_json({"status": "recorded"})

    # ----------------------------------------------------------------
    # Text-to-speech endpoint
    # ----------------------------------------------------------------

    def _handle_tts(self) -> None:
        payload = self._read_json_body()
        text = payload.get("text", "")
        lang = payload.get("lang", "en")

        if not text.strip():
            self._send_json(
                {"error": "Text is required for speech synthesis."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        try:
            wav_bytes = tts.synthesize_speech(text, lang=lang)

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(wav_bytes)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(wav_bytes)

        except tts.TTSError as exc:
            self._send_json(
                {"error": str(exc)},
                status=HTTPStatus.BAD_REQUEST,
            )
        except Exception:
            self._send_json(
                {"error": "Voice synthesis temporarily unavailable."},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )


# --------------------------------------------------------------------
# Server startup
# --------------------------------------------------------------------

def run(host: str = "127.0.0.1", port: int | None = None) -> None:
    """Start the API server using the platform port or local default."""
    if port is None:
        port = int(os.environ.get("PORT", "8000"))

    server = ThreadingHTTPServer((host, port), CollegeAPIHandler)

    print(f"Assistant API & Frontend running at http://{host}:{port}/")
    print(f"Gnani API key configured: {bool(GNANI_API_KEY)}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down Assistant API...")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()