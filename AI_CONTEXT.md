# AI Context - Processing File ISO Piping

## System Overview
An **Async Event-Driven File Processing System** that uses WebSocket for real-time user feedback while processing thousands of files without timeouts. Built on AWS serverless architecture with SQS for distributed processing and DynamoDB for state management.

## Tech Stack

### Infrastructure (CDK - TypeScript)
- **AWS CDK**: Infrastructure as Code
- **API Gateway WebSocket**: Real-time bidirectional communication
- **AWS Lambda**: Serverless compute (Python 3.11)
- **Amazon SQS**: Message queue for file processing tasks
- **Amazon DynamoDB**: NoSQL database for session state and results
- **Amazon S3**: Object storage for Excel reports

### Backend (Python 3.11)
- **boto3**: AWS SDK for Python
- **openpyxl**: Excel file generation
- Standard libraries: json, os, uuid, re, datetime

### Frontend (React)
- **React**: UI framework
- **Tailwind CSS**: Styling
- **react-use-websocket**: WebSocket client library
- **Vite**: Build tool

## Architecture Flow

### High-Level Data Flow
```
User Browser (React)
    ↓ WebSocket Connection
API Gateway WebSocket
    ↓ start_scan event
ScanDispatcher Lambda (process_handler.py)
    ↓ Batch send messages
Amazon SQS Queue
    ↓ Triggers (batch of 10)
ScanWorker Lambda (worker_handler.py)
    ↓ Writes results
DynamoDB + WebSocket Updates
    ↓ On completion
Generate Excel → S3 → Download URL
    ↓ WebSocket notification
User Browser (Download Button)
```

### Detailed Event Flow

#### 1. Session Initialization (Dispatcher)
```
1. User clicks "Start Processing" in frontend
2. Frontend sends WebSocket message:
   {
     action: "start_scan",
     token: "google_drive_token",
     file_content: "...",
     target_hole_codes: ["HOLE-1", "HOLE-2", ...]
   }
3. ScanDispatcher Lambda receives message via WebSocket route
4. Generates unique session_id (UUID)
5. Stores session metadata in DynamoDB:
   - PK: session_id
   - SK: "meta"
   - Attributes: connection_id, total_files, processed_count=0, target_hole_codes
6. Batches file metadata (10 per batch) and sends to SQS queue
7. Sends STARTED message to user via WebSocket
8. Lambda exits (does not wait for processing)
```

#### 2. File Processing (Worker)
```
1. ScanWorker Lambda triggered by SQS (batch of 10 messages)
2. For each message:
   a. Extract file metadata (session_id, file_name, content, etc.)
   b. Process file (extract text, match hole codes)
   c. Write result to DynamoDB:
      - PK: session_id
      - SK: file_name
      - Attributes: status, found_codes, pdf_link, timestamp
   d. Atomic increment: processed_count in meta item
   e. Retrieve meta item to get connection_id, total_files, processed_count
   f. Send PROGRESS update via WebSocket
   g. If match found, send MATCH_FOUND update
3. Check if processed_count == total_files
4. If complete:
   a. Query all results from DynamoDB for session_id
   b. Generate Excel report with openpyxl
   c. Upload to S3
   d. Generate presigned URL (1-hour expiry)
   e. Send COMPLETE message with download URL
```

## DynamoDB Table Schema

**Table Name**: `ProcessResultsTable`

**Keys**:
- **Partition Key (PK)**: `session_id` (String) - Unique session identifier
- **Sort Key (SK)**: `file_name` (String) - File name or "meta" for session metadata

**Item Types**:

1. **Session Metadata Item** (SK = "meta")
```json
{
  "session_id": "uuid-string",
  "file_name": "meta",
  "connection_id": "websocket-connection-id",
  "total_files": 6600,
  "processed_count": 0,
  "target_hole_codes": ["HOLE-1", "HOLE-2", ...],
  "timestamp": "2026-01-20T03:00:00.000Z"
}
```

2. **File Result Item** (SK = actual file name)
```json
{
  "session_id": "uuid-string",
  "file_name": "drawing_123.pdf",
  "status": "2 Codes",
  "found_codes": ["HOLE-5", "HOLE-7"],
  "pdf_link": "https://drive.google.com/file/...",
  "timestamp": "2026-01-20T03:01:15.000Z"
}
```

**Query Pattern**:
- Query all items by session_id: `KeyConditionExpression='session_id = :sid'`
- Filter meta: `file_name != 'meta'`
- Atomic counter update: `UpdateExpression='SET processed_count = processed_count + :inc'`

## SQS Message Schema

**Queue**: `ProcessingQueue`
**Visibility Timeout**: 180 seconds (6x Lambda timeout)
**Batch Size**: 10 messages per Lambda invocation

