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

    "navy": "#0B1F3F",
    "ink": "#172436",
    "muted": "#526176",

    "teal": "#0F8493",
    "teal_dark": "#155E75",
    "teal_soft": "#E3F5F6",
    "blue_soft": "#EFF6FF",

    "surface": "#FFFFFF",
    "surface_muted": "#F5F8FB",
    "border": "#E3EAF1",
    "border_strong": "#CCD7E3",

    "success": "#15803D",
    "warning": "#B45309",
    "danger": "#B91C1C",

    "radius_sm": "12px",
    "radius_md": "18px",
    "radius_lg": "24px",
    "radius_pill": "999px",

    "shadow_sm": "0 2px 8px rgba(15, 31, 63, 0.045), 0 8px 24px rgba(15, 31, 63, 0.035)",
    "shadow_md": "0 14px 36px rgba(15, 31, 63, 0.10)",
    "shadow_brand": "0 8px 24px rgba(15, 132, 147, 0.22)",
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
    return f"""
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
  max-width: 1520px !important;
  box-sizing: border-box;
  margin-inline: auto;
  padding-top: clamp(1.5rem, 2.6vw, 2.5rem);
  padding-bottom: clamp(2.5rem, 4vw, 4rem);
  padding-left: clamp(1.25rem, 4vw, 4.25rem);
  padding-right: clamp(1.25rem, 4vw, 4.25rem);
}}

h1, h2, h3, h4 {{
  color: var(--navy);
  font-weight: 750;
  letter-spacing: -0.025em;
  line-height: 1.15;
}}

h1 {{
  font-family: var(--font-display);
  font-size: clamp(2.25rem, 4.2vw, 3.45rem);
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
  color: var(--muted) !important;
  font-size: 0.82rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.01em !important;
  text-transform: none;
}}

/* -----------------------------------------------------------------------
   Header and navigation
----------------------------------------------------------------------- */

header[data-testid="stHeader"] {{
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: saturate(170%) blur(16px);
  border-bottom: 1px solid rgba(227, 234, 241, 0.95);
  box-shadow: 0 4px 20px rgba(15, 31, 63, 0.025);
}}

[data-testid="stTopNav"],
nav[role="navigation"] {{
  border-bottom: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.62);
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
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}}

div[data-testid="stVerticalBlockBorderWrapper"]:hover {{
  border-color: var(--border-strong) !important;
  box-shadow: var(--shadow-md) !important;
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
   Page shell, responsive columns and media
----------------------------------------------------------------------- */

.stApp [data-testid="stHorizontalBlock"] {{
  gap: clamp(0.85rem, 1.8vw, 1.4rem);
}}

.stApp [data-testid="stImage"] img {{
  border-radius: var(--radius-md);
}}

.stApp [data-testid="stTopNav"] a[aria-current="page"],
.stApp [data-testid="stTopNav"] a[aria-selected="true"] {{
  color: var(--teal-dark) !important;
  background: var(--teal-soft) !important;
  box-shadow: inset 0 0 0 1px rgba(15, 132, 147, 0.12);
}}

.stApp label,
.stApp [data-testid="stWidgetLabel"] p {{
  color: var(--ink);
  font-weight: 600;
}}

.stApp [data-testid="stCaptionContainer"] p {{
  line-height: 1.55;
}}

/* The homepage hero is keyed in hero.py so this treatment stays scoped. */
.st-key-home_hero {{
  border-radius: var(--radius-lg);
}}

.st-key-home_hero h1 {{
  max-width: 15ch;
  text-wrap: balance;
}}

.st-key-home_hero [data-testid="stImage"] img {{
  border-radius: 18px;
  box-shadow: 0 14px 34px rgba(11, 31, 63, 0.14);
}}

/* Homepage sections use shared classes instead of scattered inline styling. */
.admissions-ribbon {{
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.55rem;
  margin: 0 0 1.5rem;
  padding: 0.8rem 1.15rem;
  border: 1px solid rgba(15, 132, 147, 0.15);
  border-radius: var(--radius-pill);
  color: #FFFFFF;
  background: linear-gradient(105deg, #0B1F3F 0%, #155E75 58%, #0F8493 100%);
  box-shadow: 0 8px 22px rgba(11, 31, 63, 0.10);
  font-size: 0.92rem;
  font-weight: 650;
  line-height: 1.45;
  text-align: center;
}}

.feature-card {{
  height: 100%;
  min-height: 200px;
  padding: 1.35rem 1.2rem;
  border: 1px solid rgba(203, 213, 225, 0.75);
  border-top: 3px solid var(--feature-accent, var(--teal));
  border-radius: var(--radius-md);
  background: linear-gradient(180deg, #FFFFFF 0%, var(--feature-bg, #F4FAFB) 100%);
  box-shadow: var(--shadow-sm);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}}

.feature-card:hover {{
  border-color: var(--feature-accent, var(--teal));
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}}

.feature-card__icon {{
  margin-bottom: 0.65rem;
  font-size: 1.8rem;
  line-height: 1.2;
}}

.feature-card__title {{
  margin-bottom: 0.55rem;
  color: var(--navy);
  font-size: 1.08rem;
  font-weight: 750;
  line-height: 1.3;
}}

.feature-card__text {{
  color: var(--muted);
  font-size: 0.91rem;
  line-height: 1.65;
}}

.category-chip {{
  display: inline-flex;
  align-items: center;
  padding: 0.38rem 0.75rem;
  margin-bottom: 0.6rem;
  border: 1px solid color-mix(in srgb, var(--category-fg, var(--teal)) 18%, transparent);
  border-radius: var(--radius-pill);
  background: var(--category-bg, var(--teal-soft));
  color: var(--category-fg, var(--teal-dark));
  font-size: 0.72rem;
  font-weight: 750;
  letter-spacing: 0.06em;
}}

.cta-band {{
  margin-top: 1rem;
  padding: clamp(1.5rem, 3.5vw, 2.5rem);
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-lg);
  color: #FFFFFF;
  background:
    radial-gradient(450px 220px at 100% 0%, rgba(45, 212, 191, 0.25), transparent 72%),
    linear-gradient(125deg, #0B1F3F 0%, #153E75 62%, #0F8493 100%);
  box-shadow: 0 16px 38px rgba(11, 31, 63, 0.16);
}}

.cta-band__title {{
  margin-bottom: 0.5rem;
  color: #FFFFFF;
  font-size: clamp(1.4rem, 2.4vw, 1.85rem);
  font-weight: 800;
  letter-spacing: -0.025em;
  line-height: 1.2;
}}

.cta-band__text {{
  max-width: 68ch;
  color: rgba(255, 255, 255, 0.88);
  font-size: 0.98rem;
  line-height: 1.7;
}}

/* Interactive status is visible without changing widget behaviour. */
.stButton > button:disabled,
.stDownloadButton > button:disabled,
.stFormSubmitButton > button:disabled {{
  cursor: not-allowed !important;
  opacity: 0.52 !important;
  box-shadow: none !important;
  transform: none !important;
}}

.stApp [data-testid="stSpinner"] p {{
  color: var(--muted);
  font-weight: 600;
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
  .stApp [data-testid="stHorizontalBlock"] {{
    flex-wrap: wrap;
  }}

  .stApp [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
    min-width: min(100%, 250px) !important;
    flex: 1 1 250px !important;
  }}

  .admissions-ribbon {{
    border-radius: var(--radius-md);
    padding: 0.8rem 0.95rem;
    font-size: 0.84rem;
  }}

  .feature-card {{
    min-height: auto;
  }}
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