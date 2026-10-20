import streamlit as st

from registration_ui import render_registration_portal

st.title("Admissions", anchor=False)

# --------------------------------------------------- selected course (carried forward)
selected = st.session_state.get("selected_course")
if selected:
    with st.container(border=True):
        left, right = st.columns([3, 1], vertical_alignment="center")
        left.markdown(f"**Selected course:** {selected}")
        if right.button("Change course", width="stretch", key="change_course"):
            st.switch_page("views/courses.py")
else:
    st.info("You haven't selected a course yet.", icon=":material/info:")
    if st.button("Browse courses", type="primary", key="browse_courses"):
        st.switch_page("views/courses.py")

# ------------------------------------------------------------------ process
st.subheader("How admission works", anchor=False)
steps = [
    ("Select a course", "Browse the programmes and choose the one you are interested in."),
    ("Complete the registration form", "Fill in your details. Your selected course carries forward automatically."),
    ("Submit for review", "Your registration is submitted and reviewed by the college."),
    ("Approval by the college", "Registration approval is granted through the college's own process."),
    ("Subsequent admission requirements", "Approved students proceed with the remaining admission formalities."),
]
for n, (title, text) in enumerate(steps, start=1):
    with st.container(border=True):
        st.markdown(f"**Step {n}: {title}**")
        st.write(text)

st.caption("Registration approval and admission decisions are made only by the college, never by this website or an AI assistant.")

# ------------------------------------------------------------- registration
st.subheader("Registration", anchor=False)
render_registration_portal()