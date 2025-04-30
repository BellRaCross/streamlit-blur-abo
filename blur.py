import streamlit as st
import fitz            # PyMuPDF
from PIL import Image, ImageFilter, ImageDraw, ImageFont
import io
import os

st.set_page_config(page_title="PDF Blur by Membership", layout="wide")
st.title("PDF Blur par niveau d’abonnement")

# Rayon de flou fixe
radius = 5  # Flou fixé à 5 pixels

# --- Upload du PDF ---
uploaded_file = st.file_uploader("🔽 Uploadez un PDF", type=["pdf"])
if not uploaded_file:
    st.info("Veuillez uploader un PDF pour commencer.")
    st.stop()

# --- Lecture du PDF en images PIL ---
pdf = fitz.open(stream=uploaded_file.read(), filetype="pdf")
page_count = len(pdf)
pil_pages = []
for page in pdf:
    pix = page.get_pixmap()
    pil_pages.append(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))

# --- Définition des paliers via sliders hiérarchiques ---
st.sidebar.header("Pages accessibles par niveau")
# Dragons de Cuivre : jusqu’à cette page (inclus)
p_copper = st.sidebar.slider(
    "Dragons de Cuivre : jusqu’à la page", 1, page_count, min(2, page_count)
)
# Dragons d’Argent : jusqu’à cette page (inclus)
p_silver = st.sidebar.slider(
    "Dragons d’Argent : jusqu’à la page",
    p_copper, page_count, min(p_copper + 2, page_count)
)
# Dragons d’Or : accès à toutes les pages
d_levels = {
    "Dragons de Cuivre": p_copper,
    "Dragons d’Argent": p_silver,
    "Dragons d’Or": page_count
}

# Liste des niveaux pour preview & téléchargement
levels = list(d_levels.keys())

# --- Chargement police Bold + icône ---
font_path = os.path.join(os.getcwd(), "BeaufortforLOL", "BeaufortforLOL-Bold.otf")
font_size = 48
font = ImageFont.truetype(font_path, font_size)
lock_img_orig = Image.open("lock.png").convert("RGBA")

# Fonction pour déterminer le texte du badge
def get_badge_text(page_idx: int) -> str:
    if page_idx > d_levels["Dragons d’Argent"]:
        return "Dragons d’Or"
    elif page_idx > d_levels["Dragons de Cuivre"]:
        return "Dragons d’Argent et d’Or"
    else:
        return ""

# Fonction pour overlay du badge centré
def overlay_badge(page_img: Image.Image, text: str) -> Image.Image:
    if not text:
        return page_img
    w, h = page_img.size
    # Redimension de l'icône à 15% de la largeur
    icon_scale = 0.15
    icon_w = int(w * icon_scale)
    aspect = lock_img_orig.width / lock_img_orig.height
    icon_h = int(icon_w / aspect)
    lock_img = lock_img_orig.resize((icon_w, icon_h), resample=Image.LANCZOS)
    # Calque badge
    badge = Image.new("RGBA", page_img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    text_full = f"Réservé aux\n{text}"
    bbox = draw.multiline_textbbox((0, 0), text_full, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    total_h = icon_h + 10 + text_h
    y0 = (h - total_h) // 2
    x_icon = (w - icon_w) // 2
    x_text = (w - text_w) // 2
    badge.paste(lock_img, (x_icon, y0), mask=lock_img)
    draw.multiline_text(
        (x_text, y0 + icon_h + 10),
        text_full,
        font=font,
        fill="#ffe79f",
        align="center"
    )
    return Image.alpha_composite(page_img.convert("RGBA"), badge).convert("RGB")

# --- Preview ---
preview_lvl = st.selectbox("Aperçu pour le niveau :", levels)
st.subheader(f"Aperçu — {preview_lvl}")
cols = st.columns(4)
thumb_w = 120
for idx, orig in enumerate(pil_pages, start=1):
    img = orig.copy()
    if idx > d_levels[preview_lvl]:
        img = img.filter(ImageFilter.GaussianBlur(radius=radius))
        badge_text = get_badge_text(idx)
        img = overlay_badge(img, badge_text)
    col = cols[(idx - 1) % 4]
    col.image(img, caption=f"Page {idx}", width=thumb_w)

# --- Téléchargements par niveau ---
st.markdown("---")
st.subheader("Téléchargement des PDF par niveau")
for lvl in levels:
    buf = io.BytesIO()
    out_pdf = fitz.open()
    max_page = d_levels[lvl]
    for idx, orig in enumerate(pil_pages, start=1):
        img = orig.copy()
        if idx > max_page:
            img = img.filter(ImageFilter.GaussianBlur(radius=radius))
            badge_text = get_badge_text(idx)
            img = overlay_badge(img, badge_text)
        tmp = io.BytesIO()
        img.save(tmp, format="PNG")
        rect = pdf[idx - 1].rect
        page = out_pdf.new_page(width=rect.width, height=rect.height)
        page.insert_image(rect, stream=tmp.getvalue())
    out_pdf.save(buf)
    buf.seek(0)
    st.download_button(
        label=f"⬇️ {lvl}",
        data=buf,
        file_name=f"{lvl.replace(' ', '_')}.pdf",
        mime="application/pdf"
    )
