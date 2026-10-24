import streamlit as st

import registration_ui
from components import section_header

section_header("Admissions", "Register for a Course",
               "Choose a course, fill in the form, review your answers and submit. You can also check the status of a "
               "registration you already submitted.")
registration_ui.render_registration_portal()
