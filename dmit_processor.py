import io
import os
import subprocess
import tempfile
import zipfile
from xml.sax.saxutils import escape as xml_escape

import fitz  # PyMuPDF
from pdf2docx import Converter
from PIL import Image, ImageDraw, ImageFont

# Security limits for Zip and Image processing (DoS / Zip Bomb defense)
MAX_ZIP_ENTRIES = 1000
MAX_SINGLE_FILE_BYTES = 30 * 1024 * 1024       # 30 MB uncompressed per entry
MAX_TOTAL_UNCOMPRESSED_BYTES = 100 * 1024 * 1024  # 100 MB total uncompressed
MAX_COMPRESSION_RATIO = 15.0                   # Max ratio for entries > 1 MB
MAX_IMAGE_DIMENSION = 4096                     # Max width or height for uploaded logos

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


def sanitize_excel_val(val: str) -> str:
    """
    Sanitizes user input string for safe OpenXML injection:
    1. Neutralizes Excel CSV / Formula injection (=, +, -, @, \\t, \\r).
    2. Escapes XML special characters (&, <, >, \", \') to prevent corruption and XXE.
    """
    if not val:
        return ""
    val_str = str(val).strip()
    if val_str.startswith(("=", "+", "-", "@", "\t", "\r")):
        val_str = "'" + val_str
    return xml_escape(val_str, entities={'"': "&quot;", "'": "&apos;"})


