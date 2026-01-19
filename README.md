# Processing_file_ISO_Piping

A Python application with a simple UI for processing Excel files containing hole codes (ma_ho) and searching for them in PDF files stored in Google Drive folders.

## Features

- **Excel File Processing**: Upload Excel files with ma_ho column containing hole codes
- **Google Drive Integration**: Recursively search PDF files in Google Drive folders and subfolders
- **PDF Text Extraction**: Extract and search text content from PDFs (with caching)
- **Results Export**: Generate a RESULT sheet in the Excel file with search results
- **User-Friendly UI**: Built with Streamlit for easy interaction

## Requirements

- Python 3.8 or higher
- Google Cloud Service Account with Drive API access
- Google Drive folder containing PDF files

## Installation

1. Clone the repository:
```bash
git clone https://github.com/lequockhanh19521680/Processing_file_ISO_Piping.git
cd Processing_file_ISO_Piping
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Set up Google Drive API:
   - Create a Google Cloud project
   - Enable Google Drive API
   - Create a Service Account
   - Download the service account JSON credentials file
   - Share your Google Drive folder with the service account email

## Usage

1. Start the application:
```bash
streamlit run app.py
```

2. The application will open in your web browser

3. Follow these steps in the UI:
   - **Upload Excel File**: Choose your .xlsx file with a 'ma_ho' column
   - **Upload Service Account JSON**: Upload your Google Cloud credentials
   - **Enter Drive Folder Link**: Paste the Google Drive folder URL
   - **Click OK**: Start processing

4. Wait for processing to complete

5. **Download Results**: Click the download button to get the updated Excel file with RESULT sheet

## Input Format

### Excel File Structure
The Excel file must contain:
- One sheet (can have any name)
- Column A with header `ma_ho`
- Subsequent rows with hole codes (e.g., ABCXYZ)

Example:
```
| ma_ho   |
|---------|
| ABC123  |
| XYZ456  |
| DEF789  |
```

### Google Drive Folder Link
Supported formats:
- `https://drive.google.com/drive/folders/FOLDER_ID`
- `FOLDER_ID` (just the ID)

## Output Format

The application creates a new sheet named **RESULT** with the following columns:

| Column       | Description                                    |
|--------------|------------------------------------------------|
| ma_ho        | The hole code from the input                   |
| found        | YES if found in any PDF, NO otherwise          |
| file_name    | Name of the PDF file where code was found      |
| file_id      | Google Drive file ID                           |
| folder_path  | Path to the folder containing the PDF          |

## Technical Architecture

### Modules

- **app.py**: Main Streamlit application with UI
- **excel_utils.py**: Excel file reading and writing functions
- **drive_utils.py**: Google Drive API integration
- **pdf_utils.py**: PDF text extraction and search with caching

### Key Functions

- `read_excel_codes()`: Read ma_ho values from Excel
- `list_drive_pdfs()`: Recursively list PDF files in Drive folder
- `extract_pdf_text()`: Extract text from PDF content with caching
- `search_codes()`: Search for codes in PDF text
- `write_result_sheet()`: Write results to Excel RESULT sheet

### Performance Features

- **PDF Text Caching**: Extracted text is cached to avoid re-downloading
- **Progress Tracking**: Real-time progress updates during processing
- **Streaming Downloads**: Efficient file downloads from Google Drive
- **Recursive Folder Scanning**: Handles nested folder structures

## Notes

- PDFs are assumed to be text-based (no OCR required)
- Large folders with many PDFs may take time to process
- The application handles errors gracefully with informative messages
- Service account must have read access to the Google Drive folder

## Troubleshooting

### "Column 'ma_ho' not found"
- Ensure your Excel file has a column header named exactly `ma_ho` (case-sensitive)

### "Invalid Google Drive folder link"
- Verify the folder link is correct
- Try using just the folder ID instead of the full URL

### "Error creating Drive service"
- Check that your service account JSON file is valid
- Ensure the Drive API is enabled in your Google Cloud project

### "Permission denied" or "File not found"
- Share the Google Drive folder with the service account email
- The email can be found in your service account JSON file

## License

MIT License

## Author

Le Quoc Khanh