"""gnani_tts.py - spoken answers through the Gnani Timbre text-to-speech REST API.

Documented contract (https://docs.gnani.ai/api/TTS/tts-inference):
  POST https://api.vachana.ai/api/v1/tts/inference        header  X-API-Key-ID: <your key>
  JSON body: text, model ("timbre-v2.5"), voice, language, speed (0.85-1.15), audio_config{...}
  200 -> binary audio in the requested container; 400 / 403 / 429 / 500 / 503 -> error JSON.
Language codes used: en-IN (English), hi-IN (Hindi), hi-en (Hinglish; retried as "auto" if rejected).
The API normalises numbers, rupee amounts and percentages itself, so they are sent as written;
only Markdown symbols are removed (for example "*" would be read as "multiplied by").

The API key is read on the SERVER ONLY, from the environment or Streamlit secrets. It is never
placed in the page, in cached values or in any error message.
"""
from __future__ import annotations

import os
import re

import requests

ENDPOINT = "https://api.vachana.ai/api/v1/tts/inference"
DEFAULT_MODEL = "timbre-v2.5"
LANGUAGE_CODE = {"en": "en-IN", "hi": "hi-IN", "hn": "hi-en"}
# Example voices named in the Gnani documentation (Hindi, English, Hinglish). Change them in the settings.
DEFAULT_VOICE = {"en": "Kaveri", "hi": "Nalini", "hn": "Poorvi"}
SPEED_RANGE = (0.85, 1.15)
MAX_SPOKEN_CHARS = 700
AUDIO_CONFIG = {"sample_rate": 24000, "num_channels": 1, "sample_width": 2, "encoding": "linear_pcm", "container": "wav"}

SEE_SCREEN = {
    "en": "The full details are shown on the screen.",
    "hi": "पूरी जानकारी स्क्रीन पर दिखाई गई है।",
    "hn": "Poori jaankari screen par dikhayi gayi hai.",
}
_ERRORS = {
    400: "The voice service could not use this text or voice. Please check the voice name in your settings.",
    401: "The voice service did not accept the API key.",
    403: "The voice service refused the request. Check the API key, that your account has text-to-speech access, and your credits.",
    429: "The voice service is busy (rate limit). Please try again in a moment.",
}


class TTSError(Exception):
    """A user-safe message. It never contains the API key."""


# ------------------------------------------------------------------ settings
def load_config(secrets: dict | None = None) -> dict:
    """Read settings from environment variables first, then Streamlit secrets (flat keys)."""
    secrets = secrets or {}

    def get(name, default=None):
        value = os.environ.get(name) or secrets.get(name)
        return str(value).strip() if value not in (None, "") else default

    try:
        speed = float(get("GNANI_TTS_SPEED", "1.0"))
    except ValueError:
        speed = 1.0
    return {
        "api_key": get("GNANI_API_KEY"),
        "model": get("GNANI_TTS_MODEL", DEFAULT_MODEL),
        "speed": min(max(speed, SPEED_RANGE[0]), SPEED_RANGE[1]),
        "voices": {lang: get(f"GNANI_VOICE_{lang.upper()}", DEFAULT_VOICE[lang]) for lang in DEFAULT_VOICE},
    }


# ------------------------------------------------------------ text for speech
def _plain(markdown: str) -> str:
    """Markdown -> plain sentences the voice can read."""
    out = []
    for line in markdown.splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+\.)\s+", "", line.strip())
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        line = re.sub(r"[`*_#>]", "", line)
        line = line.replace("—", ", ").replace("·", ",").replace("&", " and ")
        line = re.sub(r"\s+", " ", line).strip()
        line = re.sub(r"\s+,", ",", line)
        if not line:
            continue
        out.append(line if line[-1] in ".!?:;।)" else line + ".")
    return " ".join(out)


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "), cut.rfind("।"))
    return cut[: end + 1] if end > 0 else cut.rstrip() + "."


def speech_text(reply_text: str, lang: str, limit: int = MAX_SPOKEN_CHARS) -> str:
    """The assistant's reply, cleaned for speech. Long answers are shortened to the direct answer,
    a pointer to the screen and the prototype-data note, so the note is always spoken."""
    paras = [p for p in re.split(r"\n\s*\n", reply_text.strip()) if p.strip()]
    if not paras:
        return ""
    note = next((p for p in paras if p.startswith("Note: This is illustrative prototype data")), None)
    spoken_note = ""
    if note:
        inner = re.search(r"\((.+)\)\s*$", note, re.S)
        spoken_note = _plain(inner.group(1)) if (lang != "en" and inner) else _plain(note)
        paras = [p for p in paras if p is not note]
    first = paras[0]
    spoken_numbers = set(re.findall(r"\d[\d,.]*\d|\d", first))
    kept = [first]
    for para in paras[1:]:                  # skip bullet lines that only repeat figures already in the direct answer
        lines = []
        for line in para.splitlines():
            numbers = re.findall(r"\d[\d,.]*\d|\d", line)
            if not (numbers and all(n in spoken_numbers for n in numbers)):
                lines.append(line)
        if lines:
            kept.append("\n".join(lines))
    body = [_plain(p) for p in kept if _plain(p)]
    parts = body + ([spoken_note] if spoken_note else [])
    full = " ".join(parts)
    if len(full) <= limit:
        return full
    head = _truncate(body[0], max(limit - len(spoken_note) - len(SEE_SCREEN[lang]) - 2, 120)) if body else ""
    return " ".join(x for x in (head, SEE_SCREEN[lang], spoken_note) if x)


# ------------------------------------------------------------------ the call
def synthesize(text: str, lang: str, api_key: str | None, model: str = DEFAULT_MODEL, voice: str | None = None,
               speed: float = 1.0, timeout: int = 30, post=None) -> bytes:
    """Return WAV audio for `text`. Raises TTSError with a safe message on any failure."""
    if not api_key:
        raise TTSError("Voice is not set up: no Gnani API key was found.")
    text = text.strip()
    if not text:
        raise TTSError("There is nothing to speak.")
    post = post or requests.post
    voice = voice or DEFAULT_VOICE.get(lang, DEFAULT_VOICE["en"])

    def call(language: str):
        body = {"text": text, "model": model, "voice": voice, "language": language,
                "speed": min(max(float(speed), SPEED_RANGE[0]), SPEED_RANGE[1]), "audio_config": AUDIO_CONFIG}
        try:
            return post(ENDPOINT, headers={"Content-Type": "application/json", "X-API-Key-ID": api_key},
                        json=body, timeout=timeout)
        except requests.exceptions.Timeout:
            raise TTSError("The voice service took too long to respond. Please try again.") from None
        except requests.exceptions.RequestException:
            raise TTSError("I couldn't reach the voice service. Check your internet connection.") from None

    response = call(LANGUAGE_CODE.get(lang, "auto"))
    if response.status_code == 400 and lang == "hn":      # Hinglish code not accepted: let the API detect the language
        response = call("auto")
    if response.status_code == 200:
        audio = response.content
        if audio[:4] == b"RIFF":
            return audio
        raise TTSError("The voice service returned something that is not audio.")
    raise TTSError(_ERRORS.get(response.status_code, "The voice service is temporarily unavailable. Please try again later."))
