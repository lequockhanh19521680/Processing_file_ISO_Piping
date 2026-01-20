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

1. **Open the Dashboard**: Navigate to `http://localhost:3000`

2. **Configure WebSocket**: 
   - Enter the WebSocket URL from CDK output (e.g., `wss://xxxxx.execute-api.region.amazonaws.com/prod`)

3. **Enter Credentials**:
   - Google Drive Token (API token for accessing files)
   - Upload Excel file with target hole codes

4. **Start Processing**:
   - Click "Start Processing"
   - Watch real-time updates:
     - Connection status indicator
     - Progress bar showing percentage
     - Live results table populating row-by-row

5. **Download Results**:
   - When complete, click "Download Final Excel"

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
  token: 'google_drive_token',
  file_content: 'excel_data',
  target_hole_codes: ['HOLE-1', 'HOLE-2', ...]
}
```

## How It Works

1. **WebSocket Connection**: Frontend connects to API Gateway WebSocket API
2. **Start Processing**: User clicks button, sends `start_scan` message
3. **Lambda Processing**: 
   - Lambda extracts connectionId from event
   - Processes files in batches of 10
   - Sends progress updates after each batch
   - Sends immediate notifications for matches
4. **Real-time Updates**: 
   - Frontend receives messages via WebSocket
   - Updates progress bar
   - Adds rows to results table
5. **Completion**:
   - Lambda generates Excel report
   - Uploads to S3
   - Sends download URL via WebSocket
   - Frontend shows download button

## Key Benefits Over HTTP REST

- ✅ **No Timeouts**: WebSocket stays open for 15+ minutes
- ✅ **Real-time Feedback**: User sees first result in seconds, not minutes
- ✅ **Better UX**: Progress bar and live updates vs. spinner
- ✅ **Scalable**: Multiple users can process simultaneously
- ✅ **Event-Driven**: No polling required

## Lambda Timeout Handling

The Lambda function has a 15-minute timeout. For processing more than 6600 files:

1. **Option 1**: Optimize processing (parallel Textract calls)
2. **Option 2**: Implement Step Functions for pagination
   - Process 1000 files → Checkpoint → Continue
3. **Option 3**: Use SQS + multiple Lambdas for distributed processing

## Customization

### Backend (`backend/src/process_handler.py`):

- Update `extract_hole_codes_from_text()` for your hole code format
- Integrate with Google Drive API for file fetching
- Add Textract processing for PDF analysis
- Adjust batch size (currently 10 files)

### Frontend (`frontend/src/Dashboard.jsx`):

- Customize UI styling
- Add filters/search to results table
- Add export options
- Modify progress update frequency

### Infrastructure (`infra/lib/stack.ts`):

- Adjust Lambda timeout/memory
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
- S3: Pay per storage and requests
- Textract: Pay per page analyzed

**Estimated cost for 6600 files**: ~$5-10 per run (depends on PDF pages)

## Next Steps

1. ✅ Basic WebSocket implementation
2. ✅ Real-time dashboard
3. ✅ Progress tracking
4. 🔄 Google Drive API integration
5. 🔄 AWS Textract integration
6. 🔄 Step Functions for large batches
7. 🔄 Authentication/authorization
8. 🔄 Production deployment

## AWS Solutions Architect Professional Exam Relevance

This implementation demonstrates:

- ✅ **Event-Driven Architecture**: WebSocket for async communication
- ✅ **Serverless**: Lambda, API Gateway, S3
- ✅ **Scalability**: Multiple concurrent users
- ✅ **Real-time Processing**: Streaming updates
- ✅ **Cost Optimization**: Pay per use
- ✅ **Best Practices**: IAM roles, CloudWatch logging
- ✅ **User Experience**: Progress feedback vs. blocking requests

## License

MIT