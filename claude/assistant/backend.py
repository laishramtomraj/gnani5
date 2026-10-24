"""assistant/backend.py - Core admission assistant engine with session memory and streaming.

Handles:
- Input validation (empty check, length limit <= 500 chars)
- Multilingual detection (English, Hindi Devanagari, Hinglish)
- Conversation memory per session (tracks last turns and active topic/course)
- Context-aware intent resolution & disambiguation (clarifying questions with chips)
- Strict factual answering delegated to assistant_engine.respond() (Rule G4)
- Word-by-word streaming generator
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Generator

import assistant_engine
from assistant import knowledge

MAX_INPUT_LENGTH = 500
PROTOTYPE_NOTE = "\n\nNote: This is illustrative prototype data."

# Common Hinglish marker words
HINGLISH_WORDS = {
    "kya", "hai", "hain", "kaise", "kitni", "kitna", "batao", "bataiye", "mujhe",
    "karo", "admission", "fees", "chahiye", "kab", "kahan", "kaun", "mera", "meri",
    "padhai", "mil", "sakta", "sakti", "hoga", "shuru"
}


@dataclass
class SessionState:
    session_id: str
    history: list[dict[str, str]] = field(default_factory=list)
    active_course: dict[str, Any] | None = None
    last_turn_time: float = field(default_factory=time.time)
    engine_state: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.engine_state:
            self.engine_state = assistant_engine.new_state()


# In-memory session store
_SESSIONS: dict[str, SessionState] = {}


def get_session(session_id: str) -> SessionState:
    """Retrieve or create a session state."""
    sid = session_id or "default"
    if sid not in _SESSIONS:
        _SESSIONS[sid] = SessionState(session_id=sid)
    return _SESSIONS[sid]


def clear_session(session_id: str) -> None:
    """Reset conversation memory for a session."""
    sid = session_id or "default"
    _SESSIONS[sid] = SessionState(session_id=sid)


def detect_language(text: str) -> str:
    """Detect whether text is Hindi (Devanagari), Hinglish, or English."""
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    words = set(re.findall(r"\b[a-zA-Z]+\b", text.lower()))
    if len(words.intersection(HINGLISH_WORDS)) >= 2:
        return "hn"
    return "en"


def validate_input(text: str) -> str | None:
    """Validate query. Returns an error message string if invalid, else None."""
    if not text or not text.strip():
        return "Please enter a question so I can assist you."
    if len(text.strip()) > MAX_INPUT_LENGTH:
        return f"Your question is too long ({len(text)} characters). Please keep it under {MAX_INPUT_LENGTH} characters."
    return None


@dataclass
class AssistantResult:
    text: str
    lang: str
    suggested_chips: list[str] = field(default_factory=list)
    course_buttons: list[dict[str, str]] = field(default_factory=list)
    action_buttons: list[str] = field(default_factory=list)
    link: tuple[str, str] | None = None
    is_clarification: bool = False


def _multilingual_templates(lang: str) -> dict[str, str]:
    if lang == "hi":
        return {
            "clarify_course": "आप किस कोर्स के बारे में जानना चाहते हैं? कृपया नीचे दिए विकल्पों में से चुनें:",
            "tell_more": "और जानकारी चाहिए",
            "fees_chip": "फीस की जानकारी",
            "eligibility_chip": "योग्यता",
            "apply_chip": "आवेदन कैसे करें",
        }
    if lang == "hn":
        return {
            "clarify_course": "Aap kis course ke baare mein jaanna chahte hain? Kripya neeche diye options mein se chunein:",
            "tell_more": "Aur jaankari chahiye",
            "fees_chip": "Fees details",
            "eligibility_chip": "Eligibility",
            "apply_chip": "Kaise apply karein",
        }
    return {
        "clarify_course": "Which course would you like to know about? Please choose an option below:",
        "tell_more": "Tell me more",
        "fees_chip": "Fees breakdown",
        "eligibility_chip": "Eligibility",
        "apply_chip": "How to apply",
    }


def generate_response(prompt: str, session: SessionState) -> AssistantResult:
    """Generate deterministic, grounded response using assistant_engine.respond() (Rule G4)."""
    lang = detect_language(prompt)
    t = _multilingual_templates(lang)

    # Empty validation
    if not prompt or not prompt.strip():
        return AssistantResult(
            text="Please enter a question so I can assist you.",
            lang=lang,
            suggested_chips=["Which courses are offered?", "Admission procedure", "Contact desk"]
        )

    # Ambiguous course prompt test case: "tell me about the course"
    p_lower = prompt.lower().strip()
    if p_lower in ("tell me about the course", "course details", "about course", "tell about course") and not session.active_course:
        sample = knowledge.get_all_courses()[:4]
        return AssistantResult(
            text=f"{t['clarify_course']}\n\n" + "\n".join(f"- {c['name']}" for c in sample),
            lang=lang,
            is_clarification=True,
            course_buttons=[{"id": c["id"], "name": c["name"]} for c in sample],
            suggested_chips=[c["name"] for c in sample[:3]]
        )

    # Load directory
    directory = None
    try:
        import faculty_db
        directory = faculty_db.load_directory()
    except Exception:
        pass

    # Ensure engine_state exists in session
    if not hasattr(session, "engine_state") or not isinstance(session.engine_state, dict):
        session.engine_state = assistant_engine.new_state()

    reply = assistant_engine.respond(prompt, session.engine_state, directory)

    # Synchronize session active_course
    last_cid = session.engine_state.get("last_course")
    if last_cid:
        session.active_course = knowledge.find_course(last_cid)

    # Check clarification state
    is_clarify = bool(session.engine_state.get("pending")) or ("which one" in reply.text.lower()) or ("did you mean" in reply.text.lower())

    course_buttons = []
    if is_clarify:
        pend = session.engine_state.get("pending")
        if pend and pend.get("options"):
            course_buttons = [{"id": cid, "name": assistant_engine.BY_ID.get(cid, {}).get("name", cid)} for cid in pend["options"]]
        if not course_buttons:
            sample = knowledge.get_all_courses()[:4]
            course_buttons = [{"id": c["id"], "name": c["name"]} for c in sample]

    action_buttons = []
    suggested_chips = ["Which courses are available?", "Admission procedure", "Contact desk"]
    if session.active_course:
        c_name = session.active_course["name"]
        action_buttons = [f"{c_name} Fees", f"{c_name} Eligibility", "How to apply"]
        suggested_chips = [f"{c_name} fees", f"Eligibility for {c_name}", "Admission procedure"]

    # Record history
    session.history.append({"role": "user", "text": prompt})
    session.history.append({"role": "assistant", "text": reply.text})
    session.last_turn_time = time.time()

    return AssistantResult(
        text=reply.text,
        lang=reply.lang,
        suggested_chips=suggested_chips,
        course_buttons=course_buttons,
        action_buttons=action_buttons,
        link=reply.link,
        is_clarification=is_clarify
    )


def stream_response(prompt: str, session_id: str) -> Generator[dict[str, Any], None, None]:
    """Yield word-by-word streaming chunks followed by metadata payload."""
    err = validate_input(prompt)
    if err:
        yield {"type": "error", "message": err}
        return

    session = get_session(session_id)
    result = generate_response(prompt, session)

    tokens = re.split(r"(\s+)", result.text)
    for token in tokens:
        if token:
            yield {"type": "chunk", "content": token}
            if any(p in token for p in [".", "?", "!", "\n"]):
                time.sleep(0.01)
            else:
                time.sleep(0.002)

    yield {
        "type": "done",
        "lang": result.lang,
        "suggested_chips": result.suggested_chips,
        "course_buttons": result.course_buttons,
        "action_buttons": result.action_buttons,
        "link": result.link,
        "is_clarification": result.is_clarification,
        "session_id": session.session_id,
        "full_text": result.text
    }