**Message Body**:
```json
{
  "session_id": "uuid-string",
  "file_name": "drawing_456.pdf",
  "file_content": "Sample text content or S3 key",
  "pdf_link": "https://drive.google.com/file/...",
  "target_hole_codes": ["HOLE-1", "HOLE-2", ...]
}
```

## WebSocket Message Protocol

### Client → Server (Frontend to Dispatcher)
```json
{
  "action": "start_scan",
  "token": "google_drive_api_token",
  "file_content": "excel_data or file list",
  "target_hole_codes": ["HOLE-1", "HOLE-2", "HOLE-3"]
}
```

### Server → Client (Backend to Frontend)

**1. STARTED**
```json
{
  "type": "STARTED",
  "message": "Processing started",
  "session_id": "uuid-string",
  "timestamp": "2026-01-20T03:00:00.000Z"
}
```

**2. PROGRESS**
```json
{
  "type": "PROGRESS",
  "value": 45,
  "processed": 2970,
  "total": 6600
}
```

**3. MATCH_FOUND**
```json
{
  "type": "MATCH_FOUND",
  "data": {
    "hole_code": "HOLE-123",
    "file_name": "drawing_456.pdf",
    "status": "1 Code",
    "pdf_link": "https://drive.google.com/file/..."
  }
}
```

**4. COMPLETE**
```json
{
  "type": "COMPLETE",
  "download_url": "https://s3.amazonaws.com/.../results.xlsx",
  "total_matches": 142,
  "total_processed": 6600,
  "message": "Processing completed successfully"
}
```

**5. ERROR**
```json
{
  "type": "ERROR",
  "message": "Error description"
}
```

## Lambda Functions

### 1. ScanDispatcher (process_handler.py)
**Role**: WebSocket event handler, session initializer, SQS dispatcher
**Timeout**: 60 seconds
**Memory**: 512 MB
**Permissions**:
- `sqs:SendMessage` → ProcessingQueue
- `dynamodb:PutItem` → ProcessResultsTable
- `execute-api:ManageConnections` → WebSocket API

**Key Logic**:
- Receives start_scan WebSocket event
- Generates session_id
- Stores session metadata in DynamoDB
- Batches files and sends to SQS
- Sends STARTED message
- Exits immediately

### 2. ScanWorker (worker_handler.py)
**Role**: File processor, DynamoDB writer, progress reporter
**Timeout**: 30 seconds
**Memory**: 1024 MB
**Trigger**: SQS event source (batch size: 10)
**Permissions**:
- `dynamodb:UpdateItem` → ProcessResultsTable
- `dynamodb:Query` → ProcessResultsTable
- `s3:PutObject` → ResultsBucket
- `execute-api:ManageConnections` → WebSocket API

**Key Logic**:
- Reads batch of 10 messages from SQS
- Processes each file (extract text, match codes)
- Writes result to DynamoDB
- Atomically increments processed_count
- Sends PROGRESS and MATCH_FOUND updates
- On completion: generates Excel, uploads to S3, sends COMPLETE

### 3. ConnectHandler, DisconnectHandler, DefaultHandler
**Role**: WebSocket lifecycle management
**Timeout**: 30 seconds
**Logic**: Simple acknowledgment handlers (inline Lambda code)

## Scaling Characteristics

### Concurrency
- **WebSocket Connections**: 100,000+ concurrent (API Gateway limit)
- **SQS Queue**: Unlimited throughput
- **Lambda Concurrency**: 1,000 concurrent executions per region (default)
- **DynamoDB**: On-demand billing scales automatically

### Processing Capacity
- **Files per Run**: Unlimited (no Lambda timeout constraint)
- **Example**: 6,600 files
  - SQS messages: 6,600
  - Worker invocations: ~660 (10 messages each)
  - Processing time: ~5-10 minutes (parallel execution)
  - Cost: ~$0.50 (excluding Textract)

## Cost Breakdown (Example: 6,600 files)

| Service | Usage | Estimated Cost |
|---------|-------|----------------|
| Lambda (Dispatcher) | 1 invocation × 512 MB × 5s | ~$0.0001 |
| Lambda (Worker) | 660 invocations × 1024 MB × 5s | ~$0.05 |
| SQS | 6,600 messages × $0.40/M requests | ~$0.003 |
| DynamoDB | 6,600 writes + 6,600 reads | ~$0.02 |
| API Gateway WebSocket | 10 min × $0.25/M min | ~$0.003 |
| S3 Storage | 1 MB × $0.023/GB | ~$0.0001 |
| **Total per run** | | **~$0.07** |

*Note: Textract costs excluded (~$0.0015/page = $9.90 for 6,600 pages)*

