# Processing File ISO Piping - Real-Time WebSocket Implementation

This project implements a real-time file processing system using AWS CDK, WebSocket API Gateway, Lambda, and React with Tailwind CSS.

## Architecture

- **Infrastructure**: AWS CDK (TypeScript) - WebSocket API Gateway, Lambda, S3
- **Backend**: Python Lambda function with streaming updates via WebSocket
- **Frontend**: React + Tailwind CSS + react-use-websocket

## Features

- ✅ Real-time WebSocket communication
- ✅ Live progress updates (every 10 files)
- ✅ Instant match notifications
- ✅ Real-time dashboard with progress bar
- ✅ Live results table
- ✅ Excel report generation and download
- ✅ Connection status indicator

## Project Structure

```
.
├── infra/                  # AWS CDK Infrastructure
│   ├── bin/
│   │   └── app.ts         # CDK App entry point
│   ├── lib/
│   │   └── stack.ts       # Main CDK Stack with WebSocket API
│   ├── cdk.json
│   ├── tsconfig.json
│   └── package.json
│
├── backend/               # Lambda Functions
│   ├── src/
│   │   └── process_handler.py  # Main processing Lambda
│   └── layer/
│       └── requirements.txt    # Python dependencies
│
└── frontend/              # React Application
    ├── src/
    │   ├── Dashboard.jsx  # Main dashboard component
    │   ├── main.jsx       # React entry point
    │   └── index.css      # Tailwind CSS
    ├── index.html
    ├── vite.config.js
    └── package.json
```

## Setup Instructions

### Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- AWS CLI configured with credentials
- AWS CDK CLI (`npm install -g aws-cdk`)

### 1. Deploy Infrastructure

```bash
cd infra

# Install dependencies
npm install

# Bootstrap CDK (first time only)
cdk bootstrap

# Build TypeScript
npm run build

# Deploy stack
cdk deploy

# Note the outputs:
# - WebSocketURL: wss://xxxxx.execute-api.region.amazonaws.com/prod
# - ResultsBucketName: processing-bucket-xxxxx
```

### 2. Build Lambda Layer (Optional)

If you need to update Python dependencies:

```bash
cd backend/layer

# Install dependencies to python/ directory
pip install -r requirements.txt -t python/

# Create layer zip (CDK will handle this automatically)
```

### 3. Run Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

The frontend will be available at `http://localhost:3000`

## Usage

1. **Configure Secrets and Deploy Infrastructure**:
   - See [SECURITY_DEPLOYMENT.md](./SECURITY_DEPLOYMENT.md) for detailed instructions on:
     - Setting up AWS Secrets Manager for Google Drive API credentials
     - Configuring AWS Amplify for automatic frontend deployment
     - Managing environment variables securely
   - Quick start: Deploy CDK stack, then set secrets in AWS Secrets Manager

2. **Local Development**:
   - Frontend: Create `.env` file in `frontend/` directory with `VITE_WEBSOCKET_URL` from CDK output
   - Backend: Secrets are automatically retrieved from AWS Secrets Manager by Lambda functions

3. **Open the Dashboard**: 
   - Production: Access via Amplify URL (see CDK output: `AmplifyAppUrl`)
   - Development: Navigate to `http://localhost:3000` (after running `npm run dev`)

4. **Enter Google Drive Link**:
   - Paste the Google Drive folder link containing files to process (e.g., `https://drive.google.com/drive/folders/xxxxx`)
   - Upload Excel file with target hole codes (optional)

5. **Start Processing**:
   - Click "Start Processing"
   - Watch real-time updates:
     - Connection status indicator
     - Progress bar showing percentage
     - Live results table populating row-by-row

6. **Download Results**:
   - When complete, click "Download Final Excel"

**Note**: All sensitive credentials are now securely stored in AWS Secrets Manager. See [SECURITY_DEPLOYMENT.md](./SECURITY_DEPLOYMENT.md) for setup instructions.

## WebSocket Message Types

### From Backend to Frontend:

