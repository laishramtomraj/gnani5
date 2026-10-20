import html
from datetime import date

import streamlit as st

from data import COLLEGE

TBA = "To be added"
_LINK = "color:inherit;font-weight:600;text-decoration:underline"   # follows the theme text colour


def _link(kind: str, value: str) -> str:
    """Clickable tel: or mailto: link. Spaces in a phone number are dropped from the href only."""
    href = "tel:" + "".join(ch for ch in value if ch.isdigit() or ch == "+") if kind == "tel" else f"mailto:{value}"
    return f'<a href="{html.escape(href, quote=True)}" style="{_LINK}">{html.escape(value)}</a>'


def contact_item(label: str, value: str | None, kind: str):
    """Label above a clickable phone number or email (kind is 'tel' or 'mailto')."""
    link = _link(kind, value) if value else html.escape(TBA)
    st.html(f'<div><div style="font-size:0.8rem;letter-spacing:0.05em;opacity:0.7">{html.escape(label.upper())}</div>'
            f'<div>{link}</div></div>')


def contact_line(label: str, value: str | None, kind: str):
    """Compact one-line version for the footer."""
    link = _link(kind, value) if value else html.escape(TBA)
    st.html(f'<div style="font-size:0.875rem;opacity:0.85">{html.escape(label)}: {link}</div>')


def brand_header():
    """Text emblem + college name (left) and a visible Apply Now button (right)."""
    left, right = st.columns([4, 1], vertical_alignment="center")
    with left:
        st.markdown(f"## :material/account_balance: {COLLEGE['name']}")
    with right:
        if st.button("Apply Now", type="primary", width="stretch", key="header_apply"):
            st.switch_page("views/admissions.py")
    st.divider()


def section_header(eyebrow: str, title: str, subtitle: str | None = None):
    st.caption(eyebrow.upper())
    st.header(title, anchor=False)
    if subtitle:
        st.write(subtitle)


def footer():
    st.write("")
    st.divider()                                   # thin light-grey line above the footer
    left, middle, right = st.columns([2, 1, 1.5])
    with left:
        st.markdown(f"**{COLLEGE['name']}**")
        st.caption(f"Address: {COLLEGE['address'] or TBA}")
        contact_line("Phone", COLLEGE["phone"], "tel")
        contact_line("Email", COLLEGE["email"], "mailto")
    with middle:
        st.markdown("**Quick links**")
        st.page_link("views/courses.py", label="Courses")
        st.page_link("views/admissions.py", label="Admissions")
        st.page_link("views/faculty.py", label="Faculty")
    with right:
        st.markdown("**Contact Us**")
        contact_line("Admissions helpline", COLLEGE["admissions_phone"], "tel")
        contact_line("Admissions email", COLLEGE["admissions_email"], "mailto")
        st.caption(f"Office hours: {COLLEGE['office_hours'] or TBA}")
        st.page_link("views/contact.py", label="Contact Us", icon=":material/mail:")
    st.caption("Contact details are sample data for this prototype.")
    st.caption(f"© {date.today().year} {COLLEGE['name']}. All rights reserved.")   # muted grey, left
    st.page_link("views/eligibility.py", label="Eligibility Checker")