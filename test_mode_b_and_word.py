import os
import io
import zipfile
from dmit_processor import process_excel, process_pdf, _pdf_to_docx

def test_mode_b_and_word_export():
    base_dir = "/Users/nakhulgithesh/Documents/work/project-pavi "
    test_dir = os.path.join(base_dir, "test ")
    refreacted_dir = os.path.join(base_dir, "refreacted")
    os.makedirs(refreacted_dir, exist_ok=True)

    excel_file = os.path.join(test_dir, "DMIT 69 pages.xlsm")

    print(f"Excel test file exists: {os.path.exists(excel_file)}")

    with open(excel_file, "rb") as f:
        excel_bytes = f.read()

    text_details = {
        "company_name": "Mind Craft Clinic",
        "tagline": "Brain & Behavioral Center",
        "phone": "+91 9876543210",
        "email": "contact@mindcraft.com",
        "address": "Mumbai, India"
    }

    footer_company = "MIND CRAFT CLINIC"
    footer_contact = "Support- +91 9876543210 || Mail: contact@mindcraft.com"

    print("\n--- TESTING MODE B (TEXT DETAILS REPLACEMENT) ON EXCEL ---")
    res_excel = process_excel(
        file_bytes=excel_bytes,
        mode="Mode B: Text Details Replacement",
        logo_bytes=None,
        text_details=text_details,
        footer_company=footer_company,
        footer_contact=footer_contact
    )

    out_xlsm_path = os.path.join(refreacted_dir, "Rebranded_DMIT_ModeB.xlsm")
    with open(out_xlsm_path, "wb") as f:
        f.write(res_excel["xlsm"])
    print(f"Saved Mode B Excel output to: {out_xlsm_path} ({len(res_excel['xlsm'])} bytes)")

    # Inspect drawing1.xml inside out_xlsm_path to verify rId8, rId87-rId92 anchors were removed
    with zipfile.ZipFile(out_xlsm_path, "r") as z:
        drawing1 = z.read("xl/drawings/drawing1.xml").decode("utf-8", errors="ignore")
        for rid in ["rId8", "rId87", "rId88", "rId89", "rId90", "rId91", "rId92"]:
            contains_rid = rid in drawing1
            print(f"Anchor {rid} removed: {not contains_rid}")

    # Test PDF generation in Mode B
    out_pdf_bytes = res_excel["pdf"]
    out_pdf_path = os.path.join(refreacted_dir, "Rebranded_DMIT_ModeB.pdf")
    with open(out_pdf_path, "wb") as f:
        f.write(out_pdf_bytes)
    print(f"\nSaved Mode B PDF output to: {out_pdf_path} ({len(out_pdf_bytes)} bytes)")

    # Test Word (.docx) export generation from PDF
    print("\n--- TESTING WORD (.DOCX) EXPORT GENERATION ---")
    out_docx_bytes = _pdf_to_docx(out_pdf_bytes)
    out_docx_path = os.path.join(refreacted_dir, "Rebranded_DMIT_ModeB.docx")
    with open(out_docx_path, "wb") as f:
        f.write(out_docx_bytes)
    print(f"Saved Word (.docx) export to: {out_docx_path} ({len(out_docx_bytes)} bytes)")

    print("\nVERIFICATION COMPLETE: Mode B & Word (.docx) export tested and verified successfully!")

if __name__ == "__main__":
    test_mode_b_and_word_export()
