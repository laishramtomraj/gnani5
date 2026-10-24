import streamlit as st

from components import section_header
from data import ACHIEVEMENTS, COLLEGE

section_header("About us", f"About {COLLEGE['name']}")

overview, mission, accreditation = st.tabs(["Overview", "Vision & Mission", "Accreditations"])

with overview:
    if COLLEGE.get("description"):
        st.write(COLLEGE["description"])
    else:
        st.write("The college's history, campus and approach to education will appear here.")
        st.caption("To be supplied by the college.")
with mission:
    if COLLEGE.get("vision") or COLLEGE.get("mission"):
        left, right = st.columns(2)
        if COLLEGE.get("vision"):
            left.markdown("#### Vision")
            left.write(COLLEGE["vision"])
        if COLLEGE.get("mission"):
            right.markdown("#### Mission")
            right.write(COLLEGE["mission"])
    else:
        st.write("Vision and mission statements will appear here.")
        st.caption("To be supplied by the college.")
with accreditation:
    if COLLEGE.get("accreditations_text"):
        st.write(COLLEGE["accreditations_text"])
    elif not ACHIEVEMENTS:
        st.write("Accreditations, approvals and recognitions will appear here.")
        st.caption("Must be verified before publishing. Nothing is invented.")
    if ACHIEVEMENTS:
        st.markdown("#### Achievements")
        for item in ACHIEVEMENTS:
            with st.container(border=True):
                picture, text = st.columns([1, 3], vertical_alignment="center") if item.get("image") else (None, st.container())
                if picture is not None:
                    picture.image(str(item["image"]), width="stretch")
                with text:
                    st.markdown(f"**{item['label']}** — {item['value']}")
                    if item.get("source"):
                        st.write(item["source"])
                    st.caption(" · ".join(x for x in (item.get("category"), item.get("date")) if x))
