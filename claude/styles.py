"""
styles.py — Global visual design system for the college website.

Styling only: this module does not modify content, routing, forms,
database access, or application behaviour.

Design goals:
- Modern, premium, professional academic appearance
- Consistent colour, spacing, typography, radius, and elevation
- Responsive layout for desktop, tablet, and mobile
- Accessible focus states and reduced-motion support
- Maintainable CSS custom properties instead of scattered hard-coded values
"""

from __future__ import annotations

from functools import lru_cache

import streamlit as st


# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

TOKENS = {
    "font_sans": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    "font_display": "'Fraunces', Georgia, 'Times New Roman', serif",

    "navy": "#0B1220",
    "ink": "#111827",
    "muted": "#475569",

    "teal": "#0E7490",
    "teal_dark": "#155E75",
    "teal_soft": "#E0F2FE",
    "blue_soft": "#EFF6FF",

    "surface": "#FFFFFF",
    "surface_muted": "#F8FAFC",
    "border": "#E2E8F0",
    "border_strong": "#CBD5E1",

    "success": "#15803D",
    "warning": "#B45309",
    "danger": "#B91C1C",

    "radius_sm": "10px",
    "radius_md": "16px",
    "radius_lg": "22px",
    "radius_pill": "999px",

    "shadow_sm": "0 1px 2px rgba(15, 23, 42, 0.05), 0 4px 14px rgba(15, 23, 42, 0.05)",
    "shadow_md": "0 10px 30px rgba(15, 23, 42, 0.08)",
    "shadow_brand": "0 8px 22px rgba(14, 116, 144, 0.24)",
}


def _css_variables() -> str:
    """Convert Python design tokens into CSS custom properties."""
    return "\n".join(
        f"  --{key.replace('_', '-')}: {value};"
        for key, value in TOKENS.items()
    )


