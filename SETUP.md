# Setup Guide

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Google Drive API

#### Create a Service Account:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Drive API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click "Enable"

4. Create Service Account credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Fill in the service account details
   - Click "Done"

5. Create a key for the service account:
   - Click on the created service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose "JSON" format
   - Download the file (this is your credentials file)

#### Share Your Google Drive Folder:

1. Open the Google Drive folder containing your PDFs
2. Click "Share"
3. Add the service account email (found in your JSON credentials file, looks like: `xyz@project-id.iam.gserviceaccount.com`)
4. Give it "Viewer" or "Reader" access
5. Click "Share"

### 3. Prepare Your Excel File

Create an Excel file (.xlsx) with:
- At least one sheet
- Column header `ma_ho` in the first row
- Hole codes in subsequent rows under the `ma_ho` column

Example:
```
| ma_ho      |
|------------|
| HOLE001    |
| HOLE002    |
| HOLE003    |
```

### 4. Run the Application

```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`

### 5. Use the Application

1. Upload your Excel file
2. Upload your service account JSON credentials
3. Paste your Google Drive folder link
4. Click "OK - Start Processing"
5. Wait for processing to complete
6. Download the updated Excel file with results

## Folder Structure

```
Processing_file_ISO_Piping/
├── app.py              # Main Streamlit application
├── excel_utils.py      # Excel processing utilities
├── drive_utils.py      # Google Drive integration
├── pdf_utils.py        # PDF text extraction
├── requirements.txt    # Python dependencies
├── README.md          # Documentation
├── SETUP.md           # This file
└── .gitignore         # Git ignore rules
```

## Environment Variables (Optional)

You can set the following environment variables for default values:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
```

## Common Issues

### Import Errors
If you get import errors, make sure all dependencies are installed:
```bash
pip install -r requirements.txt --upgrade
```

### Streamlit Port Already in Use
If port 8501 is already in use, run on a different port:
```bash
streamlit run app.py --server.port 8502
```

### Large PDF Processing
For very large PDFs or folders with many files:
- Processing may take several minutes
- The cache will help with repeated searches
- Consider breaking up the search into smaller batches

## Development

To contribute or modify the code:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Testing Locally

Create a test Excel file with a few sample codes and a small Google Drive folder with test PDFs to verify the application works correctly before processing large datasets.
