from __future__ import annotations

import re
import time

import streamlit as st

import assistant_engine
import faculty_db
from assistant import tts

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
    """Use the existing assistant engine and preserve its response flow."""
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
    """Start a fresh conversation without changing the assistant engine."""
    st.session_state["assistant_messages"] = []
    st.session_state["engine_state"] = assistant_engine.new_state()
    st.session_state.pop("speak_index", None)


def typewriter(text: str):
    """Reveal response word by word naturally."""
    parts = re.split(r"(\s+)", text)
    for part in parts:
        yield part
        if part.strip():
            time.sleep(0.015)


# ------------------------------------------------------------------ assistant-only design
# Styling is scoped to this page and does not change forms or controls elsewhere.
st.html(r"""
<style>
:root {
  --assistant-ink: #172554;
  --assistant-muted: #52627a;
  --assistant-border: #dce5f2;
  --assistant-blue: #2563eb;
  --assistant-teal: #0f9b8e;
  --assistant-lilac: #8b5cf6;
}

/* Give the assistant the usable viewport, without the separate college banner/footer. */
div[data-testid="stMainBlockContainer"]:has(.st-key-assistant_workspace) {
  max-width: 1440px !important;
  padding-top: .8rem !important;
  padding-bottom: 1.2rem !important;
  padding-left: clamp(1rem, 3.4vw, 3.5rem) !important;
  padding-right: clamp(1rem, 3.4vw, 3.5rem) !important;
}
.st-key-assistant_workspace {
  gap: .85rem !important;
  color: var(--assistant-ink);
}

.assistant-hero {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  display: flex;
  align-items: center;
  gap: 1.1rem;
  padding: clamp(1.25rem, 2.8vw, 2rem);
  margin: .2rem 0 1rem;
  border: 1px solid rgba(255,255,255,.25);
  border-radius: 26px;
  color: #fff;
  background: linear-gradient(120deg, #142653 0%, #224c92 56%, #087f8c 100%);
  box-shadow: 0 16px 42px rgba(24, 55, 112, .18);
}
.assistant-hero::before,
.assistant-hero::after {
  content: "";
  position: absolute;
  z-index: -1;
  border-radius: 999px;
  pointer-events: none;
}
.assistant-hero::before {
  width: 260px; height: 260px; right: -65px; top: -145px;
  background: rgba(255,255,255,.12);
}
.assistant-hero::after {
  width: 175px; height: 175px; right: 130px; bottom: -135px;
  background: rgba(103,232,249,.13);
}
.assistant-hero-icon {
  flex: 0 0 60px;
  width: 60px; height: 60px;
  display: grid; place-items: center;
  border: 1px solid rgba(255,255,255,.28);
  border-radius: 19px;
  background: rgba(255,255,255,.14);
  font-size: 1.75rem;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.16);
}
.assistant-hero-copy { min-width: 0; }
.assistant-eyebrow {
  margin: 0 0 .36rem;
  color: #c8f7ff;
  font-size: .72rem;
  font-weight: 800;
  letter-spacing: .14em;
  text-transform: uppercase;
}
.assistant-hero-title {
  margin: 0;
  color: #fff !important;
  font-size: clamp(1.55rem, 3vw, 2.35rem);
  font-weight: 800;
  line-height: 1.12;
  letter-spacing: -.035em;
}
.assistant-hero-description {
  max-width: 780px;
  margin: .55rem 0 0;
  color: rgba(255,255,255,.88);
  font-size: .98rem;
  line-height: 1.6;
}
.assistant-feature-pills {
  display: flex; flex-wrap: wrap; gap: .5rem;
  margin-top: .9rem;
}
.assistant-feature-pills span {
  display: inline-flex; align-items: center; gap: .38rem;
  padding: .32rem .65rem;
  border: 1px solid rgba(255,255,255,.22);
  border-radius: 999px;
  background: rgba(255,255,255,.10);
  color: #fff;
  font-size: .76rem;
  font-weight: 650;
}
.assistant-feature-pills span::before {
  content: ""; width: 6px; height: 6px; border-radius: 50%;
  background: #86efac;
}

.assistant-welcome {
  padding: clamp(1.15rem, 2.1vw, 1.65rem);
  margin: .65rem 0 1rem;
  border: 1px solid #d8e5fa;
  border-radius: 22px;
  background: linear-gradient(135deg, #f4f8ff 0%, #f5fbff 55%, #f1fdfa 100%);
  box-shadow: 0 7px 24px rgba(37, 99, 235, .055);
}
.assistant-welcome-kicker {
  margin: 0 0 .4rem;
  color: #2563eb;
  font-size: .73rem;
  font-weight: 800;
  letter-spacing: .11em;
  text-transform: uppercase;
}
.assistant-welcome-title {
  margin: 0;
  color: #172554 !important;
  font-size: clamp(1.25rem, 2.3vw, 1.7rem);
  line-height: 1.25;
  font-weight: 780;
  letter-spacing: -.025em;
}
.assistant-welcome-copy {
  margin: .48rem 0 0;
  max-width: 850px;
  color: #475569;
  font-size: .94rem;
  line-height: 1.65;
}
.assistant-section-label {
  margin: .9rem 0 .55rem;
  color: #334155;
  font-size: .82rem;
  font-weight: 800;
  letter-spacing: .045em;
}
.assistant-note {
  padding: .72rem .95rem;
  margin: .6rem 0 .7rem;
  border: 1px solid #bfdbfe;
  border-left: 4px solid #3b82f6;
  border-radius: 12px;
  background: #eff6ff;
  color: #1e3a8a;
  font-size: .85rem;
  line-height: 1.55;
}
.assistant-voice-note {
  padding: .62rem .9rem;
  margin: .5rem 0 .8rem;
  border: 1px solid #fde68a;
  border-radius: 12px;
  background: #fffbeb;
  color: #854d0e;
  font-size: .83rem;
}

/* Controls and suggestion cards */
.st-key-assistant_workspace .stButton > button {
  min-height: 48px;
  height: auto;
  white-space: normal;
  text-align: left;
  justify-content: flex-start;
  border-radius: 14px !important;
  padding: .72rem .9rem !important;
  line-height: 1.35;
}
.st-key-assistant_workspace .st-key-assistant_suggestions .stButton > button {
  min-height: 76px;
  align-items: flex-start;
  border: 1px solid #dce6f5 !important;
  background: linear-gradient(145deg, #fff 0%, #f8fbff 100%) !important;
  color: #1e3a5f !important;
  box-shadow: 0 3px 10px rgba(30, 64, 175, .045);
}
.st-key-assistant_workspace .st-key-assistant_suggestions .stButton > button:hover {
  border-color: #8db8ff !important;
  background: linear-gradient(145deg, #eff6ff 0%, #ecfeff 100%) !important;
  color: #1d4ed8 !important;
  transform: translateY(-2px);
  box-shadow: 0 10px 22px rgba(37, 99, 235, .10);
}
.st-key-assistant_workspace .st-key-assistant_suggestions [data-testid="stHorizontalBlock"] {
  gap: .75rem;
}
.st-key-assistant_workspace [data-testid="stToggle"] label {
  font-weight: 650;
  color: #334155;
}

/* Conversation messages: comfortable line length, clear contrast, subtle depth. */
.st-key-assistant_workspace [data-testid="stChatMessage"] {
  padding: 1rem 1.1rem;
  margin: .65rem 0;
  border: 1px solid #e1e8f2;
  border-radius: 19px;
  background: rgba(255,255,255,.96);
  box-shadow: 0 5px 20px rgba(15, 23, 42, .045);
  animation: assistant-message-in .22s ease-out both;
}
.st-key-assistant_workspace [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
  color: #243247;
  font-size: .97rem;
  line-height: 1.72;
}
.st-key-assistant_workspace [data-testid="stChatMessage"] p {
  margin-bottom: .55rem;
}
.st-key-assistant_workspace [data-testid="stChatMessage"] ul,
.st-key-assistant_workspace [data-testid="stChatMessage"] ol {
  padding-left: 1.3rem;
  margin: .35rem 0 .65rem;
}
.st-key-assistant_workspace [data-testid="stChatMessage"] a {
  color: #1d4ed8;
  font-weight: 700;
  text-underline-offset: 3px;
}
.st-key-assistant_workspace [data-testid="stChatMessage"] code {
  padding: .1rem .3rem;
  border-radius: 5px;
  background: #f1f5f9;
}

/* Chat input is deliberately prominent and easy to focus. */
div[data-testid="stChatInput"] {
  padding: .45rem;
  border: 1px solid #b9cdec !important;
  border-radius: 20px !important;
  background: #fff !important;
  box-shadow: 0 10px 30px rgba(37, 99, 235, .12) !important;
  transition: border-color .18s ease, box-shadow .18s ease;
}
div[data-testid="stChatInput"]:focus-within {
  border-color: #4f8df7 !important;
  box-shadow: 0 0 0 4px rgba(59,130,246,.12), 0 12px 32px rgba(37,99,235,.15) !important;
}
div[data-testid="stChatInput"] textarea {
  min-height: 48px;
  padding: .85rem .9rem !important;
  background: #fff !important;
  color: #172554 !important;
  font-size: .97rem !important;
  line-height: 1.5 !important;
}
div[data-testid="stChatInput"] textarea::placeholder { color: #718096 !important; }
div[data-testid="stChatInput"] button {
  border-radius: 13px !important;
  background: linear-gradient(135deg, #2563eb, #0f9b8e) !important;
  color: white !important;
}

/* Link/listen/new-chat controls */
.st-key-assistant_workspace .stButton > button[kind="secondary"] {
  border-color: #cbd5e1 !important;
}
.st-key-assistant_workspace .stButton > button:focus-visible,
div[data-testid="stChatInput"]:focus-within {
  outline-offset: 3px;
}

@keyframes assistant-message-in {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
@media (max-width: 800px) {
  div[data-testid="stMainBlockContainer"]:has(.st-key-assistant_workspace) {
    padding: .7rem .85rem 1rem !important;
  }
  .assistant-hero { align-items: flex-start; gap: .8rem; border-radius: 20px; }
  .assistant-hero-icon { flex-basis: 46px; width: 46px; height: 46px; border-radius: 14px; font-size: 1.35rem; }
  .assistant-hero-description { font-size: .9rem; }
  .assistant-feature-pills { gap: .35rem; }
  .assistant-feature-pills span { font-size: .7rem; }
  .st-key-assistant_workspace .st-key-assistant_suggestions .stButton > button { min-height: 66px; padding: .65rem .7rem !important; }
  .st-key-assistant_workspace [data-testid="stChatMessage"] { padding: .8rem; border-radius: 15px; }
}
@media (max-width: 520px) {
  .assistant-hero { padding: 1rem; }
  .assistant-hero-icon { display: none; }
  .assistant-feature-pills span { padding: .28rem .5rem; }
  .st-key-assistant_workspace .st-key-assistant_suggestions [data-testid="stHorizontalBlock"] {
    gap: .45rem;
    flex-wrap: wrap !important;
  }
  .st-key-assistant_workspace .st-key-assistant_suggestions [data-testid="column"] {
    flex: 1 1 100% !important;
    min-width: 100% !important;
    width: 100% !important;
  }
}
@media (prefers-reduced-motion: reduce) {
  .st-key-assistant_workspace [data-testid="stChatMessage"] { animation: none !important; }
  .st-key-assistant_workspace .stButton > button,
  div[data-testid="stChatInput"] { transition: none !important; }
}
</style>
""")


