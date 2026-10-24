# app.py
from __future__ import annotations

import os
import socket
import subprocess
import sys
from pathlib import Path

import streamlit as st

from config import get_gnani_api_key

# Validate the key early; this gives a clear deployment error if missing.
try:
    get_gnani_api_key()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()


ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def ensure_api_running():
    """Start the local API only during local development."""
    if os.getenv("RENDER") == "true":
        return

    api_url = os.getenv("ASSISTANT_API_URL", "")
    if api_url:
        # In production, use the separately deployed API service.
        return

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        is_running = s.connect_ex(("127.0.0.1", 8000)) == 0

    if not is_running:
        api_path = ROOT_DIR / "api.py"
        if api_path.exists():
            subprocess.Popen(
                [sys.executable, str(api_path)],
                cwd=str(ROOT_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )


ensure_api_running()

st.set_page_config(
    page_title="College Name | Discover Your Future",
    page_icon="🎓",
    layout="wide",
)

pages = [
    st.Page("views/home.py", title="Home", icon=":material/home:", default=True),
    st.Page("views/courses.py", title="Courses", icon=":material/school:"),
    st.Page("views/faculty.py", title="Faculty", icon=":material/groups:"),
    st.Page("views/about.py", title="About Us", icon=":material/info:"),
    st.Page("views/admissions.py", title="Admissions", icon=":material/how_to_reg:"),
    st.Page("views/eligibility.py", title="Eligibility", icon=":material/fact_check:"),
    st.Page("views/contact.py", title="Contact", icon=":material/mail:"),
    st.Page("views/assistant.py", title="Assistant", icon=":material/smart_toy:"),
]

nav = st.navigation(pages, position="top")

from components import brand_header, footer

brand_header()
nav.run()
footer()