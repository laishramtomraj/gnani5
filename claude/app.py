import streamlit as st
import catalogue_db
from components import brand_header, footer
catalogue_db.sync() 
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

brand_header()   # text emblem + visible "Apply Now" button on every page
nav.run()        # runs the selected page
footer()