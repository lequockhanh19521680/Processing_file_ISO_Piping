"""
Streamlit application for processing Excel files with Google Drive PDF search.
"""
import streamlit as st
import os
import tempfile
import shutil
from pathlib import Path

from excel_utils import read_excel_codes, write_result_sheet
from drive_utils import extract_folder_id, create_drive_service, list_drive_pdfs
from pdf_utils import PDFTextCache, search_codes


# Page configuration
st.set_page_config(
    page_title="ISO Piping PDF Processor",
    page_icon="📄",
    layout="wide"
)

# Title and description
st.title("📄 ISO Piping PDF Processor")
st.markdown("""
This application processes Excel files containing hole codes (ma_ho) and searches for them 
in PDF files stored in Google Drive folders.
""")

# Initialize session state
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False
if 'result_file_path' not in st.session_state:
    st.session_state.result_file_path = None
if 'pdf_cache' not in st.session_state:
    st.session_state.pdf_cache = PDFTextCache()


def main():
    # Create two columns for inputs
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Upload Excel File")
        uploaded_file = st.file_uploader(
            "Choose an Excel file (.xlsx)",
            type=['xlsx'],
            help="Excel file must contain a 'ma_ho' column with hole codes"
        )
    
    with col2:
        st.subheader("🔐 Service Account Credentials")
        credentials_file = st.file_uploader(
            "Upload Service Account JSON",
            type=['json'],
            help="Google Cloud service account credentials with Drive API access"
        )
    
    # Google Drive folder link input
    st.subheader("📁 Google Drive Folder")
    drive_link = st.text_input(
        "Enter Google Drive folder link:",
        placeholder="https://drive.google.com/drive/folders/YOUR_FOLDER_ID",
        help="Paste the link to your Google Drive folder containing PDFs"
    )
    
    # Process button
    st.markdown("---")
    process_button = st.button("🚀 OK - Start Processing", type="primary", use_container_width=True)
    
    # Processing logic
    if process_button:
        # Validation
        if not uploaded_file:
            st.error("❌ Please upload an Excel file")
            return
        
        if not credentials_file:
            st.error("❌ Please upload service account credentials")
            return
        
        if not drive_link:
            st.error("❌ Please enter a Google Drive folder link")
            return
        
        # Reset processing state
        st.session_state.processing_complete = False
        st.session_state.result_file_path = None
        
        try:
            with st.spinner("Processing..."):
                # Create temporary directory for processing
                temp_dir = tempfile.mkdtemp()
                
                try:
                    # Save uploaded Excel file
                    excel_path = os.path.join(temp_dir, uploaded_file.name)
                    with open(excel_path, 'wb') as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Save credentials file
                    creds_path = os.path.join(temp_dir, 'credentials.json')
                    with open(creds_path, 'wb') as f:
                        f.write(credentials_file.getbuffer())
                    
                    # Step 1: Read Excel codes
                    st.info("📖 Reading hole codes from Excel file...")
                    codes = read_excel_codes(excel_path)
                    st.success(f"✅ Found {len(codes)} hole codes")
                    
                    if len(codes) == 0:
                        st.error("❌ No codes found in Excel file")
                        return
                    
                    # Step 2: Extract folder ID and create Drive service
                    st.info("🔗 Connecting to Google Drive...")
                    folder_id = extract_folder_id(drive_link)
                    service = create_drive_service(creds_path)
                    st.success(f"✅ Connected to Drive (Folder ID: {folder_id})")
                    
                    # Step 3: List PDF files
                    st.info("📂 Listing PDF files in folder (this may take a while)...")
                    pdf_files = list_drive_pdfs(service, folder_id)
                    st.success(f"✅ Found {len(pdf_files)} PDF files")
                    
                    if len(pdf_files) == 0:
                        st.warning("⚠️ No PDF files found in the specified folder")
                        # Create empty results
                        results = [
                            {
                                'ma_ho': code,
                                'found': 'NO',
                                'file_name': '',
                                'file_id': '',
                                'folder_path': ''
                            }
                            for code in codes
                        ]
                    else:
                        # Step 4: Search for codes in PDFs
                        st.info("🔍 Searching for codes in PDFs...")
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        def update_progress(progress, message):
                            progress_bar.progress(progress)
                            status_text.text(message)
                        
                        results = search_codes(
                            codes, 
                            pdf_files, 
                            service, 
                            st.session_state.pdf_cache,
                            progress_callback=update_progress
                        )
                        
                        progress_bar.progress(1.0)
                        status_text.text("Search complete!")
                        
                        found_count = sum(1 for r in results if r['found'] == 'YES')
                        st.success(f"✅ Search complete! Found {found_count}/{len(codes)} codes")
                    
                    # Step 5: Write results to Excel
                    st.info("📝 Writing results to Excel file...")
                    result_path = write_result_sheet(excel_path, results)
                    
                    # Copy result file to a persistent location
                    result_file_name = f"result_{uploaded_file.name}"
                    persistent_path = os.path.join(temp_dir, result_file_name)
                    shutil.copy(result_path, persistent_path)
                    
                    st.session_state.result_file_path = persistent_path
                    st.session_state.processing_complete = True
                    
                    st.success("✅ Results written to RESULT sheet")
                    
                    # Display summary
                    st.markdown("---")
                    st.subheader("📊 Summary")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Codes", len(codes))
                    with col2:
                        found_count = sum(1 for r in results if r['found'] == 'YES')
                        st.metric("Codes Found", found_count)
                    with col3:
                        st.metric("PDF Files Scanned", len(pdf_files))
                    
                except Exception as e:
                    st.error(f"❌ Error during processing: {str(e)}")
                    import traceback
                    with st.expander("Show error details"):
                        st.code(traceback.format_exc())
        
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")
    
    # Download button (shown after processing)
    if st.session_state.processing_complete and st.session_state.result_file_path:
        st.markdown("---")
        st.subheader("📥 Download Results")
        
        with open(st.session_state.result_file_path, 'rb') as f:
            file_data = f.read()
            
        st.download_button(
            label="⬇️ Download Updated Excel File",
            data=file_data,
            file_name=os.path.basename(st.session_state.result_file_path),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )
        
        st.success("✅ Click the button above to download your results")


if __name__ == "__main__":
    main()
