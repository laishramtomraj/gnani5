import streamlit as st

from data import COLLEGE

st.title("Contact", anchor=False)

TBA = "To be added"
items = [
    (":material/location_on:", "Address", COLLEGE["address"]),
    (":material/call:", "Phone", COLLEGE["phone"]),
    (":material/mail:", "Email", COLLEGE["email"]),
    (":material/schedule:", "Office hours", COLLEGE["office_hours"]),
]
for col, (icon, label, value) in zip(st.columns(4), items):
    with col.container(border=True):
        st.markdown(f"#### {icon} {label}")
        st.write(value or TBA)

# Extra details appear only once the college has supplied them.
extra = [(":material/support_agent:", "Admissions helpline", COLLEGE.get("admissions_phone")),
         (":material/alternate_email:", "Admissions email", COLLEGE.get("admissions_email"))]
extra = [item for item in extra if item[2]]
if extra:
    for col, (icon, label, value) in zip(st.columns(4), extra):
        with col.container(border=True):
            st.markdown(f"#### {icon} {label}")
            st.write(value)
links = [(name, COLLEGE.get(key)) for name, key in (("Facebook", "facebook"), ("Instagram", "instagram"), ("LinkedIn", "linkedin"),
                                                    ("YouTube", "youtube"), ("X", "x_twitter")) if COLLEGE.get(key)]
if links:
    st.markdown("**Follow us:** " + " · ".join(f"[{name}]({url})" for name, url in links))

st.caption("Contact details must come from the college.")
