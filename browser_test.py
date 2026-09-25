import os
import io
import time
import zipfile
from PIL import Image
from playwright.sync_api import sync_playwright

def run_browser_automation():
    base_dir = "/Users/nakhulgithesh/Documents/work/project-pavi "
    test_dir = os.path.join(base_dir, "test ")
    refreacted_dir = os.path.join(base_dir, "refreacted")
    os.makedirs(refreacted_dir, exist_ok=True)

    excel_file = os.path.join(test_dir, "DMIT 69 pages.xlsm")
    logo_file = os.path.join(test_dir, "Screenshot 2026-07-28 at 10.58.37 PM.png")

    print(f"Excel source file exists: {os.path.exists(excel_file)}")
    print(f"Logo image file exists: {os.path.exists(logo_file)}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        print("Navigating to http://localhost:8501 ...")
        page.goto("http://localhost:8501", timeout=30000)
        page.wait_for_selector("text=DMIT Report Re-Branding Studio", timeout=15000)

        # 1. Upload Source Excel file
        print("Uploading source report DMIT 69 pages.xlsm ...")
        file_inputs = page.locator('input[type="file"]')
        file_inputs.nth(0).set_input_files(excel_file)
        time.sleep(2)

        # 2. Upload Logo Image
        print("Uploading logo image ...")
        file_inputs.nth(1).set_input_files(logo_file)
        time.sleep(2)

        # 3. Click Process & Generate Downloads
        print("Clicking Process & Generate Downloads ...")
        process_btn = page.locator("button:has-text('Process & Generate Downloads')")
        process_btn.click()

        # Wait for processing & success message
        page.wait_for_selector("text=Re-branding completed!", timeout=60000)
        print("Processing completed successfully!")

        # Take UI screenshot of browser state
        page.screenshot(path=os.path.join(refreacted_dir, "ui_test_screenshot.png"))

        # 4. Download Excel (.xlsm)
        print("Downloading Re-Branded Excel (.xlsm) ...")
        with page.expect_download(timeout=30000) as download_info_excel:
            page.locator("button:has-text('Download Re-Branded Excel')").click()
        download_excel = download_info_excel.value
        save_excel_path = os.path.join(refreacted_dir, "Rebranded_DMIT 69 pages.xlsm")
        download_excel.save_as(save_excel_path)
        print(f"Saved downloaded Excel to: {save_excel_path}")

        # 5. Download PDF (.pdf)
        print("Downloading Re-Branded PDF (.pdf) ...")
        with page.expect_download(timeout=60000) as download_info_pdf:
            page.locator("button:has-text('Download Re-Branded PDF')").click()
        download_pdf = download_info_pdf.value
        save_pdf_path = os.path.join(refreacted_dir, "Rebranded_DMIT 69 pages.pdf")
        download_pdf.save_as(save_pdf_path)
        print(f"Saved downloaded PDF to: {save_pdf_path}")

        browser.close()

    # Verification Phase: Check downloaded Excel logo images against source logo
    print("\n--- VERIFICATION PHASE ---")
    with open(logo_file, "rb") as f:
        src_img_data = f.read()

    src_img = Image.open(io.BytesIO(src_img_data))
    src_png_io = io.BytesIO()
    src_img.save(src_png_io, format="PNG")
    expected_logo_bytes = src_png_io.getvalue()

    with zipfile.ZipFile(save_excel_path, 'r') as z:
        replaced_count = 0
        for name in ['image6.png', 'image60.png', 'image61.png', 'image62.png', 'image63.png', 'image64.png', 'image65.png']:
            full_name = f'xl/media/{name}'
            if full_name in z.namelist():
                content = z.read(full_name)
                is_match = (content == expected_logo_bytes)
                print(f"Checking {name}: Replaced={is_match}, Size={len(content)} bytes")
                if is_match:
                    replaced_count += 1

    print(f"\nVERIFICATION RESULT: {replaced_count} out of 7 logo image files were 100% replaced by the test image!")

if __name__ == "__main__":
    run_browser_automation()
