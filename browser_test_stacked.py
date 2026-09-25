import os
import time
import io
import zipfile
from playwright.sync_api import sync_playwright

def run_browser_test():
    workspace_dir = "/Users/nakhulgithesh/Documents/work/project-pavi "
    excel_path = os.path.join(workspace_dir, "test ", "DMIT 69 pages.xlsm")
    logo_path = os.path.join(workspace_dir, "test ", "Screenshot 2026-07-28 at 10.58.37 PM.png")
    out_dir = os.path.join(workspace_dir, "refreacted")

    os.makedirs(out_dir, exist_ok=True)

    out_xlsm_path = os.path.join(out_dir, "Rebranded_DMIT_Stacked.xlsm")
    out_pdf_path = os.path.join(out_dir, "Rebranded_DMIT_Stacked.pdf")

    print(f"Excel input path: {excel_path}")
    print(f"Logo input path: {logo_path}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print("Navigating to http://localhost:8501...")
        page.goto("http://localhost:8501", timeout=60000)
        page.wait_for_selector("h1", timeout=15000)

        # 1. Upload Source Excel File
        print("Uploading source report (.xlsm)...")
        file_inputs = page.query_selector_all("input[type='file']")
        if len(file_inputs) >= 1:
            file_inputs[0].set_input_files(excel_path)
            time.sleep(2)

        # 2. Upload Logo Image
        print("Uploading logo image...")
        file_inputs = page.query_selector_all("input[type='file']")
        if len(file_inputs) >= 2:
            file_inputs[1].set_input_files(logo_path)
            time.sleep(2)

        # 3. Fill text input fields
        print("Filling in Email and Phone details...")
        text_inputs = page.query_selector_all("input[type='text']")
        print(f"Found {len(text_inputs)} text inputs.")

        # Let's inspect labels or fill by order:
        # Step 2: Name (0), Email (1), Phone (2)
        # Step 3: Footer Company (3), Footer Contact (4), Footer Email (5)
        if len(text_inputs) >= 6:
            text_inputs[0].fill("MIND CRAFT CLINIC")
            text_inputs[1].fill("nakhulgitheshwork@gmail.com")
            text_inputs[2].fill("9037237657")
            text_inputs[3].fill("MIND CRAFT CLINIC")
            text_inputs[4].fill("Support- 9037237657 || Mail: nakhulgitheshwork@gmail.com")
            text_inputs[5].fill("nakhulgitheshwork@gmail.com")

        time.sleep(2)

        # Take screenshot of UI state before processing
        page.screenshot(path=os.path.join(out_dir, "stacked_browser_test_form.png"))

        # 4. Click Process Button
        print("Clicking 'Process & Generate Downloads' button...")
        process_btn = page.locator("button:has-text('Process & Generate Downloads')")
        if process_btn.count() > 0:
            process_btn.click()

        print("Waiting for re-branding processing to complete...")
        page.wait_for_selector("text=Re-branding completed!", timeout=120000)
        time.sleep(3)

        # Take screenshot of completed state
        page.screenshot(path=os.path.join(out_dir, "stacked_browser_test_complete.png"))

        # 5. Download Re-Branded Excel (.xlsm)
        print("Downloading Re-Branded Excel...")
        with page.expect_download(timeout=30000) as download_info:
            page.locator("button:has-text('Download Re-Branded Excel')").click()
        download_excel = download_info.value
        download_excel.save_as(out_xlsm_path)
        print(f"Saved XLSM to: {out_xlsm_path} ({os.path.getsize(out_xlsm_path)} bytes)")

        # 6. Download Re-Branded PDF (.pdf)
        print("Downloading Re-Branded PDF...")
        with page.expect_download(timeout=30000) as download_info_pdf:
            page.locator("button:has-text('Download Re-Branded PDF')").click()
        download_pdf = download_info_pdf.value
        download_pdf.save_as(out_pdf_path)
        print(f"Saved PDF to: {out_pdf_path} ({os.path.getsize(out_pdf_path)} bytes)")

        browser.close()

    # 7. Verification of Downloaded XLSM
    print("Verifying downloaded Excel zip media entries...")
    with zipfile.ZipFile(out_xlsm_path, 'r') as z:
        for name in ['image6.png', 'image60.png', 'image61.png', 'image62.png', 'image63.png', 'image64.png', 'image65.png']:
            img_bytes = z.read(f'xl/media/{name}')
            assert len(img_bytes) > 1000, f"Error: {name} in excel is empty or invalid!"
            print(f"Verified media: xl/media/{name} ({len(img_bytes)} bytes)")

    print("\nSUCCESS! Browser end-to-end test passed completely!")

if __name__ == "__main__":
    run_browser_test()
