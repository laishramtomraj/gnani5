import streamlit as st

from components import TBA, contact_item
from data import COLLEGE

st.title("Contact Us", anchor=False)
st.info(
    "These are sample contact details for this prototype. They are placeholders and do not belong "
    "to a real college.",
    icon=":material/info:",
)

top = st.columns(2)
bottom = st.columns(2)

with top[0].container(border=True):
    st.markdown("#### :material/location_on: Address")
    st.write(COLLEGE["address"] or TBA)

with top[1].container(border=True):
    st.markdown("#### :material/schedule: Office hours")
    st.write(COLLEGE["office_hours"] or TBA)

with bottom[0].container(border=True):
    st.markdown("#### :material/call: General enquiries")
    contact_item("Phone", COLLEGE["phone"], "tel")
    contact_item("Email", COLLEGE["email"], "mailto")

with bottom[1].container(border=True):
    st.markdown("#### :material/how_to_reg: Admissions support")
    contact_item("Admissions helpline", COLLEGE["admissions_phone"], "tel")
    contact_item("Admissions email", COLLEGE["admissions_email"], "mailto")
    st.page_link("views/admissions.py", label="Go to Admissions", icon=":material/arrow_forward:")

st.caption("Contact details must come from the college.")