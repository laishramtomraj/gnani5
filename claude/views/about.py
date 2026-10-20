import streamlit as st

from components import section_header
from data import COLLEGE

section_header("About us", f"About {COLLEGE['name']}")

overview, mission, accreditation = st.tabs(["Overview", "Vision & Mission", "Accreditations"])

with overview:
    st.write("The college's history, campus and approach to education will appear here.")
    st.caption("To be supplied by the college.")
with mission:
    st.write("Vision and mission statements will appear here.")
    st.caption("To be supplied by the college.")
with accreditation:
    st.write("Accreditations, approvals and recognitions will appear here.")
    st.caption("Must be verified before publishing. Nothing is invented.")