## Key Design Decisions

### Why SQS?
- **Decouples** dispatcher from workers
- **Prevents timeout**: Dispatcher exits immediately
- **Automatic retry**: Failed messages return to queue
- **Scalability**: Multiple workers process in parallel

### Why DynamoDB?
- **Atomic counters**: processed_count updates without race conditions
- **Query by session**: Efficient retrieval of all results
- **Pay-per-request**: No provisioning required
- **Low latency**: Sub-10ms read/write

### Why Not Step Functions?
- **Overhead**: Step Functions adds complexity for simple fan-out pattern
- **Cost**: SQS is cheaper for high-volume message passing
- **Simplicity**: SQS + Lambda is more straightforward

## Security Considerations

### Current Implementation
- ✅ WebSocket uses TLS (wss://)
- ✅ IAM roles with least privilege
- ✅ S3 presigned URLs with 1-hour expiry
- ✅ No sensitive data in logs

### Production TODO
- ⚠️ Add API Gateway authorizer (Lambda or Cognito)
- ⚠️ Validate and sanitize all input
- ⚠️ Encrypt DynamoDB table at rest
- ⚠️ Add VPC for Lambda (if needed)
- ⚠️ Implement rate limiting

## Monitoring & Debugging

### CloudWatch Logs
- `/aws/lambda/ScanDispatcher`: Dispatcher logs
- `/aws/lambda/ScanWorker`: Worker logs
- `/aws/apigateway/WebSocketApi`: API Gateway logs

### Key Metrics
- `ScanWorker` invocations (should be ~total_files/10)
- `ProcessingQueue` message count (should decrease over time)
- DynamoDB `processed_count` (should equal total_files at completion)
- Lambda errors (should be 0)

### Common Issues
1. **Worker not triggered**: Check SQS event source mapping
2. **Progress stuck**: Check DynamoDB for processed_count value
3. **No WebSocket updates**: Verify connection_id in meta item
4. **Excel generation fails**: Check S3 permissions and bucket name

## Future Enhancements

1. **Google Drive Integration**: Replace simulated files with real Google Drive API calls
2. **AWS Textract Integration**: Add OCR for PDF processing
3. **Authentication**: Add Cognito user pools for WebSocket API
4. **Observability**: Add X-Ray tracing for distributed tracing
5. **Error Handling**: Add DLQ (Dead Letter Queue) for failed messages
6. **Pagination**: Support large file lists (10,000+)
7. **Filtering**: Allow user to filter results by hole code in frontend

## Development Workflow

### Build & Deploy
```bash
# Infrastructure
cd infra
npm install
npm run build
cdk deploy

# Frontend
cd frontend
npm install
npm run dev  # Development
npm run build  # Production
```

### Testing
```bash
# Test WebSocket connection
python test_websocket.py

# Manual testing
1. Start frontend (localhost:3000)
2. Enter WebSocket URL from CDK output
3. Click "Start Processing"
4. Observe real-time updates
5. Download Excel report
```

## File Structure
```
.
├── infra/
│   ├── lib/stack.ts          # Main CDK stack (SQS, DynamoDB, Lambda)
│   ├── bin/app.ts            # CDK app entry point
│   └── package.json
├── backend/
│   ├── src/
│   │   ├── process_handler.py   # Dispatcher Lambda
│   │   └── worker_handler.py    # Worker Lambda
│   └── layer/
│       └── requirements.txt     # boto3, openpyxl
├── frontend/
│   ├── src/
│   │   ├── Dashboard.jsx        # Main UI component
│   │   └── main.jsx
│   └── package.json
├── ARCHITECTURE.md              # System architecture diagram
├── AI_CONTEXT.md                # This file
└── README.md                    # User-facing documentation
```

## Important Notes for AI Modifications

1. **Session ID**: Always use UUID for session_id to avoid collisions
2. **Atomic Updates**: Use `UpdateExpression` for processed_count (never read-modify-write)
3. **WebSocket Errors**: Always catch `GoneException` (client disconnected)
4. **SQS Batch Size**: Keep at 10 for optimal Lambda concurrency
5. **DynamoDB Query**: Always filter `file_name != 'meta'` when querying results
6. **Excel Generation**: Only worker should generate Excel (on completion)
7. **Error Handling**: Log errors but don't crash Lambda (partial success is OK)
8. **Connection ID**: Store in meta item for workers to send progress updates

## Related Documentation

- `ARCHITECTURE.md`: System architecture diagrams and component descriptions
- `README.md`: User guide, setup instructions, API reference
- `QUICKSTART.md`: Quick deployment guide
- CDK Stack: `infra/lib/stack.ts` (all AWS resources)
