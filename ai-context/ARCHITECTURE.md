# Architecture: ISO Piping File Processor

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Browser                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │         React Frontend (Port 3000)                  │    │
│  │  - File upload component                            │    │
│  │  - Form validation                                  │    │
│  │  - Progress indicators                              │    │
│  │  - File download handler                            │    │
│  └────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP POST /process
                            │ (multipart/form-data)
                            ↓
┌─────────────────────────────────────────────────────────────┐
│               FastAPI Backend (Port 8000)                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │  main.py - Request orchestration                    │    │
│  │    ↓         ↓         ↓         ↓                  │    │
│  │  excel_   drive_     pdf_     Response              │    │
│  │  utils    service   utils     handler               │    │
│  └────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────┘
                            │ Google Drive API
                            │ (Service Account Auth)
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Google Drive Storage                      │
│  - Folder hierarchy with PDF files                         │
│  - Accessed via REST API                                   │
└─────────────────────────────────────────────────────────────┘
```

## Frontend Architecture

### Component Structure
```
App.jsx (Main Component)
│
├─ State Management (React hooks)
│  ├─ file: uploaded Excel file
│  ├─ driveLink: Google Drive URL
│  ├─ loading: processing status
│  ├─ error: error messages
│  ├─ success: success messages
│  └─ downloadUrl: processed file blob URL
│
├─ Event Handlers
│  ├─ handleFileChange: validate and store file
│  ├─ handleDriveLinkChange: store Drive URL
│  ├─ handleSubmit: send request to backend
│  └─ handleDownload: trigger file download
│
└─ UI Components
   ├─ File upload input
   ├─ Text input (Drive link)
   ├─ Submit button (with loading state)
   ├─ Alert messages (error/success)
   └─ Download button (conditional)
```

### Frontend-Backend Interaction

**Request Flow**:
1. User fills form and clicks "OK"
2. Client-side validation checks file and link
3. FormData object created with file and drive_link
4. Axios POST to `http://localhost:8000/process`
5. Response type set to 'blob' for binary file download
6. Blob converted to downloadable URL

**Error Handling**:
- Network errors: "Cannot connect to server"
- Server errors: Display detail message from response
- Validation errors: Display before sending request

## Backend Architecture

### Module Responsibilities

#### main.py (Orchestrator)
- **Role**: API endpoint and request coordination
- **Responsibilities**:
  - Receive multipart/form-data
  - Orchestrate processing pipeline
  - Handle exceptions and return appropriate HTTP responses
  - Enable CORS for frontend access
- **Key Functions**:
  - `root()`: Health check endpoint
  - `process_file()`: Main processing endpoint

#### excel_utils.py (Excel Handler)
- **Role**: Excel file reading and writing
- **Responsibilities**:
  - Read input Excel and extract ma_ho values
  - Validate Excel structure (check for "ma_ho" header)
  - Create RESULT sheet with findings
  - Format and save output Excel
- **Key Class**: `ExcelProcessor`
  - `read_input_excel()`: Extract ma_ho values
  - `create_result_sheet()`: Add results sheet
  - `save_to_bytes()`: Return Excel as bytes

#### drive_service.py (Google Drive Interface)
- **Role**: Google Drive API integration
- **Responsibilities**:
  - Authenticate with service account
  - Parse folder ID from Drive URL
  - Recursively list all PDF files
  - Download file contents
- **Key Class**: `DriveService`
  - `authenticate()`: Initialize Drive API client
  - `extract_folder_id()`: Parse URL to get folder ID
  - `list_pdf_files_recursive()`: Find all PDFs in folder tree
  - `download_file()`: Get file content as bytes

#### pdf_utils.py (PDF Text Extractor)
- **Role**: PDF text extraction with caching
- **Responsibilities**:
  - Extract text from PDF bytes
  - Cache extracted text by file ID
  - Perform case-insensitive text searches
- **Key Class**: `PDFTextExtractor`
  - `extract_text()`: Extract and cache PDF text
  - `search_text()`: Case-insensitive substring search
  - `text_cache`: Dictionary storing file_id → text

### Processing Pipeline

