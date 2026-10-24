"""assistant/tts.py - Text-to-Speech integration using Gnani AI Timbre API."""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Callable

import requests

ENDPOINT = "https://api.vachana.ai/api/v1/tts/inference"
DEFAULT_MODEL = "timbre-v2.5"
DEFAULT_VOICES = {"en": "Kaveri", "hi": "Nalini", "hn": "Poorvi"}
LANGUAGE_CODES = {"en": "en-IN", "hi": "hi-IN", "hn": "hi-en"}
AUDIO_CONFIG = {
    "sample_rate": 24000,
    "num_channels": 1,
    "sample_width": 2,
    "encoding": "linear_pcm",
    "container": "wav",
}
MAX_CHARS = 700

LOG_FILE = Path(__file__).resolve().parent / "tts_errors.log"
logger = logging.getLogger("assistant.tts")
if not logger.handlers:
    logger.setLevel(logging.WARNING)
    handler = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
    logger.addHandler(handler)

_AUDIO_CACHE: dict[str, bytes] = {}


class TTSError(Exception):
    pass


def get_api_key() -> str | None:
    key = os.environ.get("GNANI_API_KEY")
    return key.strip() if key else None


def clean_text_for_speech(markdown_text: str, limit: int = MAX_CHARS) -> str:
    if not markdown_text:
        return ""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", markdown_text)
    text = re.sub(r"[*_`#>~]", "", text)
    text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) <= limit:
        return text

    cut = text[:limit]
    last_punc = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "), cut.rfind("। "))
    if last_punc > 50:
        return cut[: last_punc + 1].strip() + " The full details are shown on screen."
    return cut.rstrip() + "... The full details are shown on screen."


def synthesize_speech(
    text: str,
    lang: str = "en",
    speed: float = 1.0,
    api_key: str | None = None,
    post_fn: Callable[..., Any] | None = None,
) -> bytes:
    key = get_api_key() if api_key is None else (api_key.strip() if api_key else None)
    if not key:
        logger.warning("Synthesis attempted without GNANI_API_KEY set.")
        raise TTSError("Voice service is unavailable: GNANI_API_KEY is not configured.")

    clean_text = clean_text_for_speech(text)
    if not clean_text:
        raise TTSError("No speakable text provided.")

    lang_normalized = "hi" if lang == "hi" else ("hn" if lang == "hn" else "en")
    voice = DEFAULT_VOICES.get(lang_normalized, DEFAULT_VOICES["en"])
    lang_code = LANGUAGE_CODES.get(lang_normalized, "en-IN")

    cache_key = f"{lang_normalized}:{voice}:{speed}:{clean_text}"
    if cache_key in _AUDIO_CACHE:
        return _AUDIO_CACHE[cache_key]

    caller = post_fn or requests.post

    def _call_api(target_lang: str):
        payload = {
            "text": clean_text,
            "model": DEFAULT_MODEL,
            "voice": voice,
            "language": target_lang,
            "speed": min(max(float(speed), 0.85), 1.15),
            "audio_config": AUDIO_CONFIG,
        }
        headers = {"Content-Type": "application/json", "X-API-Key-ID": key}
        return caller(ENDPOINT, headers=headers, json=payload, timeout=20)

    try:
        response = _call_api(lang_code)
        if response.status_code == 400 and lang_normalized == "hn":
            response = _call_api("auto")
    except requests.exceptions.Timeout:
        logger.error("Gnani TTS timeout while connecting to endpoint.")
        raise TTSError("The voice service timed out. Please try again.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Gnani TTS network error: {type(e).__name__}")
        raise TTSError("Could not reach the voice service. Please check network connection.")

    if response.status_code == 200:
        data = response.content
        if data[:4] == b"RIFF":
            _AUDIO_CACHE[cache_key] = data
            return data
        logger.error("Gnani TTS response was not valid WAV audio.")
        raise TTSError("The voice service returned an invalid audio format.")

    err_map = {
        400: "The voice service could not process this text or voice configuration.",
        401: "The voice service did not accept the API key. Please check your credentials.",
        403: "Access forbidden by voice service. Check account balance or permissions.",
        429: "Voice service rate limit reached. Please wait a moment before retrying.",
        500: "The voice service encountered an internal error. Please try again later.",
        503: "The voice service is temporarily unavailable.",
    }
    raise TTSError(err_map.get(response.status_code, "Voice service error occurred."))