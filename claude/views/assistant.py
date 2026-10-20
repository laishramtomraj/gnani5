import re
import time

import streamlit as st

import assistant_engine as engine
import faculty_db
import gnani_tts

faculty_db.init_db()
USER_AVATAR, BOT_AVATAR = ":material/person:", ":material/smart_toy:"


# ------------------------------------------------------------------ data
@st.cache_data(show_spinner=False)
def _directory(stamp: float) -> dict:
    return faculty_db.load_directory()


def load_directory():
    try:
        return _directory(faculty_db.DB_PATH.stat().st_mtime)
    except Exception:                      # retrieval failed: the assistant will say it cannot verify faculty details
        return None


# ----------------------------------------------------------------- voice
def _secrets() -> dict:
    try:
        return {k: st.secrets[k] for k in st.secrets}
    except Exception:                      # no secrets file
        return {}


CONFIG = gnani_tts.load_config(_secrets())
VOICE_READY = bool(CONFIG["api_key"])


@st.cache_data(show_spinner=False, max_entries=64)
def _audio(text: str, lang: str, model: str, voice: str, speed: float, _api_key: str) -> bytes:
    return gnani_tts.synthesize(text, lang, _api_key, model, voice, speed)     # failures are not cached


# ---------------------------------------------------------------- state
if "assistant_messages" not in st.session_state:
    st.session_state["assistant_messages"] = []
    st.session_state["assistant_state"] = engine.new_state()
messages = st.session_state["assistant_messages"]


def handle(prompt: str) -> None:
    reply = engine.respond(prompt, st.session_state["assistant_state"], load_directory())
    shown = "(Message hidden because it contained sensitive details.)" if reply.redact else prompt
    messages.append({"role": "user", "text": shown})
    messages.append({"role": "assistant", "text": reply.text, "link": reply.link, "lang": reply.lang, "animate": True})
    if VOICE_READY and st.session_state.get("auto_speak", True) and not reply.redact:
        st.session_state["speak"] = len(messages) - 1


def request_speech(index: int) -> None:
    st.session_state["speak"] = index


def clear() -> None:
    st.session_state["assistant_messages"] = []
    st.session_state["assistant_state"] = engine.new_state()
    st.session_state.pop("speak", None)


def typewriter(text: str):
    """Reveal the answer word by word, like an AI assistant typing (about 2.5 seconds at most)."""
    parts = re.split(r"(\s+)", text)
    words = max(1, sum(1 for p in parts if p.strip()))
    delay = min(0.025, 2.5 / words)
    for p in parts:
        yield p
        if p.strip():
            time.sleep(delay)


# ------------------------------------------------------------------ page
top = st.columns([4, 1.4], vertical_alignment="center")
top[0].title("College Assistant", anchor=False)
top[1].toggle("Read answers aloud", value=VOICE_READY, key="auto_speak", disabled=not VOICE_READY)
st.caption(
    "Answers come only from the college's course and faculty records. This assistant is informational: "
    "it cannot approve applications or guarantee admission. You can write in English, Hindi or Hinglish."
)
if not VOICE_READY:
    st.info(
        "Voice is off because no Gnani API key was found. Set GNANI_API_KEY as an environment variable or in "
        "`.streamlit/secrets.toml`, then restart the app.",
        icon=":material/volume_off:",
    )

EXAMPLES = [
    "Which B.Sc. courses are available?",
    "Which computer courses cost less than ₹1.5 lakh per year?",
    "Compare CSE and AI & Machine Learning",
    "Am I eligible for B.Tech CSE with PCM and 78%?",
    "BCA की फीस कितनी है?",
    "B.Sc. Physics ki fees kitni hai?",
]
if not messages:
    st.write("Try a question:")
    for row in (EXAMPLES[:3], EXAMPLES[3:]):
        for col, q in zip(st.columns(3), row):
            col.button(q, key=f"example_{q}", on_click=handle, args=(q,), width="stretch")

prompt = st.chat_input("Ask about courses, fees, eligibility, faculty or registration")
if prompt:
    handle(prompt)

speak_index = st.session_state.pop("speak", None)
last_assistant = max((i for i, m in enumerate(messages) if m["role"] == "assistant"), default=None)

for i, m in enumerate(messages):
    with st.chat_message(m["role"], avatar=BOT_AVATAR if m["role"] == "assistant" else USER_AVATAR):
        if m.get("animate"):
            st.write_stream(typewriter(m["text"]))
            m["animate"] = False
        else:
            st.markdown(m["text"])
        if m["role"] != "assistant":
            continue
        if i == last_assistant and m.get("link"):
            label, page = m["link"]
            st.page_link(page, label=label)
        if VOICE_READY:
            st.button("Listen", key=f"listen_{i}", icon=":material/volume_up:", on_click=request_speech, args=(i,))
            if speak_index == i:
                spoken = gnani_tts.speech_text(m["text"], m.get("lang", "en"))
                lang = m.get("lang", "en")
                try:
                    with st.spinner("Preparing audio..."):
                        wav = _audio(spoken, lang, CONFIG["model"], CONFIG["voices"][lang], CONFIG["speed"], CONFIG["api_key"])
                    st.audio(wav, format="audio/wav", autoplay=True)
                except gnani_tts.TTSError as error:
                    st.warning(str(error), icon=":material/error:")

if messages:
    st.button("Clear chat", on_click=clear, icon=":material/delete:")
