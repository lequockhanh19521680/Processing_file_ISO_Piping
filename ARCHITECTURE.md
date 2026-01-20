# System Architecture

## Overview

This document describes the **async event-driven file processing system** using AWS services with WebSocket for real-time user feedback. The system is designed to process thousands of files (6,600+) without Lambda timeout issues by using **SQS for distributed processing** and **DynamoDB for state management**.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           User's Browser                             │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │                    React Frontend                           │     │
│  │  - Dashboard.jsx (Real-time UI)                            │     │
│  │  - WebSocket Connection (react-use-websocket)              │     │
│  │  - Progress Bar, Live Results Table                        │     │
│  │  - Control Panel                                            │     │
│  └────────────────────────────────────────────────────────────┘     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ WebSocket (wss://)
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    AWS API Gateway (WebSocket)                       │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  Routes:                                                    │     │
│  │  - $connect    → ConnectHandler Lambda                     │     │
│  │  - $disconnect → DisconnectHandler Lambda                  │     │
│  │  - $default    → DefaultHandler Lambda                     │     │
│  │  - start_scan  → ScanDispatcher Lambda ⭐                   │     │
│  └────────────────────────────────────────────────────────────┘     │
└──────────────┬──────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    AWS Lambda (ScanDispatcher)                       │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  1. Extract connectionId from event                        │     │
│  │  2. Parse request (token, file_content, hole_codes)        │     │
│  │  3. Generate unique session_id (UUID)                      │     │
│  │  4. Store session metadata in DynamoDB                     │     │
│  │  5. Batch send file metadata to SQS (10 per batch)         │     │
│  │  6. Send STARTED message via WebSocket                     │     │
│  │  7. Exit immediately (no processing)                       │     │
│  └────────────────────────────────────────────────────────────┘     │
└────┬────────────────────────────────────┬────────────────────────────┘
     │                                    │
     │ WebSocket Update                   │ Send Messages
     │                                    │
     ▼                                    ▼
┌─────────────┐                  ┌─────────────────────────┐
│   API GW    │                  │    Amazon SQS Queue     │
│  Management │                  │  (ProcessingQueue)      │
│     API     │                  │  - Decouples dispatch   │
└─────────────┘                  │  - Batch processing     │
                                 │  - Auto retry           │
                                 └────────┬────────────────┘
                                          │
                                          │ Event Source (batch=10)
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      AWS Lambda (ScanWorker)                         │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  1. Read batch of 10 messages from SQS                     │     │
│  │  2. For each file:                                         │     │
│  │     - Process file (extract text, match hole codes)        │     │
│  │     - Write result to DynamoDB                             │     │
│  │     - Atomic increment: processed_count                    │     │
│  │     - Send PROGRESS update via WebSocket                   │     │
│  │     - If match found → Send MATCH_FOUND                    │     │
│  │  3. Check if processed_count == total_files                │     │
│  │  4. If complete:                                           │     │
│  │     - Query all results from DynamoDB                      │     │
│  │     - Generate Excel report                                │     │
│  │     - Upload to S3                                         │     │
│  │     - Send COMPLETE with download URL                      │     │
│  └────────────────────────────────────────────────────────────┘     │
└────┬──────────────────────────────────────┬────────────────────┬────┘
     │                                      │                    │
     │ Push updates                         │ Read/Write         │ Write
     │ via API Gateway                      │                    │
     │ Management API                       ▼                    ▼
     │                            ┌──────────────────┐  ┌─────────────┐
     │                            │   DynamoDB       │  │   AWS S3    │
     │                            │  (ProcessResults)│  │  (Results)  │
     │                            │  - Session state │  │  - Excel    │
     │                            │  - File results  │  │    reports  │
     │                            │  - Atomic counter│  └─────────────┘
     │                            └──────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────┐
│           API Gateway Management API (apigatewaymanagementapi)       │
│  - post_to_connection(ConnectionId, Data)                           │
│  - Sends JSON messages back to connected WebSocket clients          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               │ Real-time messages
                               │
                               ▼
                      ┌─────────────────┐
                      │  User Browser   │
                      │  (Updates UI)   │
                      └─────────────────┘
```

## Data Flow

### 1. Initial Connection

```
User → Frontend → WebSocket API → $connect route → ConnectHandler Lambda
                                                         ↓
                                              Connection established
                                                         ↓
                                              connectionId stored
```

### 2. Start Processing Request (Dispatcher Phase)

```
User clicks "Start Processing"
    ↓
Frontend sends message:
{
  "action": "start_scan",
  "token": "google_drive_token",
  "file_content": "...",
  "target_hole_codes": ["HOLE-1", "HOLE-2", ...]
}
    ↓
WebSocket API → start_scan route → ScanDispatcher Lambda
    ↓
1. Generate session_id (UUID)
    ↓
2. Store session metadata in DynamoDB:
   - session_id, file_name="meta"
   - connection_id, total_files, processed_count=0
    ↓
3. Batch send file metadata to SQS (10 per batch)
    ↓
4. Send STARTED message to WebSocket
    ↓
5. Lambda exits (does not wait for processing)
```

### 3. Asynchronous Processing Loop (Worker Phase)

```
SQS Queue triggers ScanWorker Lambda (batch of 10 files)
    ↓
For each file in batch:
    ├─ Extract file metadata from SQS message
    ├─ Process file (extract text, match hole codes)
    ├─ Write result to DynamoDB (session_id, file_name)
    ├─ Atomic increment processed_count in meta item
    ├─ Retrieve meta to get connection_id, total_files
    ├─ If match found → Send MATCH_FOUND → Frontend adds row
    └─ Send PROGRESS message → Frontend updates progress bar
    ↓
Check if processed_count == total_files
    ↓
If complete:
    ├─ Query all results from DynamoDB
    ├─ Generate Excel report
    ├─ Upload to S3
    ├─ Generate presigned URL
    └─ Send COMPLETE message with download URL
    ↓
Frontend receives COMPLETE → Shows download button
```

## Message Protocol

### Frontend → Backend (via WebSocket)

```json
{
  "action": "start_scan",
  "token": "google_drive_api_token",
  "file_content": "base64_encoded_excel_or_file_data",
  "target_hole_codes": ["HOLE-1", "HOLE-2", "HOLE-3"]
}
```

### Backend → Frontend (via WebSocket)

#### 1. STARTED
```json
{
  "type": "STARTED",
  "message": "Processing started",
  "timestamp": "2026-01-20T03:00:00.000Z"
}
```

#### 2. PROGRESS
```json
{
  "type": "PROGRESS",
  "value": 45,
  "processed": 450,
  "total": 1000
}
```

#### 3. MATCH_FOUND
```json
{
  "type": "MATCH_FOUND",
  "data": {
    "hole_code": "HOLE-123",
    "file_name": "drawing_456.pdf",
    "status": "1 Code",
    "pdf_link": "https://drive.google.com/file/d/..."
  }
}
```

#### 4. COMPLETE
```json
{
  "type": "COMPLETE",
  "download_url": "https://s3.amazonaws.com/.../results.xlsx",
  "total_matches": 42,
  "total_processed": 1000,
  "message": "Processing completed successfully"
}
```

#### 5. ERROR
```json
{
  "type": "ERROR",
  "message": "Error description"
}
```

## AWS Resources

### CDK Stack Resources

| Resource | Type | Purpose |
|----------|------|---------|
| WebSocketApi | WebSocket API Gateway | Manages WebSocket connections |
| ScanDispatcher | Lambda Function | Dispatcher - sends files to SQS |
| ScanWorker | Lambda Function | Worker - processes files from SQS |
| ConnectHandler | Lambda Function | Handles $connect events |
| DisconnectHandler | Lambda Function | Handles $disconnect events |
| DefaultHandler | Lambda Function | Handles $default route |
| ProcessingQueue | SQS Queue | Message queue for file processing tasks |
| ProcessResultsTable | DynamoDB Table | Stores session state and file results |
| ResultsBucket | S3 Bucket | Stores Excel reports |
| DependenciesLayer | Lambda Layer | Python dependencies (boto3, openpyxl) |

### IAM Permissions

#### ScanDispatcher Lambda Role
- `execute-api:ManageConnections` - Send messages to WebSocket clients
- `sqs:SendMessage` - Send file metadata to SQS queue
- `dynamodb:PutItem` - Store session metadata
- `logs:*` - CloudWatch logging

#### ScanWorker Lambda Role
- `execute-api:ManageConnections` - Send progress updates to WebSocket clients
- `dynamodb:UpdateItem` - Update processed_count atomically
- `dynamodb:Query` - Retrieve session results
- `s3:PutObject` - Upload Excel reports to S3
- `logs:*` - CloudWatch logging

## Scalability

### Concurrent Users
- **WebSocket Connections**: API Gateway supports 100,000+ concurrent connections
- **Lambda Concurrency**: Default 1,000 concurrent executions per region
- **SQS Throughput**: Unlimited messages per second
- **DynamoDB**: On-demand billing scales automatically
- **S3**: Unlimited storage, 5,500 PUT requests/second per prefix

### Performance Optimization
1. **Event-Driven Architecture**: Dispatcher exits immediately, workers process in parallel
2. **SQS Batching**: Process 10 files per Lambda invocation
3. **DynamoDB Atomic Updates**: No race conditions on processed_count
4. **Parallel Workers**: Multiple Lambda instances process simultaneously
5. **S3 Presigned URLs**: Direct download from S3, no Lambda proxy
6. **Lambda Layers**: Shared dependencies, faster cold starts

### No Timeout Issues
- **Old Architecture**: Single Lambda processes all files (15-min timeout for 6,600 files)
- **New Architecture**: Each worker processes 10 files (~5 seconds), unlimited total files

## Cost Breakdown (Example: 6600 files)

| Service | Usage | Cost |
|---------|-------|------|
| Lambda (Dispatcher) | 1 invocation × 512 MB × 5s × $0.0000166667 | ~$0.0001 |
| Lambda (Worker) | 660 invocations × 1024 MB × 5s × $0.0000166667 | ~$0.05 |
| SQS | 6,600 messages × $0.40/M requests | ~$0.003 |
| DynamoDB | 6,600 writes + 6,600 reads × $1.25/M requests | ~$0.02 |
| API Gateway WebSocket | 10 min × $0.25/M min | ~$0.003 |
| S3 Storage | 1 MB × $0.023/GB | ~$0.0001 |
| **Total per run (without Textract)** | | **~$0.07** |
| Textract (optional) | 6600 pages × $0.0015/page | ~$9.90 |
| **Total with Textract** | | **~$10.00** |

## Security

### Authentication & Authorization
- **Current**: Open WebSocket (demo only)
- **Production TODO**:
  - API Gateway authorizers (Lambda or Cognito)
  - JWT tokens
  - IAM authentication

### Data Protection
- WebSocket uses TLS (wss://)
- S3 presigned URLs with 1-hour expiration
- No sensitive data in logs
- Environment variables for secrets

### Network Security
- API Gateway in public subnet (WebSocket endpoint)
- Lambda in VPC (optional, for database access)
- S3 bucket policies restrict access

## Monitoring & Logging

### CloudWatch Logs
- Lambda execution logs
- API Gateway access logs
- WebSocket connection/disconnection events

### Metrics
- Lambda invocations, duration, errors
- API Gateway connection count, message count
- S3 object count, storage size

### Alarms (Recommended)
- Lambda error rate > 5%
- Lambda duration > 14 minutes (near timeout)
- API Gateway 5xx errors
- S3 bucket size > threshold

## Future Enhancements

1. **Google Drive API Integration**: Replace simulated files with real Google Drive file fetching
2. **AWS Textract Integration**: Add OCR for PDF processing
3. **DLQ (Dead Letter Queue)**: Handle failed message processing
4. **CloudFront**: Host frontend static assets
5. **Cognito**: User authentication and authorization
6. **EventBridge**: Scheduled processing triggers
7. **SNS**: Email notifications on completion
8. **X-Ray Tracing**: Distributed tracing for debugging
9. **Pagination**: Support for very large file lists (10,000+)
10. **Rate Limiting**: Prevent abuse of API

## Development vs Production

| Aspect | Development | Production |
|--------|-------------|------------|
| Files | 100 (demo) | 6,600+ |
| Architecture | Event-driven with SQS | Event-driven with SQS |
| Timeout Risk | None | None (distributed processing) |
| Authentication | None | Cognito/API Key |
| Monitoring | Basic logs | Full observability |
| Error handling | Simple | Retry logic, DLQ |
| Frontend | Local (localhost:3000) | CloudFront |
| Cost | ~$0.01/day | ~$0.07/run (without Textract) |

## Deployment Topology

```
Developer Machine
    ↓ (cdk deploy)
AWS CloudFormation Stack
    ↓ (creates)
├─ API Gateway WebSocket API
├─ Lambda Functions (6: Dispatcher, Worker, Connect, Disconnect, Default)
├─ SQS Queue (ProcessingQueue)
├─ DynamoDB Table (ProcessResultsTable)
├─ S3 Bucket (ResultsBucket)
├─ IAM Roles & Policies
└─ CloudWatch Log Groups
```

## References

- [AWS API Gateway WebSocket API](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api.html)
- [AWS Lambda](https://docs.aws.amazon.com/lambda/)
- [AWS CDK](https://docs.aws.amazon.com/cdk/)
- [React WebSocket](https://github.com/robtaussig/react-use-websocket)
