import streamlit as st

from components import section_header
from data import ACHIEVEMENTS, COLLEGE, COURSES, DATA_IS_SAMPLE, ILLUSTRATIVE_ACHIEVEMENTS
from hero import render_hero

# ------------------------------------------------------------------ TOP ALERT BANNER
st.html("""
<div style="
    background: linear-gradient(90deg, #19A7A0 0%, #0072B2 100%);
    padding: 10px 20px;
    border-radius: 50px;
    color: white;
    font-size: 0.95rem;
    font-weight: 600;
    text-align: center;
    box-shadow: 0 4px 12px rgba(25, 167, 160, 0.25);
    margin-bottom: 1.5rem;
">
    🎓 Admissions Open for Academic Session 2026–27 • Merit & Entrance Pathways Available
</div>
""")

# ------------------------------------------------------------------ HERO BANNER
render_hero()

st.write("")

# --------------------------------------------------------- ATTENTIVE AI ASSISTANT CALLOUT
with st.container(border=True):
    col_ai_left, col_ai_right = st.columns([2.5, 1.2], vertical_alignment="center")
    with col_ai_left:
        st.markdown("### 🤖 Have Questions About Admissions, Eligibility or Fees?")
        st.write(
            "Our automated **College Admission Assistant** is trained on the college course catalog, "
            "seat capacity, tuition fees, and faculty records with **Gnani Voice Speech** support."
        )
        st.caption("Try asking in English, Hindi, or Hinglish!")
    with col_ai_right:
        if st.button("💬 Chat with AI Assistant", type="primary", use_container_width=True, key="home_ai_btn"):
            st.switch_page("views/assistant.py")

st.write("")

# --------------------------------------------------------------- WHY CHOOSE US (COLORFUL CARDS)
section_header("Why Us", "Education That Prepares You for What's Next")

pillars = [
    {
        "icon": "🎓",
        "title": "Academic Depth",
        "text": "Curriculums designed with industry experts, balancing theory and modern laboratory practice.",
        "bg": "#E8F4FD",
        "border": "#2196F3",
    },
    {
        "icon": "💡",
        "title": "Innovation & Labs",
        "text": "State-of-the-art incubation hubs encouraging real projects, patents, and technical competitions.",
        "bg": "#FFF9E6",
        "border": "#FFB300",
    },
    {
        "icon": "🤝",
        "title": "Personal Mentoring",
        "text": "Dedicated faculty advisors guiding career pathways, research papers, and internships.",
        "bg": "#E8F8F5",
        "border": "#19A7A0",
    },
    {
        "icon": "🚀",
        "title": "Placement Network",
        "text": "Active partnerships with top tech, engineering, and business organizations across India.",
        "bg": "#F5EEF8",
        "border": "#9C27B0",
    },
]

cols = st.columns(4)
for col, p in zip(cols, pillars):
    with col:
        st.html(f"""
        <div style="
            background-color: {p['bg']};
            border-left: 5px solid {p['border']};
            padding: 20px 16px;
            border-radius: 12px;
            min-height: 200px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            margin-bottom: 10px;
        ">
            <div style="font-size: 2rem; margin-bottom: 8px;">{p['icon']}</div>
            <div style="font-size: 1.15rem; font-weight: 700; color: #0B1F3F; margin-bottom: 8px;">{p['title']}</div>
            <div style="font-size: 0.9rem; color: #334E68; line-height: 1.45;">{p['text']}</div>
        </div>
        """)

st.write("")

# ---------------------------------------------------------- KEY ACHIEVEMENTS
section_header(
    "Milestones",
    "Campus Achievements & Metrics",
    "A snapshot of academic, placement, and research milestones.",
)

achievements = ACHIEVEMENTS or ILLUSTRATIVE_ACHIEVEMENTS

for row_start in range(0, len(achievements), 3):
    row = achievements[row_start:row_start + 3]
    for col, item in zip(st.columns(3), row):
        with col.container(border=True):
            st.markdown(f"#### {item['icon']} {item['title']}")
            st.metric(label="Current Record", value=item["value"], label_visibility="collapsed")
            st.write(item["description"])

st.write("")

# --------------------------------------------------------- PROGRAMMES SHOWCASE
section_header("Programmes", "Explore Academic Disciplines")
groups: dict[str, list[str]] = {}
for c in COURSES:
    groups.setdefault(c["category"], []).append(c["name"])

badge_colors = {
    "Engineering": ("#E3F2FD", "#1565C0"),
    "Management & Commerce": ("#EDE7F6", "#512DA8"),
    "Basic & Applied Sciences": ("#E0F2F1", "#00695C"),
}

for col, (category, names) in zip(st.columns(len(groups)), groups.items()):
    bg, fg = badge_colors.get(category, ("#F3F6FA", "#0B1F3F"))
    with col.container(border=True):
        st.html(f"""
        <div style="
            display: inline-block;
            background-color: {bg};
            color: {fg};
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            margin-bottom: 12px;
        ">
            {category.upper()}
        </div>
        """)
        st.markdown(f"### {len(names)} Programmes")
        shown = ", ".join(names[:3])
        extra = f" and {len(names) - 3} more" if len(names) > 3 else ""
        st.write(shown + extra)
        st.page_link("views/courses.py", label="View all courses", icon=":material/arrow_forward:")

st.write("")

# ------------------------------------------------------------ READY TO BEGIN CTA
st.html("""
<div style="
    background: linear-gradient(135deg, #0B1F3F 0%, #153E75 60%, #19A7A0 100%);
    border-radius: 18px;
    padding: 36px 32px;
    color: white;
    box-shadow: 0 10px 25px rgba(11, 31, 63, 0.2);
    margin-top: 1rem;
">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px;">
        <div style="max-width: 650px;">
            <div style="font-size: 1.8rem; font-weight: 800; margin-bottom: 8px;">Ready to Begin Your Journey?</div>
            <div style="font-size: 1rem; opacity: 0.9; line-height: 1.5;">
                Registration takes only 5 minutes. Check eligibility, explore fee concessions, and submit your application online.
            </div>
        </div>
    </div>
</div>
""")

btn_col1, btn_col2, _ = st.columns([1.5, 1.5, 3])
with btn_col1:
    if st.button("🚀 Begin Registration", type="primary", use_container_width=True, key="cta_reg"):
        st.switch_page("views/admissions.py")
with btn_col2:
    if st.button("📋 Check Eligibility", use_container_width=True, key="cta_elig"):
        st.switch_page("views/eligibility.py")