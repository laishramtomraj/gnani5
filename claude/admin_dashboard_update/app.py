import streamlit as st

import catalogue_db
import content_db
from components import brand_header, footer

catalogue_db.sync()   # keep the course list in step with college.db on every run
content_db.sync()     # keep the PUBLISHED website content (college details, achievements) in step too

# Private administrator area: /?admin . It never shows the public header, footer or menu.
if "admin" in st.query_params:
    import admin_ui

    st.set_page_config(page_title="Administration", page_icon="🔒", layout="wide")
    admin_ui.run()
    st.stop()

st.set_page_config(page_title="College Name | Discover Your Future", page_icon="🎓", layout="wide")
pages = [
    st.Page("views/home.py", title="Home", icon=":material/home:", default=True),
    st.Page("views/courses.py", title="Courses", icon=":material/school:"),
    st.Page("views/faculty.py", title="Faculty", icon=":material/groups:"),
    st.Page("views/about.py", title="About Us", icon=":material/info:"),
    st.Page("views/admissions.py", title="Admissions", icon=":material/how_to_reg:"),
    st.Page("views/contact.py", title="Contact", icon=":material/mail:"),
    st.Page("views/assistant.py", title="Assistant", icon=":material/smart_toy:"),
]

nav = st.navigation(pages, position="top")

brand_header()   # text emblem + visible "Apply Now" button on every page
nav.run()        # runs the selected page
footer()
