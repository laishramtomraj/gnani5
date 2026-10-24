# config.py
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Loads .env only if it exists; on deployment, platform env vars are used.
load_dotenv(BASE_DIR / ".env")

GNANI_API_KEY = os.getenv("GNANI_API_KEY", "")


def get_gnani_api_key() -> str:
    """Return the Gnani API key from environment/secrets."""
    api_key = os.getenv("GNANI_API_KEY", GNANI_API_KEY)

    if not api_key:
        raise RuntimeError(
            "GNANI_API_KEY is missing.\n"
            "For local development, add it to .env.\n"
            "For deployment, add it in your hosting platform's Secrets/Environment Variables."
        )

    return api_key