```javascript
// 1. Started
{ type: 'STARTED', message: 'Processing started' }

// 2. Progress Update
{ type: 'PROGRESS', value: 45, processed: 450, total: 1000 }

// 3. Match Found
{ 
  type: 'MATCH_FOUND', 
  data: {
    hole_code: 'HOLE-123',
    file_name: 'drawing_456.pdf',
    status: '1 Code',
    pdf_link: 'https://...'
  }
}

// 4. Complete
{ 
  type: 'COMPLETE', 
  download_url: 'https://s3.amazonaws.com/...',
  total_matches: 42,
  message: 'Processing completed'
}

// 5. Error
{ type: 'ERROR', message: 'Error description' }
```

### From Frontend to Backend:

```javascript
{
  action: 'start_scan',
  drive_link: 'https://drive.google.com/drive/folders/xxxxx',
  file_content: 'excel_data',
  target_hole_codes: ['HOLE-1', 'HOLE-2', ...]
}
```

**Note**: Google Drive API credentials are now configured in backend environment variables.

## How It Works

**All mock implementations have been replaced with real integrations:**

1. **WebSocket Connection**: Frontend connects to API Gateway WebSocket API
2. **Start Processing**: User uploads Excel file (parsed with ExcelJS) and enters Google Drive link
3. **Dispatcher Phase** (ScanDispatcher Lambda):
   - Extracts folder ID from Google Drive URL
   - Authenticates with Google Drive API using credentials from Secrets Manager
   - Fetches real PDF files from the specified folder using Google Drive API v3
   - Falls back to simulation mode if credentials unavailable
   - Generates unique session_id
   - Stores session metadata in DynamoDB
   - Batches file metadata and sends to SQS queue
   - Sends STARTED message via WebSocket
   - Exits immediately (no waiting)
4. **Worker Phase** (ScanWorker Lambda, triggered by SQS):
   - Downloads PDF files from Google Drive
   - Extracts text using AWS Textract (primary) or PyPDF2 (fallback)
   - Searches for hole codes in extracted text
   - Processes files in batches of 10 from SQS
   - Writes results to DynamoDB
   - Atomically updates processed_count
   - Sends PROGRESS updates after each batch
   - Sends MATCH_FOUND for immediate notifications
5. **Completion Phase**:
   - Worker detects processed_count == total_files
   - Queries all results from DynamoDB
   - Generates Excel report
   - Uploads to S3
   - Sends COMPLETE with download URL via WebSocket
   - Frontend shows download button

**Real Integrations:**
- ✅ Google Drive API v3 for file fetching
- ✅ ExcelJS for parsing Excel files (frontend)
- ✅ AWS Textract for text extraction from PDFs
- ✅ PyPDF2 as fallback for text-based PDFs
- ✅ Automatic fallback to simulation mode for testing

## Key Benefits Over HTTP REST

- ✅ **No Timeouts**: Event-driven architecture eliminates Lambda timeout issues
- ✅ **Unlimited Scale**: Can process 6,600+ files without timeout
- ✅ **Real-time Feedback**: User sees first result in seconds, not minutes
- ✅ **Better UX**: Progress bar and live updates vs. spinner
- ✅ **Scalable**: Multiple users can process simultaneously
- ✅ **Event-Driven**: SQS decouples dispatcher from workers
- ✅ **Fault Tolerant**: SQS retries failed messages automatically

## Architecture Advantages

The system now uses **async event-driven architecture** with SQS and DynamoDB:

1. **No Lambda Timeouts**: Dispatcher exits in seconds, workers process in parallel
2. **Distributed Processing**: Multiple workers process files simultaneously
3. **State Management**: DynamoDB tracks progress with atomic counters
4. **Auto Scaling**: Lambda scales automatically based on SQS queue depth
5. **Cost Effective**: Pay only for actual processing time (~$0.07 per 6,600 files)

## Customization

### Backend (`backend/src/process_handler.py` - Dispatcher):

- Integrate with Google Drive API for file fetching
- Adjust SQS batch size for different workloads
- Modify session metadata structure

### Backend (`backend/src/worker_handler.py` - Worker):

- Update `extract_hole_codes_from_text()` for your hole code format
- Add Textract processing for PDF analysis
- Customize result schema in DynamoDB
- Adjust worker batch size (currently 10 files)

### Frontend (`frontend/src/Dashboard.jsx`):

- Customize UI styling
- Add filters/search to results table
- Add export options
- Modify progress update frequency

