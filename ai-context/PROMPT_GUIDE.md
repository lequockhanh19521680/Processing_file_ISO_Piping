# AI Prompt Guide: ISO Piping File Processor

## How to Prompt AI for This Project

### Context to Always Provide

When asking AI to help with this project, start with:

```
I'm working on the ISO Piping File Processor, a full-stack application that:
- Has a React frontend for uploading Excel files
- Has a FastAPI Python backend that processes files
- Searches for ma_ho identifiers in PDF files stored in Google Drive
- Uses service account authentication for Google Drive API
- Extracts text from PDFs and caches them for searching
```

Then include the relevant AI context file(s):
- `PROJECT_CONTEXT.md` - for overall understanding
- `ARCHITECTURE.md` - for technical implementation details
- `DOMAIN_GLOSSARY.md` - for domain-specific terminology

### Quick Reference Links

**Codebase Structure**:
```
/frontend
  /src
    - App.jsx (main React component)
    - App.css (styling)
    - main.jsx (entry point)
    - index.css (global styles)
  - package.json
  - vite.config.js

/backend
  - main.py (FastAPI app)
  - drive_service.py (Google Drive integration)
  - pdf_utils.py (PDF text extraction)
  - excel_utils.py (Excel reading/writing)
  - requirements.txt

/ai-context
  - PROJECT_CONTEXT.md
  - ARCHITECTURE.md
  - DOMAIN_GLOSSARY.md
  - PROMPT_GUIDE.md (this file)
```

---

## Common Task Prompts

### Feature Addition Prompts

#### Add OCR Support

```
I want to add OCR support to the ISO Piping File Processor to handle scanned PDFs.

Current behavior: Only extracts text from text-based PDFs using PyPDF2.
Desired behavior: Also extract text from scanned/image-based PDFs using OCR.

Requirements:
- Use pytesseract or similar OCR library
- Only use OCR if PyPDF2 extraction returns empty or minimal text
- Add configuration option to enable/disable OCR (default: disabled)
- Update frontend to show OCR status during processing
- Maintain existing caching mechanism

Files to modify:
- backend/pdf_utils.py (add OCR extraction method)
- backend/main.py (add OCR configuration)
- backend/requirements.txt (add pytesseract dependency)
- frontend/src/App.jsx (add OCR toggle option)

Please maintain backward compatibility and existing performance characteristics.
```

#### Add Progress Streaming

```
Add real-time progress updates to the ISO Piping File Processor.

Current behavior: Frontend shows generic "Processing..." until completion.
Desired behavior: Stream progress updates as backend processes files.

Requirements:
- Use WebSocket or Server-Sent Events (SSE) for real-time updates
- Show progress for each phase:
  - "Reading Excel file..."
  - "Found X ma_ho values"
  - "Listing PDF files..."
  - "Found Y PDFs"
  - "Processing PDF 1/Y..."
  - "Searching for ma_ho values..."
  - "Creating result sheet..."
- Update frontend progress bar with percentage
- Don't break existing single-request functionality

Files to modify:
- backend/main.py (add SSE endpoint)
- frontend/src/App.jsx (add SSE client, progress bar component)
- frontend/src/App.css (add progress bar styling)

Consider using FastAPI's StreamingResponse with SSE format.
```

#### Support Multiple Folders

```
Enable searching across multiple Google Drive folders in the ISO Piping File Processor.

Current behavior: Accepts one folder link.
Desired behavior: Accept multiple folder links and search all of them.

Requirements:
- Frontend: Change text input to textarea or multi-input component
- Accept comma-separated or newline-separated folder links
- Process all folders sequentially
- Aggregate all PDFs from all folders
- Include source folder name in folder_path column
- Validate all folder links before processing

Files to modify:
- frontend/src/App.jsx (change input component, validation)
- backend/main.py (accept list of folder links)
- backend/drive_service.py (process multiple folder IDs)
- backend/excel_utils.py (update folder_path format)

Maintain existing error handling and validation patterns.
```

---

### Performance Optimization Prompts

#### Optimize Large Folder Performance

