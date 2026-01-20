# Real Implementation Guide

This guide explains how to use the real (non-mock) implementations for Google Drive integration, Excel file parsing, and AWS Textract text extraction.

## Overview

All mock/simulated data has been replaced with real implementations:

1. **Frontend**: Real Excel parsing using ExcelJS library
2. **Backend**: Real Google Drive API integration to fetch PDF files
3. **Backend**: Real text extraction using AWS Textract (with PyPDF2 fallback)

## Prerequisites

### Google Drive API Setup

1. **Create a Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google Drive API

2. **Create OAuth 2.0 Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop app" or "Web application"
   - Download the credentials JSON file

3. **Get OAuth Tokens**:
   - Use the OAuth 2.0 flow to get `access_token` and `refresh_token`
   - You can use the Google OAuth 2.0 Playground: https://developers.google.com/oauthplayground/
   - Select "Drive API v3" scope: `https://www.googleapis.com/auth/drive.readonly`

4. **Store Credentials in AWS Secrets Manager**:
   ```bash
   aws secretsmanager create-secret \
     --name processing-file-iso/google-drive-credentials \
     --secret-string '{
       "access_token": "ya29.a0AfH6SMB...",
       "refresh_token": "1//0gK5h2...",
       "client_id": "123456789-abc.apps.googleusercontent.com",
       "client_secret": "GOCSPX-..."
     }'
   ```

### AWS Textract Setup

AWS Textract is already integrated. Ensure your Lambda function has the necessary IAM permissions:

```json
{
  "Effect": "Allow",
  "Action": [
    "textract:DetectDocumentText",
    "textract:AnalyzeDocument"
  ],
  "Resource": "*"
}
```

## Frontend: Excel File Parsing

### How It Works

The frontend now uses **ExcelJS** library to parse Excel files and extract hole codes.

### Expected Excel Format

The Excel file should have hole codes in the **first column**, starting from **row 2** (row 1 is the header):

| Hole Code | (Other columns...) |
|-----------|-------------------|
| HOLE-1    | ...               |
| HOLE-2    | ...               |
| HOLE-3    | ...               |

### Usage

1. Upload an Excel file (.xlsx or .xls)
2. The file will be automatically parsed
3. Hole codes will be extracted from column A (starting row 2)
4. You'll see a message: "Selected: filename.xlsx | Target codes: X"

### Code Reference

See `frontend/src/Dashboard.jsx` lines 114-151 for the implementation.

## Backend: Google Drive Integration

### How It Works

The backend now:
1. Extracts folder ID from Google Drive URL
2. Uses Google Drive API v3 to list all PDF files in the folder
3. Downloads each file for processing
4. Falls back to simulation mode if credentials are not available

### Supported URL Formats

- `https://drive.google.com/drive/folders/FOLDER_ID`
- `https://drive.google.com/drive/folders/FOLDER_ID?usp=sharing`
- Direct folder ID: `FOLDER_ID`

### Fallback Mode

If Google Drive credentials are not configured or the API fails:
- The system automatically falls back to simulation mode
- Generates 100 mock PDF files for testing
- Logs warnings in CloudWatch

### Code Reference

See `backend/src/process_handler.py` lines 105-208 for the implementation.

## Backend: Text Extraction with Textract

### How It Works

The worker Lambda now:
1. Downloads PDF file from Google Drive
2. Attempts to extract text using AWS Textract
3. Falls back to PyPDF2 if Textract fails
4. Searches for hole codes in extracted text using regex pattern: `\b(?:HOLE|HC)-\d+\b`

### Text Extraction Methods

1. **AWS Textract** (Primary):
   - Most accurate, handles scanned documents
   - Supports images and complex PDFs
   - Cost: ~$1.50 per 1000 pages

2. **PyPDF2** (Fallback):
   - Free, faster
   - Only works with text-based PDFs
   - No cost

### Supported Hole Code Formats

- `HOLE-123`
- `HOLE-1`
- `HC-456`
- Case-insensitive

### Code Reference

See `backend/src/worker_handler.py` lines 65-177 for the implementation.

## Deployment

### 1. Deploy Infrastructure

```bash
cd infra
npm install
npm run build
cdk deploy
```

Note the output for WebSocket URL.

