"""
FastAPI Backend for Processing ISO Piping Files

Main application that orchestrates Excel processing, Google Drive file search,
and PDF text extraction to match ma_ho values against PDF content.
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
import io
import os
from datetime import datetime

from drive_service import DriveService
from pdf_utils import PDFTextExtractor
from excel_utils import ExcelProcessor


# Initialize FastAPI app
app = FastAPI(
    title="ISO Piping File Processor",
    description="Process Excel files with ma_ho values against PDF files in Google Drive",
    version="1.0.0"
)

# Configure CORS to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "service": "ISO Piping File Processor",
        "version": "1.0.0"
    }


@app.post("/process")
async def process_file(
    file: UploadFile = File(..., description="Excel file with ma_ho values"),
    drive_link: str = Form(..., description="Google Drive folder URL")
):
    """
    Process Excel file by searching for ma_ho values in PDF files from Google Drive.
    
    Args:
        file: Excel file (.xlsx) with column A containing ma_ho values
        drive_link: Google Drive folder URL to search for PDF files
        
    Returns:
        StreamingResponse: Updated Excel file with RESULT sheet
        
    Raises:
        HTTPException: If processing fails
    """
    
    print(f"[{datetime.now()}] Starting processing request")
    print(f"File: {file.filename}, Drive link: {drive_link}")
    
    try:
        # Step 1: Read the uploaded Excel file
        print("Reading Excel file...")
        file_content = await file.read()
        excel_processor = ExcelProcessor()
        ma_ho_values = excel_processor.read_input_excel(file_content)
        
        print(f"Found {len(ma_ho_values)} ma_ho values: {ma_ho_values}")
        
        if not ma_ho_values:
            raise HTTPException(
                status_code=400,
                detail="No ma_ho values found in Excel file"
            )
        
        # Step 2: Authenticate with Google Drive
        print("Authenticating with Google Drive...")
        drive_service = DriveService()
        drive_service.authenticate()
        
        # Step 3: Extract folder ID and list all PDF files
        print("Extracting folder ID and listing PDF files...")
        folder_id = drive_service.extract_folder_id(drive_link)
        pdf_files = drive_service.list_pdf_files_recursive(folder_id)
        
        print(f"Found {len(pdf_files)} PDF files in folder and subfolders")
        
        if not pdf_files:
            # No PDFs found - mark all as NOT FOUND
            results = []
            for ma_ho in ma_ho_values:
                results.append({
                    "ma_ho": ma_ho,
                    "found": "NO",
                    "file_name": "",
                    "file_id": "",
                    "folder_path": ""
                })
            
            excel_processor.create_result_sheet(results)
            output_bytes = excel_processor.save_to_bytes()
            
            return StreamingResponse(
                io.BytesIO(output_bytes),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": "attachment; filename=processed_result.xlsx"
                }
            )
        
        # Step 4: Download and extract text from all PDFs (with caching)
        print("Downloading and extracting text from PDFs...")
        pdf_extractor = PDFTextExtractor()
        pdf_text_data = []
        
        for idx, pdf_info in enumerate(pdf_files, 1):
            print(f"Processing PDF {idx}/{len(pdf_files)}: {pdf_info['file_name']}")
            
            # Download PDF content
            pdf_content = drive_service.download_file(pdf_info['file_id'])
            if not pdf_content:
                print(f"  Failed to download {pdf_info['file_name']}")
                continue
            
            # Extract text (cached)
            text = pdf_extractor.extract_text(pdf_content, pdf_info['file_id'])
            
            pdf_text_data.append({
                'file_id': pdf_info['file_id'],
                'file_name': pdf_info['file_name'],
                'folder_path': pdf_info['folder_path'],
                'text': text
            })
        
        print(f"Successfully extracted text from {len(pdf_text_data)} PDFs")
        
        # Step 5: Search for each ma_ho in all PDF texts
        print("Searching for ma_ho values in PDF texts...")
        results = []
        
        for ma_ho in ma_ho_values:
            found = False
            matching_file = None
            
            # Search in all PDF texts
            for pdf_data in pdf_text_data:
                if pdf_extractor.search_text(pdf_data['text'], ma_ho):
                    found = True
                    matching_file = pdf_data
                    break  # Found in this file, no need to search further
            
            if found and matching_file:
                results.append({
                    "ma_ho": ma_ho,
                    "found": "YES",
                    "file_name": matching_file['file_name'],
                    "file_id": matching_file['file_id'],
                    "folder_path": matching_file['folder_path']
                })
                print(f"  ✓ {ma_ho} found in {matching_file['file_name']}")
            else:
                results.append({
                    "ma_ho": ma_ho,
                    "found": "NO",
                    "file_name": "",
                    "file_id": "",
                    "folder_path": ""
                })
                print(f"  ✗ {ma_ho} not found")
        
        # Step 6: Create RESULT sheet and save
        print("Creating RESULT sheet...")
        excel_processor.create_result_sheet(results)
        output_bytes = excel_processor.save_to_bytes()
        
        print(f"[{datetime.now()}] Processing completed successfully")
        
        # Return the processed Excel file
        return StreamingResponse(
            io.BytesIO(output_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=processed_result.xlsx"
            }
        )
        
    except ValueError as e:
        print(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except FileNotFoundError as e:
        print(f"File not found error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e) + "\nPlease ensure service-account.json is in the backend directory."
        )
    
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during processing: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    
    # Check for service account file
    if not os.path.exists("service-account.json"):
        print("\n⚠️  WARNING: service-account.json not found!")
        print("Please place your Google Service Account JSON file in the backend directory.")
        print("The service account must have read access to the Google Drive folders.\n")
    
    print("Starting ISO Piping File Processor API...")
    print("API will be available at: http://localhost:8000")
    print("API documentation at: http://localhost:8000/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
