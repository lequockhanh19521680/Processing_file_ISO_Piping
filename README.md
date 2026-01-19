# ISO Piping File Processor

A full-stack web application that automates the process of searching for piping identifiers (ma_ho values) within PDF documents stored in Google Drive folders.

## 🎯 Purpose

This application helps engineers and quality control teams verify that specific piping identifiers appear in PDF documentation. It automates what would otherwise be a manual, time-consuming process of searching through hundreds of PDF files across multiple folders.

## ✨ Features

- **Excel Upload**: Upload a spreadsheet with ma_ho identifiers to search for
- **Google Drive Integration**: Recursively scan PDF files in Drive folders and subfolders
- **PDF Text Extraction**: Extract and cache text from PDFs for efficient searching
- **Automated Matching**: Case-insensitive search for each ma_ho value
- **Result Export**: Download an Excel file with detailed results showing which files contain each identifier

## 🏗️ Architecture

- **Frontend**: React 18 with Vite (modern, fast development)
- **Backend**: Python FastAPI (high-performance async web framework)
- **PDF Processing**: PyPDF2 for text extraction
- **Excel Processing**: openpyxl for reading and writing
- **Google Drive**: Service account authentication for API access

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.9 or higher** - [Download Python](https://www.python.org/downloads/)
- **Node.js 18 or higher** - [Download Node.js](https://nodejs.org/)
- **npm** (comes with Node.js)
- **Google Cloud Service Account** with Drive API access (see setup below)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/lequockhanh19521680/Processing_file_ISO_Piping.git
cd Processing_file_ISO_Piping
```

### 2. Set Up Google Service Account

#### Create Service Account:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google Drive API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click "Enable"
4. Create a service account:
   - Navigate to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Fill in the details and create
5. Create and download JSON key:
   - Click on the created service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose "JSON" format
   - Save the downloaded file

#### Configure Service Account:
1. Rename the downloaded file to `service-account.json`
2. Move it to the `backend/` directory:
   ```bash
   mv ~/Downloads/your-service-account-*.json backend/service-account.json
   ```
3. **Important**: Share your Google Drive folder with the service account email:
   - Open the service account JSON file
   - Copy the `client_email` value (looks like `xxx@xxx.iam.gserviceaccount.com`)
   - In Google Drive, right-click your folder > Share
   - Paste the service account email and give "Viewer" access

### 3. Set Up Backend

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify service account file exists
ls service-account.json

# Run the backend server
python main.py
```

The backend will start on **http://localhost:8000**

You should see:
```
Starting ISO Piping File Processor API...
API will be available at: http://localhost:8000
API documentation at: http://localhost:8000/docs
```

### 4. Set Up Frontend

Open a **new terminal window** (keep backend running):

```bash
cd frontend

# Install dependencies
npm install

# Run the development server
npm run dev
```

The frontend will start on **http://localhost:3000**

You should see:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:3000/
```

### 5. Use the Application

1. Open your browser and navigate to **http://localhost:3000**
2. Upload an Excel file (.xlsx) with:
   - One sheet
   - Column A header named "ma_ho"
   - ma_ho values in rows below the header
3. Paste your Google Drive folder URL (must be shared with service account)
4. Click "OK - Start Processing"
5. Wait for processing (progress shown in browser)
6. Download the processed Excel file with a new "RESULT" sheet

## 📊 Input/Output Format

### Input Excel File

| ma_ho |
|-------|
| ISO-P-001 |
| VALVE-A123 |
| PIPE-2024 |

### Output Excel File

Original sheet + new **RESULT** sheet:

| ma_ho | found | file_name | file_id | folder_path |
|-------|-------|-----------|---------|-------------|
| ISO-P-001 | YES | Drawing_Rev2.pdf | 1aB2cD3e... | /Engineering/Piping |
| VALVE-A123 | NO | | | |
| PIPE-2024 | YES | Spec_Sheet.pdf | 4gH5iJ6k... | /Engineering/Piping/2024 |

## 🛠️ Development

### Project Structure

```
Processing_file_ISO_Piping/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── drive_service.py        # Google Drive integration
│   ├── pdf_utils.py            # PDF text extraction
│   ├── excel_utils.py          # Excel file processing
│   ├── requirements.txt        # Python dependencies
│   └── service-account.json    # Google credentials (not in repo)
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Main React component
│   │   ├── App.css             # Component styles
│   │   ├── main.jsx            # React entry point
│   │   └── index.css           # Global styles
│   ├── index.html              # HTML template
│   ├── package.json            # Node dependencies
│   └── vite.config.js          # Vite configuration
├── ai-context/
│   ├── PROJECT_CONTEXT.md      # Project overview for AI
│   ├── ARCHITECTURE.md         # Technical architecture
│   ├── DOMAIN_GLOSSARY.md      # Domain terminology
│   └── PROMPT_GUIDE.md         # AI prompting guide
├── .gitignore
└── README.md
```

### Backend API Endpoints

- **GET /** - Health check
- **POST /process** - Process Excel file
  - Form data: `file` (Excel), `drive_link` (string)
  - Returns: Processed Excel file
- **GET /docs** - Interactive API documentation (Swagger UI)

### Running Tests

Currently, the project does not have automated tests. To add tests:

**Backend:**
```bash
cd backend
pip install pytest pytest-cov
pytest tests/ -v
```

**Frontend:**
```bash
cd frontend
npm test
```

## 🔒 Security Notes

- **Never commit** `service-account.json` to version control
- The `.gitignore` file excludes all JSON credentials
- In production, use environment variables or secret management services
- Restrict CORS to specific frontend domains in production
- Ensure service account has minimal required permissions (read-only for Drive)

## 🐛 Troubleshooting

### "Service account file not found"
- Ensure `service-account.json` is in the `backend/` directory
- Verify the file is valid JSON
- Check file permissions

### "Cannot connect to server"
- Verify backend is running on port 8000
- Check that frontend is configured to use `http://localhost:8000`
- Ensure no firewall blocking the connection

### "User does not have sufficient permissions"
- Verify the Google Drive folder is shared with the service account email
- Check that the service account email has "Viewer" or "Reader" access
- Ensure Google Drive API is enabled in your Google Cloud project

### "No text extracted from PDF"
- The PDF might be image-based (scanned) - requires OCR (not currently supported)
- Try opening the PDF and checking if text can be selected/copied
- Some PDFs have text but in a format PyPDF2 cannot extract

### Processing takes too long
- Check the number of PDF files in the folder
- Typical processing: 1-2 seconds per PDF file
- Consider folders with fewer than 500 PDFs for optimal performance

## 🚀 Production Deployment

For production deployment, consider:

1. **Build Frontend:**
   ```bash
   cd frontend
   npm run build
   # Serve dist/ folder with nginx or similar
   ```

2. **Run Backend with Production Server:**
   ```bash
   cd backend
   uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

3. **Environment Variables:**
   - Store service account credentials in AWS Secrets Manager, Azure Key Vault, etc.
   - Configure CORS to allow only your production frontend URL
   - Set up HTTPS/SSL certificates

4. **Containerization:**
   - Consider using Docker for easier deployment
   - Create separate containers for frontend and backend
   - Use docker-compose for local development

5. **Monitoring:**
   - Add logging and error tracking (Sentry, CloudWatch, etc.)
   - Monitor API response times and error rates
   - Set up alerts for service account expiration

## 📚 AI Context Files

This project includes comprehensive AI context files in the `ai-context/` directory. These files enable future AI assistants to quickly understand the project without re-explaining requirements:

- **PROJECT_CONTEXT.md** - High-level overview, purpose, and data flow
- **ARCHITECTURE.md** - Technical implementation details and design decisions
- **DOMAIN_GLOSSARY.md** - Definitions of domain-specific terms (ma_ho, etc.)
- **PROMPT_GUIDE.md** - How to effectively prompt AI for this project

When working with AI on this project, reference these files for context.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is open source and available for use.

## 🙋 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Review the troubleshooting section above
- Check the AI context files for detailed documentation

## 🔮 Future Enhancements

Potential improvements (see PROMPT_GUIDE.md for detailed prompts):
- [ ] Add OCR support for scanned PDFs
- [ ] Real-time progress updates via WebSocket
- [ ] Support for multiple Google Drive folders
- [ ] Persistent caching with database
- [ ] Parallel PDF processing for better performance
- [ ] User authentication and session management
- [ ] Export results to multiple formats (CSV, JSON)
- [ ] Advanced search options (regex, fuzzy matching)
- [ ] Web-based PDF viewer for found results
- [ ] Email notifications when processing completes

---

Made with ❤️ for ISO Piping Engineers