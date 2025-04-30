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
# Dragon de Cuivre : jusqu’à cette page (inclus)
p_copper = st.sidebar.slider(
    "Dragon de Cuivre : jusqu’à la page", 1, page_count, min(2, page_count)
)
# Dragon d’Argent : jusqu’à cette page (inclus)
p_silver = st.sidebar.slider(
    "Dragon d’Argent : jusqu’à la page",
    p_copper, page_count, min(p_copper + 2, page_count)
)
# Dragon d’Or : accès à toutes les pages
d_levels = {
    "Dragon de Cuivre": p_copper,
    "Dragon d’Argent": p_silver,
    "Dragon d’Or": page_count
}

ordered_levels = ["Dragon de Cuivre", "Dragon d’Argent", "Dragon d’Or"]

# --- Chargement police Bold + icône ---
font_path = os.path.join(os.getcwd(), "BeaufortforLOL", "BeaufortforLOL-Bold.otf")
font_size = 48
font = ImageFont.truetype(font_path, font_size)
lock_img_orig = Image.open("lock.png").convert("RGBA")

def get_required_level(page_idx: int) -> str:
    # Retourne le niveau minimal nécessaire pour voir la page
    for lvl in ordered_levels:
        if page_idx <= d_levels[lvl]:
            return lvl
    return ordered_levels[-1]

def overlay_badge(page_img: Image.Image, level_name: str) -> Image.Image:
    w, h = page_img.size
    # Redimension de l'icône à 15% de la largeur
    icon_scale = 0.15
    icon_w = int(w * icon_scale)
    aspect = lock_img_orig.width / lock_img_orig.height
    icon_h = int(icon_w / aspect)
    lock_img = lock_img_orig.resize((icon_w, icon_h), resample=Image.LANCZOS)
    # Préparer badge transparent
    badge = Image.new("RGBA", page_img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    # Texte multi-lignes
    text = f"Réservé aux\n{level_name}"
    bbox = draw.multiline_textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    total_h = icon_h + 10 + text_h
    # Centrage vertical et horizontal
    y0 = (h - total_h) // 2
    x_icon = (w - icon_w) // 2
    x_text = (w - text_w) // 2
    badge.paste(lock_img, (x_icon, y0), mask=lock_img)
    draw.multiline_text((x_text, y0 + icon_h + 10), text, font=font, fill="#ffe79f", align="center")
    return Image.alpha_composite(page_img.convert("RGBA"), badge).convert("RGB")

# --- Preview ---
preview_lvl = st.selectbox("Aperçu pour le niveau :", ordered_levels)
st.subheader(f"Aperçu — {preview_lvl}")
cols = st.columns(4)
thumb_w = 120
for idx, orig in enumerate(pil_pages, start=1):
    img = orig.copy()
    # Si page non accessible par le niveau preview, flouter + badge
    if idx > d_levels[preview_lvl]:
        img = img.filter(ImageFilter.GaussianBlur(radius=radius))
        # badge pour le palier requis
        req = get_required_level(idx)
        # si le palier requis est le même que preview, sauter (mais ici preview < req)
        img = overlay_badge(img, req)
    col = cols[(idx - 1) % 4]
    col.image(img, caption=f"Page {idx}", width=thumb_w)

# --- Téléchargements par niveau ---
st.markdown("---")
st.subheader("Téléchargement des PDF par niveau")
for lvl in ordered_levels:
    buf = io.BytesIO()
    out_pdf = fitz.open()
    max_page = d_levels[lvl]
    for idx, orig in enumerate(pil_pages, start=1):
        img = orig.copy()
        if idx > max_page:
            img = img.filter(ImageFilter.GaussianBlur(radius=radius))
            req = get_required_level(idx)
            img = overlay_badge(img, req)
        tmp = io.BytesIO()
        img.save(tmp, format="PNG")
        rect = pdf[idx - 1].rect
        page = out_pdf.new_page(width=rect.width, height=rect.height)
        page.insert_image(rect, stream=tmp.getvalue())
    out_pdf.save(buf)
    buf.seek(0)
    st.download_button(label=f"⬇️ {lvl}", data=buf, file_name=f"{lvl.replace(' ', '_')}.pdf", mime="application/pdf")