```python
# Step-by-step execution in main.py process_file()

1. Read Excel File
   └─> excel_processor.read_input_excel(file_content)
       Returns: List[str] of ma_ho values

2. Authenticate Drive
   └─> drive_service.authenticate()
       Loads service-account.json credentials

3. Get PDF Files
   └─> drive_service.extract_folder_id(drive_link)
       └─> drive_service.list_pdf_files_recursive(folder_id)
           Returns: List[Dict] with file_id, file_name, folder_path

4. Extract PDF Texts (with caching)
   For each PDF:
     └─> drive_service.download_file(file_id)
         └─> pdf_extractor.extract_text(pdf_content, file_id)
             Returns: str (cached for subsequent searches)

5. Search for ma_ho values
   For each ma_ho:
     For each cached PDF text:
       └─> pdf_extractor.search_text(text, ma_ho)
           First match → record result, break

6. Create Result Sheet
   └─> excel_processor.create_result_sheet(results)
       └─> excel_processor.save_to_bytes()
           Returns: bytes (Excel file)

7. Return Response
   └─> StreamingResponse with Excel file
```

## Google Drive Integration

### Authentication Flow
```
service-account.json (credentials file)
        ↓
service_account.Credentials.from_service_account_file()
        ↓
build('drive', 'v3', credentials=credentials)
        ↓
Authenticated Drive API client
```

### API Operations Used

1. **List Files**: `files().list(q=query, fields="...")`
   - Query: `'{folder_id}' in parents and trashed=false`
   - Returns: Files and folders in specified folder
   - Fields: id, name, mimeType

2. **Download File**: `files().get_media(fileId=file_id)`
   - Returns: MediaIoBaseDownload stream
   - Downloaded in chunks to BytesIO buffer

### Recursive Folder Traversal
```python
def list_pdf_files_recursive(folder_id, parent_path):
    for item in folder_contents:
        if item.mimeType == 'folder':
            # Recurse into subfolder
            results += list_pdf_files_recursive(item.id, parent_path + "/" + item.name)
        elif item.mimeType == 'application/pdf':
            # Add PDF to results
            results.append({file_id, file_name, folder_path})
    return results
```

## PDF Processing Pipeline

### Text Extraction Strategy
1. **Download Once**: Each PDF downloaded once regardless of ma_ho count
2. **Cache Aggressively**: Store extracted text in memory dictionary
3. **Fast Search**: Use Python's `in` operator on cached strings
4. **Case-Insensitive**: Convert both text and search term to lowercase

### Memory Considerations
- **Trade-off**: Memory usage vs. speed
- **Current**: All PDF texts cached in memory during processing
- **Limitation**: May hit memory limits with thousands of large PDFs
- **Future**: Could implement LRU cache or disk-based caching

## Performance Considerations

### Current Performance Characteristics

**Bottlenecks**:
1. Google Drive API rate limits
2. Sequential PDF downloads (no parallelization)
3. PDF text extraction (CPU-intensive)
4. Network latency for each file download

**Optimization Strategies**:
- ✅ Implemented: Text caching (extract once, search many)
- ✅ Implemented: Single pass through PDFs
- ❌ Not implemented: Parallel downloads
- ❌ Not implemented: Progress streaming to frontend
- ❌ Not implemented: Incremental results

### Scalability Limits

**Current Design Handles**:
- ✓ 100s of ma_ho values
- ✓ 100s of PDF files
- ✓ PDF files up to ~10 MB each

**May Struggle With**:
- ✗ 1000+ PDF files (time)
- ✗ Very large PDFs (>50 MB)
- ✗ Slow network connections
- ✗ Drive API rate limits

**Recommended Improvements for Scale**:
1. Add progress websocket for real-time updates
2. Implement concurrent PDF downloads (asyncio)
3. Add database for persistent caching
4. Implement background job queue (Celery/Redis)
5. Add pagination for large result sets

## Deployment Considerations

### Local Development
- Frontend: `npm run dev` on port 3000
- Backend: `python main.py` on port 8000
- Service account file must be in `backend/` directory

### Production Deployment
- **Frontend**: Build with `npm run build`, serve static files
- **Backend**: Use production ASGI server (uvicorn with workers)
- **Environment Variables**: Store service account credentials securely
- **CORS**: Restrict to specific frontend domain
- **Monitoring**: Add logging and error tracking
- **Scaling**: Consider containerization (Docker) and orchestration (Kubernetes)

### Security Checklist
- [ ] Service account credentials in secure vault (not in code)
- [ ] CORS restricted to production frontend URL
- [ ] HTTPS for all communications
- [ ] Input validation and sanitization
- [ ] Rate limiting on API endpoints
- [ ] File size limits enforced
- [ ] Error messages don't leak sensitive info
