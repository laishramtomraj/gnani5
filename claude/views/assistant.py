import re
import time
import streamlit as st

import assistant_engine
import faculty_db
from assistant import knowledge, tts

faculty_db.init_db()

USER_AVATAR = ":material/person:"
BOT_AVATAR = ":material/smart_toy:"

VOICE_KEY = tts.get_api_key()
VOICE_READY = bool(VOICE_KEY)


# ------------------------------------------------------------------ state
if "assistant_messages" not in st.session_state:
    st.session_state["assistant_messages"] = []
    st.session_state["engine_state"] = assistant_engine.new_state()

messages = st.session_state["assistant_messages"]
engine_state = st.session_state["engine_state"]


def handle(prompt: str) -> None:
    if not prompt or not prompt.strip():
        return

    directory = faculty_db.load_directory()
    reply = assistant_engine.respond(prompt, engine_state, directory)

    messages.append({"role": "user", "text": prompt})
    messages.append({
        "role": "assistant",
        "text": reply.text,
        "link": reply.link,
        "lang": reply.lang,
        "animate": True,
    })

    if VOICE_READY and st.session_state.get("auto_speak", False):
        st.session_state["speak_index"] = len(messages) - 1


def clear() -> None:
    st.session_state["assistant_messages"] = []
    st.session_state["engine_state"] = assistant_engine.new_state()
    st.session_state.pop("speak_index", None)


def typewriter(text: str):
    """Reveal response word by word naturally."""
    parts = re.split(r"(\s+)", text)
    for p in parts:
        yield p
        if p.strip():
            time.sleep(0.015)


# ------------------------------------------------------------------ page header
top = st.columns([4, 1.4], vertical_alignment="center")
top[0].title("College Admission Assistant", anchor=False)
top[1].toggle("Auto-speak", value=False, key="auto_speak", disabled=not VOICE_READY)

st.caption(
    "Ground truth answers powered by the college course & faculty database with Gnani TTS voice support. "
    "I am an automated assistant. For official admission advice, please contact the college."
)

if not VOICE_READY:
    st.info(
        "Voice synthesis is off: add `GNANI_API_KEY` in `.streamlit/secrets.toml` or Streamlit Cloud Secrets to enable audio.",
        icon=":material/volume_off:",
    )

# ------------------------------------------------------------ suggested questions
EXAMPLES = [
    "Which B.Tech courses are available?",
    "BCA ki fees kitni hai?",
    "Am I eligible for B.Tech CSE with 75% and PCM?",
    "What is the admission procedure?",
    "Tell me about BBA",
    "Courses under 1 lakh per year",
]

if not messages:
    st.write("Suggested questions:")
    for row in (EXAMPLES[:3], EXAMPLES[3:]):
        for col, q in zip(st.columns(3), row):
            col.button(q, key=f"ex_{q}", on_click=handle, args=(q,), use_container_width=True)

# ---------------------------------------------------------------- chat input
prompt = st.chat_input("Ask about courses, fees, eligibility, faculty or registration...")
if prompt:
    handle(prompt)

# --------------------------------------------------------------- render messages
speak_target = st.session_state.pop("speak_index", None)
last_bot = max((i for i, m in enumerate(messages) if m["role"] == "assistant"), default=None)

for i, m in enumerate(messages):
    with st.chat_message(m["role"], avatar=BOT_AVATAR if m["role"] == "assistant" else USER_AVATAR):
        if m.get("animate"):
            st.write_stream(typewriter(m["text"]))
            m["animate"] = False
        else:
            st.markdown(m["text"])

        if m["role"] != "assistant":
            continue

        # Optional link button to courses/faculty/admissions
        if i == last_bot and m.get("link"):
            label, page = m["link"]
            clean_page = page.lstrip("/")
            try:
                st.page_link(clean_page, label=f"📄 {label}")
            except Exception:
                pass

        # Audio Listen button
        if VOICE_READY:
            def _request_voice(idx=i):
                st.session_state["speak_index"] = idx

            st.button("Listen", key=f"listen_{i}", icon=":material/volume_up:", on_click=_request_voice)

            if speak_target == i:
                lang = m.get("lang", "en")
                try:
                    with st.spinner("Generating speech via Gnani Timbre..."):
                        wav_data = tts.synthesize_speech(m["text"], lang=lang, api_key=VOICE_KEY)
                    st.audio(wav_data, format="audio/wav", autoplay=True)
                except tts.TTSError as error:
                    st.warning(str(error), icon=":material/error:")

if messages:
    st.button("New conversation", on_click=clear, icon=":material/delete:")