```
Optimize the ISO Piping File Processor for folders with 1000+ PDF files.

Current bottlenecks:
- Sequential PDF downloads (no parallelization)
- All PDF text held in memory simultaneously
- No progress indication during long operations

Optimization requirements:
- Implement concurrent PDF downloads (use asyncio, max 10 concurrent)
- Add LRU cache with size limit instead of unlimited memory cache
- Add database (SQLite) for persistent PDF text caching between sessions
- Implement request timeout handling (max 5 minutes)
- Add server-side pagination for very large result sets

Files to modify:
- backend/main.py (add async/await, timeout handling)
- backend/drive_service.py (make download async)
- backend/pdf_utils.py (implement LRU cache, add SQLite caching)
- backend/requirements.txt (add aiohttp, cachetools, sqlalchemy)

Consider using `asyncio.gather()` with semaphore for controlled concurrency.
Please provide a migration path for existing deployments.
```

#### Reduce Memory Usage

```
Reduce memory footprint of the ISO Piping File Processor.

Current issue: All PDF texts cached in memory causes OOM with many large PDFs.

Requirements:
- Implement streaming PDF processing (process one at a time)
- Use file-based caching (temp directory) instead of memory cache
- Add configurable cache size limit
- Implement cache eviction strategy (LRU)
- Monitor and log memory usage during processing

Files to modify:
- backend/pdf_utils.py (replace dict with file-based cache)
- backend/main.py (add memory monitoring)
- backend/requirements.txt (add diskcache or joblib)

Trade-offs to consider:
- Disk I/O vs memory usage
- Cache persistence between requests
- Cleanup strategy for cache files

Please provide configuration options for cache directory and size limits.
```

---

### Deployment Prompts

#### Deploy to AWS

```
Help me deploy the ISO Piping File Processor to AWS.

Current setup: Local development (React dev server + Python uvicorn).

Deployment requirements:
- Frontend: AWS S3 + CloudFront for static hosting
- Backend: AWS Elastic Beanstalk or ECS (containerized)
- Secrets: Store service-account.json in AWS Secrets Manager
- Database: Optional - RDS for persistent caching
- HTTPS: Use AWS Certificate Manager
- CORS: Configure for production domain

Deliverables:
1. Dockerfile for backend
2. Docker Compose for local testing
3. AWS CloudFormation or Terraform templates
4. CI/CD pipeline (GitHub Actions)
5. Environment variable configuration
6. Deployment documentation

Consider cost optimization and auto-scaling for variable workloads.
```

#### Containerize Application

```
Containerize the ISO Piping File Processor using Docker.

Requirements:
- Multi-stage Dockerfile for frontend (build + nginx)
- Python Dockerfile for backend
- docker-compose.yml for local development
- Production-ready configuration
- Volume mounts for service account credentials
- Environment variable configuration
- Health check endpoints
- Logging to stdout/stderr

Files to create:
- frontend/Dockerfile
- backend/Dockerfile
- docker-compose.yml
- docker-compose.prod.yml
- .dockerignore (both frontend and backend)

Optimization requirements:
- Minimize image sizes
- Use layer caching effectively
- Pin dependency versions
- Security scanning with Trivy

Include setup instructions in README.
```

---

### Debugging Prompts

#### Debug PDF Text Extraction Issues

```
Help me debug why certain PDFs aren't extracting text correctly.

Context: ISO Piping File Processor using PyPDF2 for text extraction.

Symptoms:
- Some PDFs report as "not found" but manual check shows ma_ho exists
- Extract_text() returns empty string for some PDFs
- No error messages logged

What I need:
1. Add detailed logging for PDF extraction process
2. Create a debug mode that saves extracted text to files
3. Add PDF metadata inspection (pages, encoding, version)
4. Implement fallback extraction methods
5. Add validation test suite for different PDF types

Files to modify:
- backend/pdf_utils.py (add debug logging and fallbacks)
- backend/main.py (add debug mode parameter)

Please help identify why text extraction fails and provide workarounds.
```

#### Investigate Google Drive API Errors

```
Debug Google Drive API authentication and permission issues.

Current errors:
- "HttpError 403: User does not have sufficient permissions"
- Intermittent authentication failures

What I need:
1. Detailed logging of all Drive API calls
2. Validation of service account permissions
3. Retry logic for transient errors
4. Better error messages for common permission issues
5. Test script to validate Drive access before processing

Files to modify:
- backend/drive_service.py (add logging, retry logic, validation)
- backend/main.py (improve error messages)

Context file: ARCHITECTURE.md (Google Drive Integration section)

Please provide checklist for validating service account setup.
```

---

### Testing Prompts

