import os
import re
import io
import zipfile
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont
import fitz  # PyMuPDF
from pdf2docx import Converter


# Target cover logo image files in DMIT report Excel archive
COVER_LOGO_IMAGES = {
    "xl/media/image6.png",
    "xl/media/image60.png",
    "xl/media/image61.png",
    "xl/media/image62.png",
    "xl/media/image63.png",
    "xl/media/image64.png",
    "xl/media/image65.png",
}

COVER_LOGO_RIDS = ["rId8", "rId87", "rId88", "rId89", "rId90", "rId91", "rId92"]


def build_composite_branding_image(
    logo_bytes: bytes | None = None,
    company_name: str = "",
    email: str = "",
    phone: str = "",
    canvas_w: int = 1156
) -> bytes:
    """
    Creates a combined cover branding banner image containing:
    1. Logo image at top (scaled proportionally)
    2. Company / Clinic Name below logo (in Title font)
    3. Email below Name (in Medium font)
    4. Phone number below Email (in Medium font, same size as Email)
    """
    padding = 24

    # 1. Process uploaded logo image if provided
    logo_img = None
    if logo_bytes:
        try:
            logo_img = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
        except Exception as e:
            print(f"Error opening logo bytes: {e}")

    logo_w, logo_h = 0, 0
    if logo_img:
        max_w, max_h = 850, 480
        orig_w, orig_h = logo_img.size
        ratio = min(max_w / orig_w, max_h / orig_h, 1.0)
        logo_w = max(1, int(orig_w * ratio))
        logo_h = max(1, int(orig_h * ratio))
        logo_img = logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)

    # 2. Setup font sizes and load system fonts
    title_size = 54
    medium_size = 34

    font_title = None
    font_medium = None

    font_paths_bold = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    ]
    font_paths_reg = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]

    for p in font_paths_bold:
        if os.path.exists(p):
            try:
                font_title = ImageFont.truetype(p, title_size)
                break
            except Exception:
                pass

    for p in font_paths_reg:
        if os.path.exists(p):
            try:
                font_medium = ImageFont.truetype(p, medium_size)
                break
            except Exception:
                pass

    if not font_title:
        try:
            font_title = ImageFont.load_default(size=title_size)
        except Exception:
            font_title = ImageFont.load_default()

    if not font_medium:
        try:
            font_medium = ImageFont.load_default(size=medium_size)
        except Exception:
            font_medium = ImageFont.load_default()

    # 3. Calculate text dimensions
    def get_text_size(text, font):
        if not text:
            return 0, 0
        if hasattr(font, "getbbox"):
            bbox = font.getbbox(text)
            return (bbox[2] - bbox[0]), (bbox[3] - bbox[1])
        return len(text) * 16, 30

    name_w, name_h = get_text_size(company_name, font_title)
    email_w, email_h = get_text_size(email, font_medium)
    phone_w, phone_h = get_text_size(phone, font_medium)

    # 4. Total canvas height calculation
    text_block_h = 0
    if company_name:
        text_block_h += name_h + (24 if (email or phone) else 0)
    if email:
        text_block_h += email_h + (16 if phone else 0)
    if phone:
        text_block_h += phone_h

    logo_block_h = (logo_h + 30) if logo_img else 0
    total_h = max(350, padding + logo_block_h + text_block_h + padding)

    # 5. Draw composite canvas (White background matching report cover)
    canvas = Image.new("RGBA", (canvas_w, total_h), (255, 255, 255, 255))

    # Paste logo centered at top
    curr_y = padding
    if logo_img:
        logo_x = (canvas_w - logo_w) // 2
        canvas.paste(logo_img, (logo_x, curr_y), logo_img)
        curr_y += logo_h + 30

    draw = ImageDraw.Draw(canvas)

    # Draw Name (Title Font)
    if company_name:
        draw.text(((canvas_w - name_w) // 2, curr_y), company_name, fill=(15, 23, 42), font=font_title)
        curr_y += name_h + 24

    # Draw Email (Medium Font)
    if email:
        draw.text(((canvas_w - email_w) // 2, curr_y), email, fill=(51, 65, 85), font=font_medium)
        curr_y += email_h + 16

    # Draw Phone (Medium Font, same size as Email)
    if phone:
        draw.text(((canvas_w - phone_w) // 2, curr_y), phone, fill=(51, 65, 85), font=font_medium)

    # Output PNG bytes
    out_buf = io.BytesIO()
    canvas.convert("RGB").save(out_buf, format="PNG")
    return out_buf.getvalue()


def process_excel(
    file_bytes: bytes,
    mode: str = "Combined Logo & Text",
    logo_bytes: bytes | None = None,
    text_details: dict | None = None,
    footer_company: str = "THE MIND MYSTERY",
    footer_contact: str = "Support- 8075891014 || Mail: mindmysteryinstitute@hotmail.com"
) -> dict:
    """
    Processes .xlsm Excel DMIT report.
    Replaces cover logo image with combined Logo + Name + Email + Phone block.
    Returns dict: {"xlsm": bytes, "pdf": bytes, "docx": bytes}
    """
    text_details = text_details or {}
    company_name = text_details.get("company_name", "") or footer_company
    email_addr = text_details.get("email", "")
    phone_num = text_details.get("phone", "")

    # Build composite logo + text image
    composite_logo_bytes = build_composite_branding_image(
        logo_bytes=logo_bytes,
        company_name=company_name,
        email=email_addr,
        phone=phone_num
    )

    input_zip = zipfile.ZipFile(io.BytesIO(file_bytes), 'r')
    output_io = io.BytesIO()

    with zipfile.ZipFile(output_io, 'w', zipfile.ZIP_DEFLATED) as output_zip:
        for item in input_zip.infolist():
            filename = item.filename
            content = input_zip.read(filename)

            # 1. Replace ALL cover logo image files with composite banner
            if filename in COVER_LOGO_IMAGES or (filename.startswith("xl/media/image6") and filename.endswith(".png")):
                content = composite_logo_bytes

            # 2. Global String Replacements in XML files
            if filename.endswith(".xml") or filename.endswith(".rels"):
                text_content = content.decode("utf-8", errors="ignore")

                if "THE MIND MYSTERY" in text_content:
                    text_content = text_content.replace("THE MIND MYSTERY", footer_company)

                if "Support- 8075891014 || Mail: mindmysteryinstitute@hotmail.com" in text_content:
                    text_content = text_content.replace(
                        "Support- 8075891014 || Mail: mindmysteryinstitute@hotmail.com",
                        footer_contact
                    )

                if "mindmysteryinstitute@hotmail.com" in text_content and email_addr:
                    text_content = text_content.replace(
                        "mindmysteryinstitute@hotmail.com",
                        email_addr
                    )

                content = text_content.encode("utf-8")

            output_zip.writestr(item, content)

    xlsm_out_bytes = output_io.getvalue()

    # Generate PDF export via LibreOffice
    pdf_out_bytes = _excel_to_pdf(xlsm_out_bytes)

    return {
        "xlsm": xlsm_out_bytes,
        "pdf": pdf_out_bytes,
        "docx": b""
    }


def process_pdf(
    file_bytes: bytes,
    mode: str = "Combined Logo & Text",
    logo_bytes: bytes | None = None,
    text_details: dict | None = None,
    footer_company: str = "THE MIND MYSTERY",
    footer_contact: str = "Support- 8075891014 || Mail: mindmysteryinstitute@hotmail.com"
) -> dict:
    """
    Processes PDF DMIT report using PyMuPDF (fitz).
    Inserts combined Logo + Name + Email + Phone block on Cover Page.
    Returns dict: {"xlsm": None, "pdf": bytes, "docx": bytes}
    """
    text_details = text_details or {}
    company_name = text_details.get("company_name", "") or footer_company
    email_addr = text_details.get("email", "")
    phone_num = text_details.get("phone", "")

    composite_logo_bytes = build_composite_branding_image(
        logo_bytes=logo_bytes,
        company_name=company_name,
        email=email_addr,
        phone=phone_num
    )

    doc = fitz.open(stream=file_bytes, filetype="pdf")

    # A. Cover Page 1 Logo / Details Replacement
    if len(doc) > 0:
        page1 = doc[0]
        rect_cover = fitz.Rect(50, 70, 550, 360)

        # Apply white redaction rectangle over old logo
        page1.add_redact_annot(rect_cover, fill=(1, 1, 1))
        page1.apply_redactions()

        page1.insert_image(rect_cover, stream=composite_logo_bytes, keep_proportion=True)

    # B. Global 69-Page Footer Replacement
    for page in doc:
        # Search & redact "THE MIND MYSTERY"
        for rect in page.search_for("THE MIND MYSTERY"):
            page.add_redact_annot(rect, fill=(1, 1, 1))
            page.apply_redactions()
            page.insert_textbox(
                rect,
                footer_company,
                fontsize=9,
                fontname="helv",
                color=(0.2, 0.2, 0.2),
                align=fitz.TEXT_ALIGN_CENTER
            )

        # Search & redact footer contact line
        contact_matches = page.search_for("Support- 8075891014")
        if not contact_matches:
            contact_matches = page.search_for("mindmysteryinstitute@hotmail.com")

        for rect in contact_matches:
            expanded_rect = fitz.Rect(rect.x0 - 60, rect.y0 - 2, rect.x1 + 160, rect.y1 + 2)
            page.add_redact_annot(expanded_rect, fill=(1, 1, 1))
            page.apply_redactions()
            page.insert_textbox(
                expanded_rect,
                footer_contact,
                fontsize=8,
                fontname="helv",
                color=(0.3, 0.3, 0.3),
                align=fitz.TEXT_ALIGN_CENTER
            )

    pdf_out_bytes = doc.tobytes()

    return {
        "xlsm": None,
        "pdf": pdf_out_bytes,
        "docx": b""
    }


def _pdf_to_docx(pdf_bytes: bytes) -> bytes:
    """Converts PDF bytes to Word (.docx) bytes via pdf2docx."""
    if not pdf_bytes:
        return b""

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
        tmp_pdf.write(pdf_bytes)
        tmp_pdf_path = tmp_pdf.name

    tmp_docx_path = tmp_pdf_path.replace(".pdf", ".docx")
    try:
        cv = Converter(tmp_pdf_path)
        cv.convert(tmp_docx_path, start=0, end=None)
        cv.close()

        with open(tmp_docx_path, "rb") as f:
            docx_bytes = f.read()
        return docx_bytes
    except Exception as e:
        print(f"pdf2docx error: {e}")
        return b""
    finally:
        if os.path.exists(tmp_pdf_path):
            os.remove(tmp_pdf_path)
        if os.path.exists(tmp_docx_path):
            os.remove(tmp_docx_path)


def _excel_to_pdf(excel_bytes: bytes) -> bytes:
    """Converts .xlsm Excel bytes to PDF using LibreOffice/soffice CLI."""
    with tempfile.NamedTemporaryFile(suffix=".xlsm", delete=False) as tmp_excel:
        tmp_excel.write(excel_bytes)
        tmp_excel_path = tmp_excel.name

    temp_dir = os.path.dirname(tmp_excel_path)
    expected_pdf_path = tmp_excel_path.replace(".xlsm", ".pdf")

    lo_binaries = [
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/opt/homebrew/bin/soffice",
        "/opt/homebrew/bin/libreoffice",
        "soffice",
        "libreoffice"
    ]

    for lo_cmd in lo_binaries:
        try:
            res = subprocess.run(
                [lo_cmd, "--headless", "--convert-to", "pdf", tmp_excel_path, "--outdir", temp_dir],
                capture_output=True,
                timeout=60
            )
            if res.returncode == 0 and os.path.exists(expected_pdf_path):
                with open(expected_pdf_path, "rb") as f:
                    pdf_bytes = f.read()

                if os.path.exists(tmp_excel_path):
                    os.remove(tmp_excel_path)
                if os.path.exists(expected_pdf_path):
                    os.remove(expected_pdf_path)
                return pdf_bytes
        except Exception:
            continue

    if os.path.exists(tmp_excel_path):
        os.remove(tmp_excel_path)
    if os.path.exists(expected_pdf_path):
        os.remove(expected_pdf_path)

    return b""