# ---------------------------------------------------------------------------
# Stylesheet
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _build_css() -> str:
    """Build the complete stylesheet once, then reuse it across reruns."""
    variables = _css_variables()
    return f"""""

   
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Fraunces:opsz,wght@9..144,600;9..144,700&display=swap');

:root {{
{variables}
}}

/* -----------------------------------------------------------------------
   Base typography and application canvas
----------------------------------------------------------------------- */

html, body, [class*="st-"], .stMarkdown, button, input, textarea, select {{
  font-family: var(--font-sans) !important;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}}

.stApp {{
  color: var(--ink);
  background:
    radial-gradient(1100px 520px at 88% -12%, rgba(14, 116, 144, 0.11), transparent 65%),
    radial-gradient(850px 480px at -5% 0%, rgba(30, 64, 175, 0.07), transparent 60%),
    linear-gradient(180deg, #FFFFFF 0%, var(--surface-muted) 460px);
}}

/* Full-width layout with proportional desktop gutters */
.stMainBlockContainer,
.block-container {{
  width: 100%;
  max-width: none !important;
  box-sizing: border-box;
  margin-inline: auto;
  padding-top: 2.25rem;
  padding-bottom: 3.5rem;
  padding-left: clamp(1.5rem, 5vw, 6rem);
  padding-right: clamp(1.5rem, 5vw, 6rem);
}}

h1, h2, h3, h4 {{
  color: var(--navy);
  font-weight: 750;
  letter-spacing: -0.025em;
  line-height: 1.15;
}}

h1 {{
  font-family: var(--font-display);
  font-size: clamp(2.15rem, 4vw, 3rem);
  line-height: 1.08;
}}

h2 {{ font-size: clamp(1.65rem, 2.6vw, 2.1rem); }}
h3 {{ font-size: 1.32rem; }}
h4 {{ font-size: 1.08rem; }}

p, li {{
  line-height: 1.65;
}}

strong {{
  color: var(--navy);
}}

/* Section eyebrows created through st.caption */
[data-testid="stCaptionContainer"] {{
  color: var(--teal) !important;
  font-size: 0.76rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.11em !important;
  text-transform: uppercase;
}}

/* -----------------------------------------------------------------------
   Header and navigation
----------------------------------------------------------------------- */

header[data-testid="stHeader"] {{
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: saturate(180%) blur(14px);
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
}}

[data-testid="stTopNav"],
nav[role="navigation"] {{
  border-bottom: 1px solid var(--border);
}}

[data-testid="stPageLink"] a,
[data-testid="stSidebarNav"] a {{
  border-radius: var(--radius-pill);
  font-weight: 600;
  transition:
    background-color 0.2s ease,
    color 0.2s ease,
    box-shadow 0.2s ease;
}}

[data-testid="stPageLink"] a:hover,
[data-testid="stSidebarNav"] a:hover {{
  background: var(--teal-soft);
  color: var(--teal-dark);
}}

/* -----------------------------------------------------------------------
   Buttons and interactive controls
----------------------------------------------------------------------- */

.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {{
  border-radius: var(--radius-pill) !important;
  padding: 0.62rem 1.45rem !important;
  font-weight: 650 !important;
  border: 1px solid transparent !important;
  transition:
    transform 0.16s ease,
    box-shadow 0.22s ease,
    background-color 0.2s ease,
    border-color 0.2s ease,
    color 0.2s ease;
}}

.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {{
  background: linear-gradient(135deg, var(--teal) 0%, var(--teal-dark) 100%) !important;
  color: #FFFFFF !important;
  border: none !important;
  box-shadow: var(--shadow-brand);
}}

.stButton > button[kind="secondary"],
.stDownloadButton > button,
.stFormSubmitButton > button[kind="secondary"] {{
  background: var(--surface) !important;
  color: var(--navy) !important;
  border-color: var(--border-strong) !important;
}}

.stButton > button:hover,
.stDownloadButton > button:hover,
.stFormSubmitButton > button:hover {{
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}}

.stButton > button:active,
.stDownloadButton > button:active,
.stFormSubmitButton > button:active {{
  transform: translateY(0);
  box-shadow: var(--shadow-sm);
}}

/* Accessible keyboard focus */
button:focus-visible,
a:focus-visible,
input:focus-visible,
textarea:focus-visible,
select:focus-visible {{
  outline: 3px solid rgba(14, 116, 144, 0.35) !important;
  outline-offset: 2px !important;
}}

/* -----------------------------------------------------------------------
   Cards, forms, expanders, and containers
----------------------------------------------------------------------- */

div[data-testid="stForm"],
div[data-testid="stExpander"],
div[data-testid="stVerticalBlockBorderWrapper"] {{
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
  box-shadow: var(--shadow-sm) !important;
  overflow: hidden;
}}

div[data-testid="stExpander"] summary {{
  font-weight: 650;
}}

div[data-testid="stForm"] {{
  padding: 1.15rem;
}}

/* -----------------------------------------------------------------------
   Inputs
----------------------------------------------------------------------- */

input,
textarea,
[data-baseweb="select"] > div {{
  background: var(--surface) !important;
  border-color: var(--border-strong) !important;
  border-radius: var(--radius-sm) !important;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}}

input:focus,
textarea:focus {{
  border-color: var(--teal) !important;
  box-shadow: 0 0 0 4px rgba(14, 116, 144, 0.13) !important;
}}

/* -----------------------------------------------------------------------
   Metrics, alerts, tabs, and tables
----------------------------------------------------------------------- */

div[data-testid="stMetric"] {{
  background: linear-gradient(180deg, var(--surface) 0%, var(--surface-muted) 100%);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 1.1rem 1.25rem;
  box-shadow: var(--shadow-sm);
}}

div[data-testid="stMetricLabel"] {{
  color: var(--muted) !important;
  font-weight: 600 !important;
}}

div[data-testid="stMetricValue"] {{
  color: var(--navy) !important;
  font-weight: 800 !important;
}}

div[data-testid="stAlert"] {{
  border: 1px solid rgba(226, 232, 240, 0.9) !important;
  border-radius: var(--radius-md) !important;
  box-shadow: var(--shadow-sm);
}}

button[data-baseweb="tab"] {{
  font-weight: 600;
}}

button[data-baseweb="tab"][aria-selected="true"] {{
  color: var(--teal-dark) !important;
}}

div[data-baseweb="tab-highlight"] {{
  height: 3px !important;
  background-color: var(--teal) !important;
  border-radius: var(--radius-pill);
}}

[data-testid="stDataFrame"] {{
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}}

/* -----------------------------------------------------------------------
   Chat assistant
----------------------------------------------------------------------- */

[data-testid="stChatMessage"] {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}}

/* -----------------------------------------------------------------------
   Footer, links, dividers, and selection
----------------------------------------------------------------------- */

hr {{
  height: 1px !important;
  border: none !important;
  background: linear-gradient(
    90deg,
    transparent,
    var(--border),
    transparent
  ) !important;
  margin: 2.25rem 0 !important;
}}

a {{
  transition: color 0.18s ease, opacity 0.18s ease;
}}

a:hover {{
  color: var(--teal-dark);
}}

::selection {{
  background: var(--teal-soft);
  color: var(--navy);
}}

html {{
  scroll-behavior: smooth;
}}

/* -----------------------------------------------------------------------
   Responsive full-width layout
----------------------------------------------------------------------- */

/* Tablet and smaller laptops */
@media (max-width: 1024px) {{
  .stMainBlockContainer,
  .block-container {{
    padding-left: 1.5rem;
    padding-right: 1.5rem;
  }}
}}

/* Mobile */
@media (max-width: 768px) {{
  .stMainBlockContainer,
  .block-container {{
    padding-left: 1rem;
    padding-right: 1rem;
    padding-top: 1.5rem;
    padding-bottom: 2.5rem;
  }}

  h1 {{
    font-size: 1.95rem;
  }}

  h2 {{
    font-size: 1.55rem;
  }}

  .stButton > button,
  .stDownloadButton > button,
  .stFormSubmitButton > button {{
    width: 100%;
  }}
}}

/* -----------------------------------------------------------------------
   Accessibility and print
----------------------------------------------------------------------- */

@media (prefers-reduced-motion: reduce) {{
  *,
  *::before,
  *::after {{
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important;
    scroll-behavior: auto !important;
  }}
}}

@media print {{
  header[data-testid="stHeader"],
  [data-testid="stTopNav"],
  nav[role="navigation"],
  .stButton,
  .stDownloadButton,
  .stFormSubmitButton {{
    display: none !important;
  }}

  .stApp {{
    background: #FFFFFF !important;
  }}

  .block-container {{
    max-width: 100%;
    padding: 0;
  }}
}}
</style>
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_theme() -> None:
    """Inject the global stylesheet once per Streamlit page run."""
    st.markdown(_build_css(), unsafe_allow_html=True)