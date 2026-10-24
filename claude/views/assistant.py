import streamlit as st
import streamlit.components.v1 as components

st.title("College Admission Assistant", anchor=False)
st.caption(
    "Ground truth answers powered by the college course & faculty database with Gnani TTS voice support."
)

# Embed the exact api.py HTML/CSS/JS frontend inside the page
components.iframe(
    src="http://127.0.0.1:8000",
    height=750,
    scrolling=True
)