def validate_zip_archive(archive: zipfile.ZipFile) -> None:
    """
    Validates zip archive against zip bombs and memory exhaustion attacks.
    Raises ValueError if thresholds are exceeded.
    """
    entries = archive.infolist()
    if len(entries) > MAX_ZIP_ENTRIES:
        raise ValueError(f"Security Alert: Archive exceeds file entry limit ({len(entries)} > {MAX_ZIP_ENTRIES})")

    cumulative_uncompressed = 0
    for entry in entries:
        cumulative_uncompressed += entry.file_size
        if entry.file_size > MAX_SINGLE_FILE_BYTES:
            raise ValueError(
                f"Security Alert: File '{entry.filename}' exceeds uncompressed size limit ({entry.file_size} bytes)"
            )
        if cumulative_uncompressed > MAX_TOTAL_UNCOMPRESSED_BYTES:
            raise ValueError(
                f"Security Alert: Cumulative archive size exceeds limit ({cumulative_uncompressed} bytes)"
            )
        if entry.compress_size > 0 and entry.file_size > 1024 * 1024:
            ratio = entry.file_size / entry.compress_size
            if ratio > MAX_COMPRESSION_RATIO:
                raise ValueError(
                    f"Security Alert: Entry '{entry.filename}' has excessive compression ratio ({ratio:.1f}:1)"
                )


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

    # Enforce safe decompression limit in Pillow
    Image.MAX_IMAGE_PIXELS = 10_000_000

    # 1. Process uploaded logo image if provided
    logo_img = None
    if logo_bytes:
        try:
            with Image.open(io.BytesIO(logo_bytes)) as raw_img:
                if raw_img.width > MAX_IMAGE_DIMENSION or raw_img.height > MAX_IMAGE_DIMENSION:
                    raise ValueError(f"Logo dimensions exceed maximum allowable {MAX_IMAGE_DIMENSION}px")
                logo_img = raw_img.convert("RGBA")
        except Exception as e:
            print(f"Error opening logo bytes: {e}")
            logo_img = None

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
            except (OSError, ValueError):
                continue

    for p in font_paths_reg:
        if os.path.exists(p):
            try:
                font_medium = ImageFont.truetype(p, medium_size)
                break
            except (OSError, ValueError):
                continue

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
    if not file_bytes:
        raise ValueError("Source Excel file is empty.")

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

    # Open archive and validate against zip bombs
    input_zip = zipfile.ZipFile(io.BytesIO(file_bytes), 'r')
    validate_zip_archive(input_zip)

    # Sanitize user inputs for OpenXML injection safety
    safe_footer_company = sanitize_excel_val(footer_company)
    safe_footer_contact = sanitize_excel_val(footer_contact)
    safe_email_addr = sanitize_excel_val(email_addr)

    output_io = io.BytesIO()

    with zipfile.ZipFile(output_io, 'w', zipfile.ZIP_DEFLATED) as output_zip:
        for item in input_zip.infolist():
            filename = item.filename
            content = input_zip.read(filename)

            # 1. Replace ALL cover logo image files with composite banner
            if filename in COVER_LOGO_IMAGES or (filename.startswith("xl/media/image6") and filename.endswith(".png")):
                content = composite_logo_bytes

            # 2. Global String Replacements in XML files with sanitized values
            if filename.endswith((".xml", ".rels")):
                text_content = content.decode("utf-8", errors="ignore")

                if "THE MIND MYSTERY" in text_content:
                    text_content = text_content.replace("THE MIND MYSTERY", safe_footer_company)

                if "Support- 8075891014 || Mail: mindmysteryinstitute@hotmail.com" in text_content:
                    text_content = text_content.replace(
                        "Support- 8075891014 || Mail: mindmysteryinstitute@hotmail.com",
                        safe_footer_contact
                    )

                if "mindmysteryinstitute@hotmail.com" in text_content and safe_email_addr:
                    text_content = text_content.replace(
                        "mindmysteryinstitute@hotmail.com",
                        safe_email_addr
                    )

                content = text_content.encode("utf-8")

            output_zip.writestr(item, content)

    xlsm_out_bytes = output_io.getvalue()

    # Generate PDF export via sandboxed LibreOffice
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
    if not file_bytes:
        raise ValueError("Source PDF file is empty.")

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

    # B. Global Multi-Page Footer Replacement (batch annotations before redaction)
    for page in doc:
        company_insertions = []
        for rect in page.search_for("THE MIND MYSTERY"):
            page.add_redact_annot(rect, fill=(1, 1, 1))
            company_insertions.append(rect)

        contact_insertions = []
        contact_matches = page.search_for("Support- 8075891014")
        if not contact_matches:
            contact_matches = page.search_for("mindmysteryinstitute@hotmail.com")

        for rect in contact_matches:
            expanded_rect = fitz.Rect(rect.x0 - 60, rect.y0 - 2, rect.x1 + 160, rect.y1 + 2)
            page.add_redact_annot(expanded_rect, fill=(1, 1, 1))
            contact_insertions.append(expanded_rect)

        # Apply redactions once per page for integrity and performance
        if company_insertions or contact_insertions:
            page.apply_redactions()

        for rect in company_insertions:
            page.insert_textbox(
                rect,
                footer_company,
                fontsize=9,
                fontname="helv",
                color=(0.2, 0.2, 0.2),
                align=fitz.TEXT_ALIGN_CENTER
            )

        for rect in contact_insertions:
            page.insert_textbox(
                rect,
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
    """Converts PDF bytes to Word (.docx) bytes via pdf2docx using safe isolated temporary directory."""
    if not pdf_bytes:
        return b""

    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_pdf_path = os.path.join(temp_dir, "input.pdf")
        tmp_docx_path = os.path.join(temp_dir, "output.docx")

        with open(tmp_pdf_path, "wb") as f:
            f.write(pdf_bytes)

        try:
            cv = Converter(tmp_pdf_path)
            cv.convert(tmp_docx_path, start=0, end=None)
            cv.close()

            if os.path.exists(tmp_docx_path):
                with open(tmp_docx_path, "rb") as f:
                    return f.read()
        except Exception as e:
            print(f"pdf2docx conversion error: {e}")
            return b""

    return b""


def _excel_to_pdf(excel_bytes: bytes) -> bytes:
    """
    Converts .xlsm Excel bytes to PDF using isolated LibreOffice headless execution.
    Sandboxes user profile and isolates files in dedicated temporary directory.
    """
    if not excel_bytes:
        return b""

    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_excel_path = os.path.join(temp_dir, "input.xlsm")
        with open(tmp_excel_path, "wb") as f:
            f.write(excel_bytes)

        expected_pdf_path = os.path.join(temp_dir, "input.pdf")
        profile_dir = os.path.join(temp_dir, "lo_profile")
        os.makedirs(profile_dir, exist_ok=True)

        lo_binaries = [
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            "/opt/homebrew/bin/soffice",
            "/opt/homebrew/bin/libreoffice",
            "soffice",
            "libreoffice"
        ]

        for lo_cmd in lo_binaries:
            try:
                res = subprocess.run(  # noqa: S603
                    [
                        lo_cmd,
                        "--headless",
                        "--nodefault",
                        "--nolockcheck",
                        "--nologo",
                        "--norestore",
                        f"-env:UserInstallation=file://{profile_dir}",
                        "--convert-to", "pdf",
                        tmp_excel_path,
                        "--outdir", temp_dir
                    ],
                    capture_output=True,
                    timeout=45,
                    check=False
                )
                if res.returncode == 0 and os.path.exists(expected_pdf_path):
                    with open(expected_pdf_path, "rb") as f:
                        return f.read()
            except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
                continue
            except Exception as e:
                print(f"LibreOffice conversion warning: {e}")
                continue

    return b""
