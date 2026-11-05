import os

import streamlit as st

from dmit_processor import (
    _pdf_to_docx,
    build_composite_branding_image,
    process_excel,
    process_pdf,
)

# Streamlit Page Configuration
st.set_page_config(
    page_title="DMIT Studio Pro | Report Re-Branding Engine",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Responsive Light & Dark Mode Compatible CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* Completely hide Streamlit Cloud header, toolbar, Share, GitHub, Star, Edit, and Menu */
    header[data-testid="stHeader"],
    .stAppHeader,
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    #MainMenu,
    #GithubIcon,
    .stDeployButton,
    footer {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        min-height: 0 !important;
    }

    /* Reduce excess top whitespace created by hidden header */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
    }

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Clean Top Header */
    .studio-header {
        padding: 1.2rem 0 1.5rem 0;
        border-bottom: 2px solid rgba(120, 120, 120, 0.15);
        margin-bottom: 2rem;
    }
    .studio-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: #0284C7;
        font-weight: 600;
        margin-bottom: 0.3rem;
    }
    .studio-title {
        font-size: 2.1rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin: 0;
    }
    .studio-desc {
        font-size: 0.95rem;
        opacity: 0.7;
        margin-top: 0.3rem;
    }
    
    /* Subtext Explanations */
    .field-hint {
        font-size: 0.82rem;
        opacity: 0.65;
        margin-top: -0.4rem;
        margin-bottom: 0.6rem;
    }
    
    /* Section Headings */
    .section-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        color: #0284C7;
        font-weight: 600;
        letter-spacing: 0.1em;
        margin-bottom: 0.2rem;
    }
    .section-title {
        font-size: 1.15rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Header Section
st.markdown("""
<div class="studio-header">
    <div class="studio-tag">✦ AUTOMATED DMIT RE-BRANDING</div>
    <h1 class="studio-title">DMIT Studio Pro</h1>
    <div class="studio-desc">Re-brand DMIT reports (.xlsm & .pdf) with combined Logo + Name + Email + Phone cover branding.</div>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    # STEP 1: Upload Source File
    with st.container(border=True):
        st.markdown('<div class="section-tag">01 // SOURCE REPORT</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Upload Original DMIT Report</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Upload .xlsm or .pdf source report",
            type=["xlsm", "pdf"]
        )
        st.markdown('<div class="field-hint">Upload the original DMIT Excel workbook (.xlsm) or PDF report to re-brand.</div>', unsafe_allow_html=True)

    # STEP 2: Cover Branding (Logo + Text Stacked)
    with st.container(border=True):
        st.markdown('<div class="section-tag">02 // COVER PAGE BRANDING</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Stacked Cover Logo & Text</div>', unsafe_allow_html=True)
        st.markdown('<div class="field-hint">Replaces "THE MIND MYSTERY" cover logo with stacked <b>Logo → Name → Email → Phone</b>.</div>', unsafe_allow_html=True)

        uploaded_logo = st.file_uploader(
            "1. Upload Client Logo Image (PNG, JPG, JPEG)",
            type=["png", "jpg", "jpeg"]
        )
        st.markdown('<div class="field-hint">Logo image placed at the top (original logo size).</div>', unsafe_allow_html=True)

        logo_bytes = uploaded_logo.getvalue() if uploaded_logo else None

        text_details = {}

        text_details["company_name"] = st.text_input("2. Company / Clinic Name", value="Mind Craft Clinic")
        st.markdown('<div class="field-hint">Placed directly below the logo in <b>Title Font</b>.</div>', unsafe_allow_html=True)

        text_details["email"] = st.text_input("3. Support Email", value="contact@mindcraft.com")
        st.markdown('<div class="field-hint">Placed directly below Name in <b>Medium Font</b>.</div>', unsafe_allow_html=True)

        text_details["phone"] = st.text_input("4. Contact Phone Number", value="+91 9876543210")
        st.markdown('<div class="field-hint">Placed directly below Email in <b>Medium Font</b> (same size as email).</div>', unsafe_allow_html=True)

        # Live Preview of Composite Banner
        st.write("---")
        st.write("🖼️ **Cover Banner Preview (Stacked Layout):**")
        preview_bytes = build_composite_branding_image(
            logo_bytes=logo_bytes,
            company_name=text_details["company_name"],
            email=text_details["email"],
            phone=text_details["phone"]
        )
        st.image(preview_bytes, use_container_width=True, caption="Live Preview of Cover Replacement Banner")

with col2:
    # STEP 3: Global Footer Configuration
    with st.container(border=True):
        st.markdown('<div class="section-tag">03 // PAGE FOOTERS & CONTACT</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Global Footer Replacements</div>', unsafe_allow_html=True)

        footer_company = st.text_input("Footer Company Name", value="MIND CRAFT CLINIC")
        st.markdown('<div class="field-hint">👉 <b>What it does:</b> Replaces "THE MIND MYSTERY" text printed across all page footers.</div>', unsafe_allow_html=True)

        footer_contact = st.text_input("Footer Contact Line", value="Support- +91 9876543210 || Mail: contact@mindcraft.com")
        st.markdown('<div class="field-hint">👉 <b>What it does:</b> Replaces default support phone & email line printed at bottom of pages.</div>', unsafe_allow_html=True)

        footer_email = st.text_input("Footer Support Email", value="contact@mindcraft.com")
        st.markdown('<div class="field-hint">👉 <b>What it does:</b> Replaces "mindmysteryinstitute@hotmail.com" everywhere in report text.</div>', unsafe_allow_html=True)

    # STEP 4: Export Center
    with st.container(border=True):
        st.markdown('<div class="section-tag">04 // EXPORT CENTER</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Generate Re-Branded Report</div>', unsafe_allow_html=True)

        if uploaded_file:
            file_ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
            file_bytes = uploaded_file.getvalue()
            base_name = os.path.splitext(uploaded_file.name)[0]

            st.success(f"Loaded: **{uploaded_file.name}** ({len(file_bytes) / 1024 / 1024:.2f} MB)")

            if st.button("🚀 Process & Generate Downloads", type="primary", use_container_width=True):
                with st.spinner("Processing report re-branding..."):
                    try:
                        if file_ext == "xlsm":
                            result = process_excel(
                                file_bytes=file_bytes,
                                logo_bytes=logo_bytes,
                                text_details=text_details,
                                footer_company=footer_company,
                                footer_contact=footer_contact
                            )
                        elif file_ext == "pdf":
                            result = process_pdf(
                                file_bytes=file_bytes,
                                logo_bytes=logo_bytes,
                                text_details=text_details,
                                footer_company=footer_company,
                                footer_contact=footer_contact
                            )
                        else:
                            st.error(f"Unsupported file format: .{file_ext}")
                            result = None

                        if result:
                            st.session_state["result"] = result
                            st.session_state["processed_ext"] = file_ext
                            st.session_state["base_name"] = base_name
                            st.success("✨ Re-branding completed!")
                    except Exception as err:
                        st.error(f"Processing error: {err}")

            if "result" in st.session_state:
                res = st.session_state["result"]
                base_out_name = st.session_state.get("base_name", "Report")

                st.write("---")
                st.write("**Download Formats:**")

                if res.get("xlsm"):
                    st.download_button(
                        label="📊 Download Re-Branded Excel (.xlsm)",
                        data=res["xlsm"],
                        file_name=f"Rebranded_{base_out_name}.xlsm",
                        mime="application/vnd.ms-excel.sheet.macroEnabled.12",
                        use_container_width=True
                    )

                if res.get("pdf"):
                    st.download_button(
                        label="📄 Download Re-Branded PDF (.pdf)",
                        data=res["pdf"],
                        file_name=f"Rebranded_{base_out_name}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )

                col_d1, col_d2 = st.columns([2, 1])
                with col_d1:
                    st.write("📝 **Word Export (.docx)**")
                with col_d2:
                    if st.button("Generate .docx", use_container_width=True):
                        with st.spinner("Converting PDF to Word (.docx)..."):
                            try:
                                pdf_data = res.get("pdf")
                                if pdf_data:
                                    docx_bytes = _pdf_to_docx(pdf_data)
                                    if docx_bytes:
                                        st.session_state["docx_bytes"] = docx_bytes
                                        st.success("Word document generated!")
                                    else:
                                        st.error("Failed to convert PDF to Word (.docx).")
                                else:
                                    st.error("No PDF data available for conversion.")
                            except Exception as err:
                                st.error(f"Word export error: {err}")

                if st.session_state.get("docx_bytes"):
                    st.download_button(
                        label="⬇️ Download Word Document (.docx)",
                        data=st.session_state["docx_bytes"],
                        file_name=f"Rebranded_{base_out_name}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
        else:
            st.info("💡 Upload a `.xlsm` or `.pdf` file in Step 01 to enable Process & Download buttons.")