### 2. Configure Google Drive Credentials

Use the AWS Secrets Manager secret ARN from CDK output:

```bash
aws secretsmanager put-secret-value \
  --secret-id <SECRET_ARN> \
  --secret-string '{
    "access_token": "YOUR_ACCESS_TOKEN",
    "refresh_token": "YOUR_REFRESH_TOKEN",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET"
  }'
```

### 3. Configure Frontend

Create `.env` file in `frontend/`:

```env
VITE_WEBSOCKET_URL=wss://xxxxx.execute-api.region.amazonaws.com/prod
```

### 4. Run Frontend

```bash
cd frontend
npm install
npm run dev
```

## Testing

### Test with Real Data

1. **Prepare Google Drive Folder**:
   - Create a Google Drive folder
   - Upload PDF files containing hole codes
   - Share the folder (or ensure your OAuth token has access)
   - Copy the folder URL

2. **Prepare Excel File**:
   - Create Excel file with hole codes in first column
   - Save as .xlsx

3. **Run Processing**:
   - Open dashboard
   - Enter Google Drive folder URL
   - Upload Excel file
   - Click "Start Processing"
   - Watch real-time updates!

### Test with Simulation Mode

If you don't have Google Drive credentials configured:
- System automatically falls back to simulation
- Generates 100 mock files
- Useful for testing the WebSocket flow

## Cost Estimation

### With Real Implementation

**Per 1000 files:**
- Lambda execution: ~$0.50
- AWS Textract: ~$1.50 (assuming 1 page per PDF)
- Google Drive API: Free (within quota)
- SQS messages: ~$0.40
- DynamoDB: ~$0.10
- S3 storage: ~$0.01

**Total: ~$2.51 per 1000 files**

### Optimization Tips

1. **Use PyPDF2 when possible**: Set a flag to skip Textract for text-based PDFs
2. **Batch processing**: Already implemented (10 files per batch)
3. **Cache results**: Store processed files in DynamoDB to avoid reprocessing

## Troubleshooting

### Google Drive API Errors

**Error: "Invalid credentials"**
- Verify access_token is not expired
- Refresh the token using refresh_token
- Check OAuth scopes include Drive API read access

**Error: "Folder not found"**
- Verify folder ID is correct
- Ensure the OAuth account has access to the folder
- Check folder is not trashed

### Textract Errors

**Error: "Insufficient permissions"**
- Add Textract permissions to Lambda IAM role
- See Prerequisites section above

**Error: "Document too large"**
- Textract has a 5MB limit per document
- System will automatically fall back to PyPDF2

### Excel Parsing Errors

**Error: "Failed to parse Excel file"**
- Ensure file is valid .xlsx or .xls format
- Check hole codes are in first column
- Verify file is not corrupted

## Security Best Practices

1. **Never commit credentials**: Use AWS Secrets Manager
2. **Rotate tokens regularly**: Set up automatic token rotation
3. **Use least privilege**: IAM roles with minimal permissions
4. **Monitor API usage**: Set up CloudWatch alarms
5. **Validate input**: Already implemented in Lambda functions

## Monitoring

### CloudWatch Logs

**Dispatcher Lambda** (`/aws/lambda/ProcessingFileISOPipingStack-ScanDispatcher`):
- Google Drive API calls
- File list fetching
- SQS message sending

**Worker Lambda** (`/aws/lambda/ProcessingFileISOPipingStack-ScanWorker`):
- File downloads
- Textract calls
- Text extraction results

### Key Metrics to Watch

- Lambda duration (should be < 15 minutes)
- SQS queue depth
- Textract API calls (cost monitoring)
- Google Drive API quota (10,000 requests per 100 seconds)

## Next Steps

1. ✅ Real implementations complete
2. ✅ Security best practices implemented
3. 🔄 Set up Google Drive OAuth credentials
4. 🔄 Deploy to AWS
5. 🔄 Test with real data
6. 🔄 Monitor costs and performance
7. 🔄 Optimize based on usage patterns

## Support

For issues or questions:
1. Check CloudWatch logs for detailed error messages
2. Verify credentials in AWS Secrets Manager
3. Test Google Drive API access separately
4. Review this guide's troubleshooting section
