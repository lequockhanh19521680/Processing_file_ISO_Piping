# Domain Glossary: ISO Piping File Processor

## Core Terms

### ma_ho
**Definition**: A unique identifier code used in ISO piping projects to reference specific piping components, assemblies, or documentation sections.

**Context**: 
- Appears in technical drawings, specifications, and quality control documents
- Must be tracked and verified across multiple PDF documents
- Case-insensitive (e.g., "MA-001" matches "ma-001" or "Ma-001")
- Can contain alphanumeric characters, hyphens, underscores

**Usage in Application**:
- Input: Read from column A of uploaded Excel file
- Processing: Searched for in PDF document text content
- Output: Listed in RESULT sheet with found/not found status

**Example Values**:
- `ISO-P-001`
- `MA-PIPE-2024-123`
- `VALVE_A001`

---

### Google Drive Folder
**Definition**: A directory in Google Drive cloud storage that contains PDF files and potentially nested subfolders.

**Characteristics**:
- Identified by a unique folder ID in the URL
- Can contain unlimited nested subdirectories
- Access controlled via Google Drive permissions
- Service account must have read access

**URL Formats**:
```
https://drive.google.com/drive/folders/{FOLDER_ID}
https://drive.google.com/drive/u/0/folders/{FOLDER_ID}
```

**Application Behavior**:
- Recursively scans all subdirectories
- Only processes PDF files (ignores other file types)
- Preserves folder path information in results

---

### PDF Text Extraction
**Definition**: The process of reading and converting textual content from PDF files into plain text strings for searching.

**Technical Details**:
- Uses PyPDF2 library's `extract_text()` method
- Extracts text from all pages in the PDF
- Concatenates page texts with spaces
- Does NOT use OCR (optical character recognition)
- Only works with text-based PDFs (not scanned images)

**Limitations**:
- Cannot read text from images embedded in PDFs
- Cannot read scanned documents
- Text extraction quality depends on PDF structure
- Some PDFs with complex layouts may extract text out of order

**Caching Strategy**:
- Each PDF's text is extracted once per processing session
- Cached in memory using file ID as key
- Cache is cleared when processing completes
- Enables fast searching across multiple ma_ho values

---

### RESULT Sheet
**Definition**: A new worksheet added to the processed Excel file that contains the search results for each ma_ho value.

**Column Structure**:

| Column | Name | Type | Description |
|--------|------|------|-------------|
| A | ma_ho | Text | The identifier that was searched for |
| B | found | Text | "YES" if found in any PDF, "NO" if not found |
| C | file_name | Text | Name of the PDF file where ma_ho was found (empty if not found) |
| D | file_id | Text | Google Drive file ID of the matching PDF (empty if not found) |
| E | folder_path | Text | Full folder path where the file is located (empty if not found) |

**Behavior**:
- Always shows ALL ma_ho values from input
- Each ma_ho appears exactly once
- If found in multiple PDFs, only the FIRST match is recorded
- Column widths auto-adjusted for readability

**Example Row**:
```
ma_ho: ISO-P-001
found: YES
file_name: Technical_Specification_Rev2.pdf
file_id: 1aB2cD3eF4gH5iJ6kL7mN8oP9qR0sT
folder_path: /Engineering/Piping/2024
```

---

## Technical Terms

### Service Account
**Definition**: A Google Cloud account used for server-to-server authentication without user interaction.

**Characteristics**:
- Identified by email address (ends with @*.iam.gserviceaccount.com)
- Credentials stored in JSON file
- Used for automated processes
- Requires explicit permission grants on Drive folders

**Setup Requirements**:
1. Create service account in Google Cloud Console
2. Enable Google Drive API
3. Download JSON credentials file
4. Share target Drive folders with service account email
5. Place credentials file in backend directory as `service-account.json`

---

### Multipart Form Data
**Definition**: HTTP request encoding type used to upload files along with text data.

**Usage in Application**:
- Frontend sends POST request with Content-Type: multipart/form-data
- Contains two parts:
  1. `file`: Binary Excel file data
  2. `drive_link`: Text string with Google Drive URL

---

### Blob URL
**Definition**: A temporary URL created in the browser that points to binary data in memory.

**Usage in Application**:
- Created when backend returns processed Excel file
- Enables download without server-side file storage
- Format: `blob:http://localhost:3000/uuid`
- Automatically cleaned up when page unloads

---

### Recursive Listing
**Definition**: A traversal algorithm that explores a directory tree by visiting each folder and its subfolders.

**Implementation**:
```
Start with root folder
For each item in folder:
  If item is a folder:
    Recursively list items in that folder
  If item is a PDF:
    Add to results list
Return all collected PDFs
```

**Depth**: Unlimited - will traverse arbitrarily deep folder structures

---

## Workflow Terms

### Processing Session
**Definition**: The complete lifecycle of one user request, from file upload to result download.

**Phases**:
1. **Initiation**: User submits form with Excel + Drive link
2. **Validation**: Backend checks file format and Drive link format
3. **Discovery**: List all PDF files in Drive folder
4. **Extraction**: Download and extract text from each PDF
5. **Search**: Find each ma_ho in all PDF texts
6. **Assembly**: Create RESULT sheet with findings
7. **Delivery**: Return processed Excel file to user

**Duration**: Varies based on:
- Number of PDF files (1-2 seconds per PDF)
- Size of PDF files
- Network speed
- Google Drive API response time

---

### Case-Insensitive Search
**Definition**: Text matching that treats uppercase and lowercase letters as equivalent.

**Implementation**:
```python
search_term.lower() in pdf_text.lower()
```

**Examples**:
- "ISO-P-001" matches "iso-p-001"
- "Valve" matches "VALVE" and "valve"
- Preserves original text in results

---

## File Format Terms

### .xlsx
**Definition**: Microsoft Excel Open XML Spreadsheet format.

**Requirements for Input File**:
- Must have at least one sheet
- Column A header must be exactly "ma_ho" (case-insensitive)
- Rows 2+ contain ma_ho values to search
- Empty cells in column A are skipped

**Output File Includes**:
- All original sheets (unchanged)
- New "RESULT" sheet with findings
- Preserved formatting from original file

---

### application/pdf
**Definition**: MIME type for PDF (Portable Document Format) files.

**Application Filtering**:
- Google Drive returns mimeType for each file
- Only files with `mimeType == 'application/pdf'` are processed
- Other files (Word, Excel, images, etc.) are ignored

---

## Error Terms

### Not Found
**Definition**: Status when a ma_ho value does not appear in any PDF text.

**Result Entry**:
```
ma_ho: [value]
found: NO
file_name: (empty)
file_id: (empty)
folder_path: (empty)
```

**Possible Reasons**:
- ma_ho doesn't exist in any document
- ma_ho exists in non-PDF files
- PDF is scanned (image-based, not text)
- Text extraction failed for the PDF
- Spelling variation not detected

---

### Authentication Failed
**Definition**: Error when Google Drive API cannot verify service account credentials.

**Common Causes**:
- service-account.json file missing
- Invalid or corrupted JSON file
- Service account disabled
- Google Drive API not enabled
- Network connectivity issues

**Resolution**:
- Verify service-account.json exists in backend directory
- Check JSON file is valid
- Ensure service account has necessary permissions
- Verify Google Drive API is enabled in Cloud Console