#### Add Unit Tests

```
Add comprehensive unit tests for the ISO Piping File Processor backend.

Requirements:
- Use pytest as test framework
- Mock Google Drive API calls
- Test all modules (excel_utils, pdf_utils, drive_service, main)
- Achieve >80% code coverage
- Include edge cases and error conditions

Test structure:
```
/backend
  /tests
    - test_excel_utils.py
    - test_pdf_utils.py
    - test_drive_service.py
    - test_main.py
    - conftest.py (fixtures)
    /fixtures
      - sample.xlsx
      - sample.pdf
```

Files to modify:
- backend/requirements.txt (add pytest, pytest-cov, pytest-mock)
- Create all test files

Test scenarios to cover:
- Valid and invalid Excel files
- PDF text extraction and caching
- Drive URL parsing
- API error handling
- Result sheet generation

Include README section on running tests.
```

#### Add Integration Tests

```
Create integration tests that validate end-to-end functionality.

Requirements:
- Test actual API endpoints (not mocked)
- Use test fixtures for Google Drive folder
- Validate complete processing pipeline
- Test concurrent requests
- Test error scenarios

Test approach:
1. Create dedicated test Google Drive folder
2. Upload known test PDFs with specific ma_ho values
3. Create test Excel file with those ma_ho values
4. Run full processing
5. Validate RESULT sheet contents

Tools to use:
- pytest with httpx for API testing
- Test service account with access to test folder

Files to create:
- backend/tests/integration/test_process_endpoint.py
- backend/tests/integration/test_fixtures.py

Include documentation on setting up test environment.
```

---

### Documentation Prompts

#### Generate API Documentation

```
Create comprehensive API documentation for the ISO Piping File Processor backend.

Requirements:
- OpenAPI/Swagger specification (FastAPI auto-generates)
- Detailed endpoint documentation
- Request/response examples
- Error code reference
- Authentication guide
- Rate limiting information (if implemented)

Documentation should include:
1. API overview and base URL
2. Authentication setup (service account)
3. POST /process endpoint details:
   - Parameters (file, drive_link)
   - Success response (Excel file)
   - Error responses (400, 500)
   - Example curl commands
4. Health check endpoint (GET /)

Output format:
- Markdown file (API_DOCUMENTATION.md)
- Enhanced FastAPI OpenAPI descriptions
- Postman collection export

FastAPI already provides /docs endpoint - enhance the automatic documentation.
```

#### Create Setup Guide for Non-Technical Users

```
Write a beginner-friendly setup guide for the ISO Piping File Processor.

Target audience: Engineers with minimal programming experience.

Guide should include:
1. Prerequisites (Python, Node.js installation)
2. Step-by-step setup instructions with screenshots
3. How to obtain and configure Google Service Account
4. How to share Drive folders with service account
5. Running the application locally
6. Common troubleshooting issues
7. FAQ section

Format: Markdown with embedded images.
File: SETUP_GUIDE.md

Use simple language and include:
- Expected output at each step
- What to do if something goes wrong
- Validation steps to ensure correct setup
- Example test files to verify functionality
```

---

## Advanced Modification Prompts

#### Migrate from PyPDF2 to pdfplumber

```
Replace PyPDF2 with pdfplumber for better text extraction accuracy.

Reason: pdfplumber provides more reliable text extraction for complex PDFs.

Requirements:
- Replace PyPDF2 with pdfplumber in pdf_utils.py
- Maintain existing caching mechanism
- Ensure API compatibility (same function signatures)
- Add configuration option to choose extraction library
- Benchmark performance comparison

Files to modify:
- backend/pdf_utils.py (update extract_text method)
- backend/requirements.txt (replace PyPDF2 with pdfplumber)

Testing:
- Verify all existing functionality works
- Compare extraction quality on sample PDFs
- Measure performance impact

Include migration notes in documentation.
```

#### Add Database for Job Queue

```
Implement background job processing with database queue.

Current issue: Long-running requests timeout, no job status tracking.

Requirements:
- Add PostgreSQL or SQLite database
- Implement job queue (using Celery or RQ)
- Create job status endpoint (GET /jobs/{job_id})
- Update frontend to poll for job status
- Store job results in database

Architecture changes:
1. POST /process creates job, returns job_id immediately
2. Background worker processes job
3. Frontend polls GET /jobs/{job_id} for status
4. When complete, fetch result from GET /results/{job_id}

Files to modify:
- backend/main.py (add job creation and status endpoints)
- backend/requirements.txt (add celery, redis, sqlalchemy)
- frontend/src/App.jsx (implement polling logic)
- Add: backend/worker.py (Celery worker)
- Add: backend/models.py (SQLAlchemy models)
- Add: backend/database.py (DB connection)

Include Docker setup for Redis and PostgreSQL.
```