### Infrastructure (`infra/lib/stack.ts`):

- Adjust Lambda timeout/memory for workers
- Configure SQS visibility timeout and batch size
- Set up DynamoDB table attributes
- Configure S3 bucket policies
- Add CloudWatch alarms
- Set up custom domain for WebSocket API

## Security Considerations

- ✅ **Secrets Management**: Google Drive API credentials stored in AWS Secrets Manager
- ✅ **Parameter Store**: WebSocket URL stored in AWS Systems Manager Parameter Store
- ✅ **No Hardcoded Credentials**: All sensitive data retrieved at runtime
- ✅ **IAM Roles**: Lambda functions use least-privilege IAM roles
- ✅ **WebSocket Authentication**: Connections authenticated via API Gateway
- ✅ **S3 Security**: CORS configured, presigned URLs expire after 1 hour
- ✅ **Automatic Deployment**: AWS Amplify with environment variable injection
- ⚠️ **Production TODO**: Add authentication/authorization (Cognito, API keys)
- ⚠️ **Production TODO**: Validate input data thoroughly
- ⚠️ **Production TODO**: Implement rate limiting (API Gateway throttling)
- ⚠️ **Production TODO**: Enable AWS WAF for DDoS protection
- ⚠️ **Production TODO**: Restrict CORS origins to production domain only

**For detailed security setup instructions, see [SECURITY_DEPLOYMENT.md](./SECURITY_DEPLOYMENT.md)**

## Troubleshooting

### WebSocket won't connect
- Verify WebSocket URL format: `wss://` not `https://`
- Check API Gateway deployment
- Review CloudWatch logs

### No progress updates
- Check Lambda CloudWatch logs
- Verify connectionId is being passed
- Check API Gateway Management API permissions

### Lambda timeout
- Reduce number of files processed
- Implement pagination with Step Functions
- Optimize processing logic

## Cost Optimization

- Lambda: Pay per request and duration
- API Gateway: Pay per connection minute and messages
- SQS: Pay per message ($0.40/M requests)
- DynamoDB: Pay per request (on-demand billing)
- S3: Pay per storage and requests

**Estimated cost for 6600 files**: 
- Without Textract: ~$0.07 per run
- With Textract: ~$10.00 per run (includes $9.90 for OCR)

## Next Steps

1. ✅ Basic WebSocket implementation
2. ✅ Real-time dashboard
3. ✅ Progress tracking
4. ✅ Event-driven architecture with SQS + DynamoDB
5. ✅ Scalable worker processing (no timeouts)
6. ✅ **Secrets Management with AWS Secrets Manager**
7. ✅ **AWS Amplify deployment configuration**
8. ✅ **Secure credential handling (no hardcoded secrets)**
9. ✅ **Google Drive API integration (real, not mock)**
10. ✅ **AWS Textract integration (real text extraction)**
11. ✅ **ExcelJS integration (real Excel parsing)**
12. 🔄 Authentication/authorization (Cognito, API keys)
13. 🔄 Production deployment with custom domain

**For detailed setup instructions, see [REAL_IMPLEMENTATION_GUIDE.md](./REAL_IMPLEMENTATION_GUIDE.md)**

## AWS Solutions Architect Professional Exam Relevance

This implementation demonstrates:

- ✅ **Event-Driven Architecture**: WebSocket for async communication, SQS for decoupling
- ✅ **Serverless**: Lambda, API Gateway, S3, DynamoDB, SQS, Amplify
- ✅ **Security**: Secrets Manager, Parameter Store, IAM roles, least-privilege access
- ✅ **Scalability**: Multiple concurrent users, unlimited file processing
- ✅ **Real-time Processing**: Streaming updates via WebSocket
- ✅ **State Management**: DynamoDB with atomic counters
- ✅ **Cost Optimization**: Pay per use, no idle resources
- ✅ **Fault Tolerance**: SQS retries, distributed workers
- ✅ **Best Practices**: No hardcoded credentials, IAM roles, CloudWatch logging, loose coupling
- ✅ **CI/CD**: Automated deployment with AWS Amplify
- ✅ **User Experience**: Progress feedback vs. blocking requests

## License

MIT