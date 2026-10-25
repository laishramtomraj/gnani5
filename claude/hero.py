"""hero.py - homepage hero banner (Python + Streamlit only, no HTML/CSS/JS).

The banner picture is drawn with Pillow (installed with Streamlit). If you add
assets/campus-aerial.jpg it becomes the banner background; otherwise a navy-to-teal
academic illustration is used. No institutional facts are invented.
"""
import io

import streamlit as st

import content_db
from PIL import Image, ImageDraw, ImageOps

from data import COLLEGE, find_hero_image

NAVY = (11, 31, 63)
TEAL = (27, 111, 120)
W, H = 1400, 1000


def _gradient() -> Image.Image:
    mask = Image.linear_gradient("L").resize((W, H))          # top = 0, bottom = 255
    return Image.composite(Image.new("RGB", (W, H), TEAL), Image.new("RGB", (W, H), NAVY), mask)


def _building_outline(canvas: Image.Image) -> Image.Image:
    """Faint line drawing of an academic building (pediment, columns, steps)."""
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ink = (255, 255, 255, 70)
    s = W / 760                                                # scale from a 600x340 sketch
    ox, oy = 147, 190                                          # centres the sketch on the canvas

    def P(x, y):                                               # sketch -> canvas coordinates
        return (ox + x * s, oy + y * s)

    d.line([P(60, 150), P(300, 40), P(540, 150), P(60, 150)], fill=ink, width=5, joint="curve")
    d.ellipse([*P(282, 92), *P(318, 128)], outline=ink, width=5)
    d.rectangle([*P(60, 150), *P(540, 164)], outline=ink, width=5)
    for x in (100, 170, 240, 360, 430, 500):
        d.line([P(x, 164), P(x, 290)], fill=ink, width=5)
    for x0, y0, x1, y1 in ((60, 290, 540, 302), (40, 302, 560, 314), (20, 314, 580, 326)):
        d.rectangle([*P(x0, y0), *P(x1, y1)], outline=ink, width=5)
    return Image.alpha_composite(canvas.convert("RGBA"), layer)


@st.cache_data(show_spinner=False)
def _banner_png(photo_path: str | None, photo_mtime: float | None) -> bytes:
    if photo_path:
        photo = ImageOps.fit(Image.open(photo_path).convert("RGB"), (W, H))
        base = Image.blend(photo, Image.new("RGB", (W, H), NAVY), 0.35)   # navy tint for a uniform look
        canvas = base.convert("RGBA")
    else:
        canvas = _building_outline(_gradient())
    rounded = Image.new("L", (W, H), 0)
    ImageDraw.Draw(rounded).rounded_rectangle([0, 0, W - 1, H - 1], radius=48, fill=255)
    canvas.putalpha(rounded)
    out = io.BytesIO()
    canvas.save(out, format="PNG")
    return out.getvalue()


def render_hero() -> None:
    photo = find_hero_image()
    banner = _banner_png(str(photo) if photo else None, photo.stat().st_mtime if photo else None)

    with st.container(border=True, key="home_hero"):
        left, right = st.columns([1.15, 1], gap="large", vertical_alignment="center")
        with left:
            st.badge(f"Welcome to {COLLEGE['name']}", icon=":material/school:", color="green")
            st.title(content_db.text("home_headline").replace("\n", "  \n"), anchor=False)
            st.write(content_db.text("home_intro"))
            b1, b2 = st.columns(2)
            if b1.button("Explore Courses", type="primary", width="stretch", key="hero_courses"):
                st.switch_page("views/courses.py")
            if b2.button("Begin Registration", width="stretch", key="hero_register"):
                st.switch_page("views/admissions.py")
        with right:
            st.image(banner, width="stretch")
            if not photo:
                st.caption("Placeholder visual. Add `assets/campus-aerial.jpg` to show your campus here.")
