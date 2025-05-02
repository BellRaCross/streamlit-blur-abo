import streamlit as st
import fitz  # PyMuPDF
from PIL import Image, ImageFilter, ImageDraw, ImageFont
import io
import os

# Configuration de la page
st.set_page_config(page_title="PDF Blur by Membership", layout="wide")
st.title("PDF Blur par niveau d’abonnement")

# Paramètres fixes
radius = 5          # Rayon de flou fixe
export_scale = 3    # Facteur d’échelle pour la résolution

# --- Chargement des pages avec cache ---
@st.cache_data
def load_pdf_images(uploaded_bytes):
    pdf = fitz.open(stream=uploaded_bytes, filetype="pdf")
    pages = []
    for page in pdf:
        mat = fitz.Matrix(export_scale, export_scale)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pages.append((img, page.rect))
    return pages

# --- Upload du PDF ---
uploaded_file = st.file_uploader("🔽 Uploadez un PDF", type=["pdf"])
if not uploaded_file:
    st.info("Veuillez uploader un PDF pour commencer.")
    st.stop()

# Chargement des images
pil_pages = load_pdf_images(uploaded_file.read())
page_count = len(pil_pages)

# --- Sliders hiérarchiques ---
st.sidebar.header("Pages accessibles par niveau")
p_copper = st.sidebar.slider("Dragons de Cuivre : jusqu’à la page", 1, page_count, min(2, page_count))
p_silver = st.sidebar.slider(
    "Dragons d’Argent : jusqu’à la page", p_copper, page_count, min(p_copper + 2, page_count)
)
d_levels = {"Dragons de Cuivre": p_copper, "Dragons d’Argent": p_silver, "Dragons d’Or": page_count}
levels = list(d_levels.keys())

# --- Chargement police + icône ---
font = ImageFont.truetype(
    os.path.join(os.getcwd(), "BeaufortforLOL", "BeaufortforLOL-Bold.otf"),
    48 * export_scale
)
lock_img_orig = Image.open("lock.png").convert("RGBA")

# --- Fonctions utilitaires ---
def get_badge_text(idx, lvl):
    if lvl == "Dragons de Cuivre":
        if idx > d_levels["Dragons d’Argent"]:
            return "Dragons d’Or"
        elif idx > d_levels["Dragons de Cuivre"]:
            return "Dragons d’Argent\net d’Or"
    elif lvl == "Dragons d’Argent":
        if idx > d_levels["Dragons d’Argent"]:
            return "Dragons d’Or"
    return ""


def overlay_badge(img, text):
    if not text:
        return img
    w, h = img.size
    icon_w = int(w * 0.15)
    icon_h = int(icon_w * lock_img_orig.height / lock_img_orig.width)
    icon = lock_img_orig.resize((icon_w, icon_h), resample=Image.LANCZOS)
    # Shadow layer
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_shadow = ImageDraw.Draw(shadow)
    text_full = f"Réservé aux\n{text}"
    bbox = draw_shadow.multiline_textbbox((0, 0), text_full, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    total_h = icon_h + 10 + th
    y0 = (h - total_h) // 2
    x0_icon = (w - icon_w) // 2
    x0_text = (w - tw) // 2
    # Draw shadow
    shadow.paste((0, 0, 0, 255), (x0_icon, y0), mask=icon)
    draw_shadow.multiline_text((x0_text, y0 + icon_h + 10), text_full, font=font, fill=(0,0,0,255), align="center")
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=export_scale * 2))
    base = img.convert("RGBA")
    base = Image.alpha_composite(base, shadow)
    # Draw actual badge
    base.paste(icon, (x0_icon, y0), mask=icon)
    draw = ImageDraw.Draw(base)
    draw.multiline_text((x0_text, y0 + icon_h + 10), text_full, font=font, fill="#ffe79f", align="center")
    return base.convert("RGB")

# --- Aperçu en grille ---
preview_lvl = st.selectbox("Aperçu pour le niveau :", levels)
st.subheader(f"Aperçu — {preview_lvl}")
cols = st.columns(4)
thumb_w = 120
for i, (img, _) in enumerate(pil_pages, start=1):
    img_copy = img.copy()
    if i > d_levels[preview_lvl]:
        img_copy = img_copy.filter(ImageFilter.GaussianBlur(radius=radius))
        badge = get_badge_text(i, preview_lvl)
        img_copy = overlay_badge(img_copy, badge)
    cols[(i-1)%4].image(img_copy, caption=f"Page {i}", width=thumb_w)
    # Le même bouton de zoom sur hover de Streamlit suffira pour fullscreen

# --- Téléchargements ---
# Nom de base du document sans extension
import pathlib
base_name = pathlib.Path(uploaded_file.name).stem

st.markdown("---")
st.subheader("Téléchargement des PDF par niveau")
for lvl in levels:
    buf = io.BytesIO()
    out = fitz.open()
    for i, (img, rect) in enumerate(pil_pages, start=1):
        page_img = img.copy()
        if i > d_levels[lvl]:
            page_img = page_img.filter(ImageFilter.GaussianBlur(radius=radius))
            badge = get_badge_text(i, lvl)
            page_img = overlay_badge(page_img, badge)
        tmp = io.BytesIO()
        page_img.save(tmp, format="PNG")
        p = out.new_page(width=rect.width, height=rect.height)
        p.insert_image(rect, stream=tmp.getvalue())
    out.save(buf)
    buf.seek(0)
    # Nouveau nom: Nom du document - Niveau.pdf
    download_filename = f"{base_name} - {lvl}.pdf"
    st.download_button(
        label=f"⬇️ {lvl}",
        data=buf,
        file_name=download_filename,
        mime="application/pdf"
    )