---

## Context Assumptions for AI

When prompting AI about this project, the AI should assume:

### Technical Context
- **Language versions**: Python 3.9+, Node.js 18+, React 18
- **Development OS**: Works on Linux, macOS, Windows
- **Browser support**: Modern browsers (Chrome, Firefox, Safari, Edge)
- **Network**: Requires internet access for Google Drive API

### Project Constraints
- **Code style**: Follow existing patterns in codebase
- **Dependencies**: Minimize new dependencies
- **Backward compatibility**: Don't break existing functionality
- **Performance**: Consider 100-1000 PDF files as typical use case
- **Security**: Never commit credentials or secrets

### Architecture Decisions
- **No database** (current): All state in memory or files
- **Single-threaded** (current): Sequential processing
- **Stateless** (current): No session management
- **CORS enabled**: Frontend and backend on different ports

### User Assumptions
- **Technical level**: Basic computer skills
- **Use case**: Occasional batch processing (not real-time)
- **Access**: Has Google Drive folder access
- **Environment**: Running locally or on internal network

---

## Quick Command Reference

### Development Commands

**Backend**:
```bash
cd backend
pip install -r requirements.txt
python main.py
# Runs on http://localhost:8000
```

**Frontend**:
```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:3000
```

### Testing Commands
```bash
# Backend tests (when implemented)
cd backend
pytest tests/ -v --cov=.

# Frontend tests (when implemented)
cd frontend
npm test
```

### Build Commands
```bash
# Frontend production build
cd frontend
npm run build
# Output in frontend/dist/
```

### Docker Commands (when containerized)
```bash
docker-compose up --build
docker-compose down
```

---

## Troubleshooting Prompts

#### "Service account file not found"
```
Help me resolve "service-account.json not found" error.

What I've tried:
- [List what you've attempted]

What I need:
1. Verification steps for service account file location
2. How to validate JSON file format
3. Alternative authentication methods
4. Debug logging to see what path is being checked

Context: ARCHITECTURE.md (Google Drive Integration section)
```

#### "Cannot connect to server"
```
Frontend shows "Cannot connect to server" error.

Environment:
- Frontend running on: [URL]
- Backend running on: [URL]
- CORS configuration: [settings]

What I need:
1. Verify CORS configuration
2. Check if backend is actually running
3. Test with curl command
4. Browser console error analysis

Files to check:
- backend/main.py (CORS middleware)
- frontend/src/App.jsx (API_BASE_URL)
```

#### "Excel file validation failed"
```
Backend rejects valid-looking Excel file.

Error message: [paste error]

What I need:
1. Detailed validation logic explanation
2. How to inspect Excel file structure
3. Common formatting issues
4. Tool to validate Excel file before upload

Context: DOMAIN_GLOSSARY.md (xlsx section)
Reference: backend/excel_utils.py (read_input_excel method)
```

---

## Best Practices for AI Collaboration

### DO:
✅ Provide specific error messages and logs
✅ Reference relevant AI context files (PROJECT_CONTEXT.md, etc.)
✅ Describe desired behavior, not just problems
✅ Mention what you've already tried
✅ Ask for explanations along with code changes
✅ Request tests for new functionality
✅ Ask for documentation updates

### DON'T:
❌ Ask for complete rewrites without justification
❌ Request features without considering existing architecture
❌ Ignore performance implications
❌ Forget about backward compatibility
❌ Skip error handling in new code
❌ Add dependencies without considering alternatives

### Example Good Prompt Structure:
```
[Specific goal]
Current behavior: [what happens now]
Desired behavior: [what should happen]

Requirements:
- [Specific requirement 1]
- [Specific requirement 2]

Files to modify:
- [file 1] (what changes)
- [file 2] (what changes)

Context files: [relevant .md files]
Constraints: [performance, compatibility, etc.]

Please include [tests/docs/examples].
```

---

This guide should be updated as the project evolves and new patterns emerge.
