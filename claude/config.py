# config.py
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Loads .env only if it exists (local dev)
load_dotenv(BASE_DIR / ".env")


def get_gnani_api_key() -> str:
    """Return the Gnani API key from st.secrets, os.environ, or .env.
    
    Returns an empty string or key without crashing, allowing graceful UI warnings.
    """
    # 1. Check os.environ (set by local .env or cloud environment)
    api_key = os.getenv("GNANI_API_KEY", "")

    # 2. Check Streamlit Cloud Secrets
    if not api_key:
        try:
            import streamlit as st
            if "GNANI_API_KEY" in st.secrets:
                api_key = st.secrets["GNANI_API_KEY"]
                # Also set in os.environ so all sub-modules can see it
                os.environ["GNANI_API_KEY"] = api_key
        except Exception:
            pass

    return api_key.strip()