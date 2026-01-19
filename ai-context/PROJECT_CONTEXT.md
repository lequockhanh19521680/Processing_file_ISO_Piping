# Project Context: ISO Piping File Processor

## Purpose

This application automates the process of searching for specific identifiers (ma_ho values) within PDF documents stored in Google Drive folders. It streamlines quality control and documentation verification workflows for ISO piping projects.

## High-Level Problem Statement

Engineers and quality control teams need to verify that specific piping identifiers (ma_ho codes) appear in PDF documentation. Manually searching through hundreds of PDF files across multiple folders is time-consuming and error-prone. This application solves this by:

1. Reading a list of ma_ho identifiers from an Excel spreadsheet
2. Recursively scanning all PDF files in a specified Google Drive folder
3. Searching for each ma_ho value in the PDF content (not filenames)
4. Generating a comprehensive report showing which identifiers were found and where

## End-to-End Data Flow

```
User (Browser)
    ↓
    1. Uploads Excel file with ma_ho values
    2. Provides Google Drive folder link
    ↓
React Frontend (Port 3000)
    ↓
    3. Sends POST request with file + link
    ↓
FastAPI Backend (Port 8000)
    ↓
    4. Reads Excel → extracts ma_ho values
    5. Authenticates with Google Drive (Service Account)
    6. Lists all PDFs recursively in folder
    7. Downloads each PDF once
    8. Extracts text from PDFs (cached)
    9. Searches for each ma_ho in all PDF texts
    10. Creates RESULT sheet in Excel
    ↓
    11. Returns processed Excel file
    ↓
React Frontend
    ↓
    12. Offers file download to user
```

## Core Constraints and Assumptions

### Assumptions
- **PDF Format**: PDFs are text-based (not scanned images) - no OCR required
- **Network Access**: Application has internet access to Google Drive API
- **Service Account**: Google Service Account JSON file is available with read access to target Drive folders
- **Excel Format**: Input Excel has exactly one sheet with column A header "ma_ho"
- **Case-Insensitive Search**: ma_ho searches are case-insensitive
- **Single Match**: Only the first matching file for each ma_ho is recorded

### Constraints
- **Performance**: Downloads each PDF once and caches extracted text in memory
- **Memory**: All PDF text is cached during processing (consider memory limits for very large folders)
- **Concurrency**: Single-threaded processing (no parallel PDF downloads)
- **Authentication**: Uses service account (not OAuth user authentication)
- **File Types**: Only processes PDF files, ignores other file types
- **Search Method**: Simple substring matching in extracted text

## Key Features

1. **Recursive Folder Scanning**: Searches through nested folder structures
2. **Text Caching**: Extracts PDF text once and caches for multiple searches
3. **Progress Tracking**: Console logging shows processing status
4. **Error Handling**: Graceful handling of download failures and invalid files
5. **Clean UI**: Simple, intuitive interface for non-technical users
6. **CORS Enabled**: Frontend and backend can run on different ports

## Technology Stack

- **Frontend**: React 18 with Vite, Axios
- **Backend**: Python FastAPI, Uvicorn
- **PDF Processing**: PyPDF2
- **Excel Processing**: openpyxl
- **Google Drive**: google-api-python-client with service account auth
- **Styling**: Pure CSS (no external UI frameworks)

## Security Considerations

- Service account credentials must never be committed to version control
- .gitignore explicitly excludes *.json files (except package.json)
- CORS should be restricted to specific frontend URL in production
- No sensitive data is logged or stored permanently
- All file processing happens in memory (no disk storage of uploads)