EXAMPLES = [
    "Which B.Tech courses are available?",
    "BCA ki fees kitni hai?",
    "Am I eligible for B.Tech CSE with 75% and PCM?",
    "What is the admission procedure?",
    "Tell me about BBA",
    "Courses under 1 lakh per year",
]


with st.container(key="assistant_workspace"):
    # Dedicated assistant header, independent of the college site-wide footer.
    st.html("""
    <section class="assistant-hero" aria-label="College admission assistant introduction">
      <div class="assistant-hero-icon" aria-hidden="true">✦</div>
      <div class="assistant-hero-copy">
        <div class="assistant-eyebrow">STUDENT SUPPORT · COURSE DISCOVERY · ADMISSIONS</div>
        <h1 class="assistant-hero-title">College Admission Assistant</h1>
        <p class="assistant-hero-description">Get help exploring courses, understanding fees and eligibility, and navigating the admission process. Ask naturally in English, Hindi, or Hinglish.</p>
        <div class="assistant-feature-pills">
          <span>College information</span><span>Course guidance</span><span>Voice answers</span>
        </div>
      </div>
    </section>
    """)

    control_cols = st.columns([1.3, 1], vertical_alignment="center", gap="small")
    with control_cols[0]:
        st.toggle(
            "Read answers aloud",
            value=False,
            key="auto_speak",
            disabled=not VOICE_READY,
            help="Automatically play assistant answers when voice synthesis is configured.",
        )
    with control_cols[1]:
        if messages:
            st.button(
                "New conversation",
                key="assistant_new_conversation",
                on_click=clear,
                icon=":material/add_comment:",
                use_container_width=True,
            )
        else:
            st.markdown(
                '<div style="text-align:right;color:#64748b;font-size:.8rem;padding:.45rem 0">'
                'Your conversation stays on this page</div>',
                unsafe_allow_html=True,
            )

    st.html("""
    <div class="assistant-note">
      <strong>Helpful and grounded answers.</strong> Responses use the college prototype’s available course and faculty information. Please confirm important admission decisions with the college.
    </div>
    """)

    if not VOICE_READY:
        st.html("""
        <div class="assistant-voice-note">
          <strong>Voice playback is not configured yet.</strong> Text chat remains available. Configure <code>GNANI_API_KEY</code> in your local environment or Streamlit Secrets to enable speech synthesis.
        </div>
        """)

    # Suggested prompts are genuine buttons wired to the same handler as before.
    if not messages:
        st.html("""
        <section class="assistant-welcome" aria-label="Suggested assistant questions">
          <div class="assistant-welcome-kicker">Start here</div>
          <h2 class="assistant-welcome-title">What would you like to know?</h2>
          <p class="assistant-welcome-copy">Choose a popular question below or type your own message. You can ask a follow-up whenever you need more detail.</p>
          <div class="assistant-section-label">POPULAR QUESTIONS</div>
        </section>
        """)
        with st.container(key="assistant_suggestions"):
            for row_start in (0, 3):
                cols = st.columns(3, gap="small")
                for col, q in zip(cols, EXAMPLES[row_start:row_start + 3]):
                    with col:
                        col.button(
                            q,
                            key=f"ex_{q}",
                            on_click=handle,
                            args=(q,),
                            use_container_width=True,
                        )

    # Preserve the original Streamlit chat input and response flow.
    prompt = st.chat_input(
        "Message the assistant… Ask about courses, fees, eligibility or admissions"
    )
    if prompt:
        handle(prompt)

    # --------------------------------------------------------- render messages
    speak_target = st.session_state.pop("speak_index", None)
    last_bot = max(
        (index for index, message in enumerate(messages) if message["role"] == "assistant"),
        default=None,
    )

    for index, message in enumerate(messages):
        with st.chat_message(
            message["role"],
            avatar=BOT_AVATAR if message["role"] == "assistant" else USER_AVATAR,
        ):
            if message.get("animate"):
                st.write_stream(typewriter(message["text"]))
                message["animate"] = False
            else:
                st.markdown(message["text"])

            if message["role"] != "assistant":
                continue

            # Optional link button to courses/faculty/admissions.
            if index == last_bot and message.get("link"):
                label, page = message["link"]
                clean_page = page.lstrip("/")
                try:
                    st.page_link(clean_page, label=f"📄 {label}")
                except Exception:
                    pass

            # Existing Gnani audio playback action, unchanged in behavior.
            if VOICE_READY:
                def _request_voice(idx=index):
                    st.session_state["speak_index"] = idx

                st.button(
                    "Listen to answer",
                    key=f"listen_{index}",
                    icon=":material/volume_up:",
                    on_click=_request_voice,
                )

                if speak_target == index:
                    language = message.get("lang", "en")
                    try:
                        with st.spinner("Preparing audio answer…"):
                            wav_data = tts.synthesize_speech(
                                message["text"], lang=language, api_key=VOICE_KEY
                            )
                        st.audio(wav_data, format="audio/wav", autoplay=True)
                    except tts.TTSError as error:
                        st.warning(str(error), icon=":material/error:")
