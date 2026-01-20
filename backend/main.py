"""
FastAPI Backend for Processing ISO Piping Files

Main application that orchestrates Excel processing, Google Drive file search,
and PDF text extraction to match ma_ho values against PDF content.
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, AsyncGenerator
import io
import os
from datetime import datetime
import asyncio
import json
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed

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
# WARNING: In production, replace "*" with your specific frontend URL(s)
# Example: allow_origins=["https://your-frontend-domain.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/process-with-progress")
async def process_file_with_progress(
    file: UploadFile = File(..., description="Excel file with ma_ho values"),
    drive_link: str = Form(..., description="Google Drive folder URL")
):
    """
    Process Excel file with real-time progress updates using Server-Sent Events.
    
    Returns a stream of progress events followed by the final Excel file.
    """
    # FIX: Read file content immediately while the file is still open.
    # FastAPI closes the UploadFile immediately after the request handler returns,
    # causing "I/O operation on closed file" if we try to read it inside the 
    # StreamingResponse generator later.
    try:
        file_content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read upload file: {str(e)}")

    async def generate_progress_and_file():
        try:
            # Send initial progress
            yield f"data: {json.dumps({'type': 'progress', 'stage': 'reading_excel', 'message': 'Reading Excel file...'})}\n\n"
            
            # Step 1: Process the already read Excel file content
            excel_processor = ExcelProcessor()
            # Use the variable 'file_content' read above, instead of reading 'file' again
            ma_ho_values = excel_processor.read_input_excel(file_content)
            
            yield f"data: {json.dumps({'type': 'progress', 'stage': 'excel_read', 'message': f'Found {len(ma_ho_values)} ma_ho values', 'count': len(ma_ho_values)})}\n\n"
            
            if not ma_ho_values:
                yield f"data: {json.dumps({'type': 'error', 'message': 'No ma_ho values found in Excel file'})}\n\n"
                return
            
            # Step 2: Authenticate with Google Drive
            yield f"data: {json.dumps({'type': 'progress', 'stage': 'authenticating', 'message': 'Authenticating with Google Drive...'})}\n\n"
            drive_service = DriveService()
            drive_service.authenticate()
            
            # Step 3: Extract folder ID and list all PDF files
            yield f"data: {json.dumps({'type': 'progress', 'stage': 'listing_files', 'message': 'Listing PDF files in Drive folder...'})}\n\n"
            folder_id = drive_service.extract_folder_id(drive_link)
            pdf_files = drive_service.list_pdf_files_recursive(folder_id)
            
            yield f"data: {json.dumps({'type': 'progress', 'stage': 'files_listed', 'message': f'Found {len(pdf_files)} PDF files', 'total_files': len(pdf_files)})}\n\n"
            
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
                
                yield f"data: {json.dumps({'type': 'complete', 'message': 'Processing complete (no PDFs found)'})}\n\n"
                # Send the file as base64
                file_b64 = base64.b64encode(output_bytes).decode('utf-8')
                yield f"data: {json.dumps({'type': 'file', 'data': file_b64, 'filename': 'processed_result.xlsx'})}\n\n"
                return
            
            # Step 4: Download and extract text from all PDFs in parallel
            yield f"data: {json.dumps({'type': 'progress', 'stage': 'processing_pdfs', 'message': 'Processing PDFs in parallel...'})}\n\n"
            pdf_extractor = PDFTextExtractor()
            pdf_text_data = []
            
            # Use ThreadPoolExecutor for parallel processing
            max_workers = min(10, len(pdf_files))
            processed_count = 0
            
            def process_with_progress(pdf_info):
                # Create a new drive service instance per thread for thread safety
                thread_drive_service = DriveService()
                thread_drive_service.service = drive_service.service  # Reuse authenticated service
                return _download_and_extract_pdf(thread_drive_service, pdf_extractor, pdf_info)
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_pdf = {
                    executor.submit(process_with_progress, pdf_info): pdf_info 
                    for pdf_info in pdf_files
                }
                
                for future in as_completed(future_to_pdf):
                    pdf_info = future_to_pdf[future]
                    try:
                        result = future.result()
                        if result:
                            pdf_text_data.append(result)
                        processed_count += 1
                        
                        # Send progress update every 10 files or at key milestones
                        if processed_count % 10 == 0 or processed_count == len(pdf_files):
                            progress_data = {
                                'type': 'progress',
                                'stage': 'processing_pdfs',
                                'message': f'Processing PDF {processed_count}/{len(pdf_files)}: {pdf_info["file_name"]}',
                                'current': processed_count,
                                'total': len(pdf_files)
                            }
                            yield f"data: {json.dumps(progress_data)}\n\n"
                    except Exception as e:
                        print(f"Error processing {pdf_info['file_name']}: {str(e)}")
            
            yield f"data: {json.dumps({'type': 'progress', 'stage': 'pdfs_processed', 'message': f'Extracted text from {len(pdf_text_data)} PDFs'})}\n\n"
            
            # Step 5: Search for each ma_ho in all PDF texts
            yield f"data: {json.dumps({'type': 'progress', 'stage': 'searching', 'message': 'Searching for ma_ho values...'})}\n\n"
            results = []
            
            for idx, ma_ho in enumerate(ma_ho_values, 1):
                found = False
                matching_file = None
                
                for pdf_data in pdf_text_data:
                    if pdf_extractor.search_text(pdf_data['text'], ma_ho):
                        found = True
                        matching_file = pdf_data
                        break
                
                if found and matching_file:
                    results.append({
                        "ma_ho": ma_ho,
                        "found": "YES",
                        "file_name": matching_file['file_name'],
                        "file_id": matching_file['file_id'],
                        "folder_path": matching_file['folder_path']
                    })
                    yield f"data: {json.dumps({'type': 'search_result', 'ma_ho': ma_ho, 'found': True, 'file_name': matching_file['file_name'], 'current': idx, 'total': len(ma_ho_values)})}\n\n"
                else:
                    results.append({
                        "ma_ho": ma_ho,
                        "found": "NO",
                        "file_name": "",
                        "file_id": "",
                        "folder_path": ""
                    })
                    yield f"data: {json.dumps({'type': 'search_result', 'ma_ho': ma_ho, 'found': False, 'current': idx, 'total': len(ma_ho_values)})}\n\n"
            
            # Step 6: Create RESULT sheet and save
            yield f"data: {json.dumps({'type': 'progress', 'stage': 'creating_result', 'message': 'Creating result sheet...'})}\n\n"
            excel_processor.create_result_sheet(results)
            output_bytes = excel_processor.save_to_bytes()
            
            yield f"data: {json.dumps({'type': 'complete', 'message': 'Processing complete!'})}\n\n"
            
            # Send the file as base64
            file_b64 = base64.b64encode(output_bytes).decode('utf-8')
            yield f"data: {json.dumps({'type': 'file', 'data': file_b64, 'filename': 'processed_result.xlsx'})}\n\n"
            
        except Exception as e:
            print(f"Error in process_file_with_progress: {str(e)}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_progress_and_file(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
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
        
        # Step 4: Download and extract text from all PDFs in parallel
        print("Downloading and extracting text from PDFs in parallel...")
        pdf_extractor = PDFTextExtractor()
        pdf_text_data = []
        
        # Use ThreadPoolExecutor for parallel processing
        max_workers = min(10, len(pdf_files))  # Limit concurrent downloads
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_pdf = {
                executor.submit(
                    _download_and_extract_pdf, 
                    drive_service, 
                    pdf_extractor, 
                    pdf_info
                ): pdf_info 
                for pdf_info in pdf_files
            }
            
            # Process completed tasks
            for idx, future in enumerate(as_completed(future_to_pdf), 1):
                pdf_info = future_to_pdf[future]
                try:
                    result = future.result()
                    if result:
                        pdf_text_data.append(result)
                        print(f"Processed PDF {idx}/{len(pdf_files)}: {pdf_info['file_name']}")
                except Exception as e:
                    print(f"Error processing {pdf_info['file_name']}: {str(e)}")
        
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


def _download_and_extract_pdf(drive_service: DriveService, pdf_extractor: PDFTextExtractor, pdf_info: Dict) -> Dict:
    """
    Helper function to download and extract text from a single PDF.
    Used for parallel processing.
    """
    try:
        # Download PDF content
        pdf_content = drive_service.download_file(pdf_info['file_id'])
        if not pdf_content:
            return None
        
        # Extract text (cached)
        text = pdf_extractor.extract_text(pdf_content, pdf_info['file_id'])
        
        return {
            'file_id': pdf_info['file_id'],
            'file_name': pdf_info['file_name'],
            'folder_path': pdf_info['folder_path'],
            'text': text
        }
    except Exception as e:
        print(f"Error in _download_and_extract_pdf for {pdf_info['file_name']}: {str(e)}")
        return None


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