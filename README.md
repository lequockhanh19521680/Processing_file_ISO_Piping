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

1. **Configure Environment Variables**:
   - Frontend: Create `.env` file in `frontend/` directory with `VITE_WEBSOCKET_URL`
   - Backend: Set `GOOGLE_DRIVE_API_KEY` and `GOOGLE_DRIVE_API_TOKEN` in Lambda environment variables

2. **Open the Dashboard**: Navigate to `http://localhost:3000`

3. **Enter Google Drive Link**:
   - Paste the Google Drive folder link containing files to process (e.g., `https://drive.google.com/drive/folders/xxxxx`)
   - Upload Excel file with target hole codes (optional)

4. **Start Processing**:
   - Click "Start Processing"
   - Watch real-time updates:
     - Connection status indicator
     - Progress bar showing percentage
     - Live results table populating row-by-row

5. **Download Results**:
   - When complete, click "Download Final Excel"

**Note**: WebSocket URL and Google Drive API credentials are now configured via environment variables, not in the UI.

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

1. **WebSocket Connection**: Frontend connects to API Gateway WebSocket API
2. **Start Processing**: User clicks button, sends `start_scan` message
3. **Dispatcher Phase** (ScanDispatcher Lambda):
   - Generates unique session_id
   - Stores session metadata in DynamoDB
   - Batches file metadata and sends to SQS queue
   - Sends STARTED message via WebSocket
   - Exits immediately (no waiting)
4. **Worker Phase** (ScanWorker Lambda, triggered by SQS):
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

- ✅ WebSocket connections are authenticated via API Gateway
- ✅ Lambda has IAM role with minimal permissions
- ✅ S3 bucket has CORS configured
- ✅ Presigned URLs expire after 1 hour
- ⚠️ Add authentication/authorization for production
- ⚠️ Validate input data thoroughly
- ⚠️ Implement rate limiting

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
6. 🔄 Google Drive API integration
7. 🔄 AWS Textract integration
8. 🔄 Authentication/authorization
9. 🔄 Production deployment

## AWS Solutions Architect Professional Exam Relevance

This implementation demonstrates:

- ✅ **Event-Driven Architecture**: WebSocket for async communication, SQS for decoupling
- ✅ **Serverless**: Lambda, API Gateway, S3, DynamoDB, SQS
- ✅ **Scalability**: Multiple concurrent users, unlimited file processing
- ✅ **Real-time Processing**: Streaming updates via WebSocket
- ✅ **State Management**: DynamoDB with atomic counters
- ✅ **Cost Optimization**: Pay per use, no idle resources
- ✅ **Fault Tolerance**: SQS retries, distributed workers
- ✅ **Best Practices**: IAM roles, CloudWatch logging, loose coupling
- ✅ **User Experience**: Progress feedback vs. blocking requests

## License

MIT