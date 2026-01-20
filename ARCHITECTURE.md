# System Architecture

## Overview

This document describes the real-time file processing system architecture using AWS services and WebSocket communication.

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
│  │  - start_scan  → ProcessHandler Lambda ⭐                   │     │
│  └────────────────────────────────────────────────────────────┘     │
└──────────────┬──────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    AWS Lambda (ProcessHandler)                       │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  1. Extract connectionId from event                        │     │
│  │  2. Parse request (token, file_content, hole_codes)        │     │
│  │  3. Initialize WebSocket Manager                           │     │
│  │  4. Process files in batches                               │     │
│  │     - Fetch from Google Drive (future)                     │     │
│  │     - Extract text with Textract (future)                  │     │
│  │     - Match hole codes                                     │     │
│  │  5. Send real-time updates via WebSocket                   │     │
│  │     - STARTED, PROGRESS, MATCH_FOUND, COMPLETE, ERROR      │     │
│  │  6. Generate Excel report                                  │     │
│  │  7. Upload to S3                                           │     │
│  └────────────────────────────────────────────────────────────┘     │
└────┬──────────────────────────────────────┬────────────────────┬────┘
     │                                      │                    │
     │ Push updates                         │ Read/Write         │
     │ via API Gateway                      │                    │
     │ Management API                       ▼                    ▼
     │                            ┌──────────────────┐  ┌─────────────┐
     │                            │   AWS Textract   │  │   AWS S3    │
     │                            │  (Future: OCR)   │  │  (Results)  │
     │                            └──────────────────┘  └─────────────┘
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

### 2. Start Processing Request

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
WebSocket API → start_scan route → ProcessHandler Lambda
```

### 3. Real-time Processing Loop

```
ProcessHandler Lambda:
    ↓
1. Extract connectionId from event['requestContext']['connectionId']
    ↓
2. Initialize WebSocketManager with API Gateway Management API endpoint
    ↓
3. Send STARTED message
    ↓
4. For each batch of 10 files:
    ├─ Process file (extract text, match hole codes)
    ├─ If match found → Send MATCH_FOUND message → Frontend adds row
    └─ After batch → Send PROGRESS message → Frontend updates progress bar
    ↓
5. Generate Excel report
    ↓
6. Upload to S3
    ↓
7. Send COMPLETE message with download URL
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
| ProcessHandler | Lambda Function | Main processing logic |
| ConnectHandler | Lambda Function | Handles $connect events |
| DisconnectHandler | Lambda Function | Handles $disconnect events |
| DefaultHandler | Lambda Function | Handles $default route |
| ResultsBucket | S3 Bucket | Stores Excel reports |
| DependenciesLayer | Lambda Layer | Python dependencies (boto3, openpyxl) |

### IAM Permissions

#### ProcessHandler Lambda Role
- `execute-api:ManageConnections` - Send messages to WebSocket clients
- `s3:PutObject`, `s3:GetObject` - Upload/download from S3
- `textract:*` - Process documents with Textract (future)
- `logs:*` - CloudWatch logging

## Scalability

### Concurrent Users
- **WebSocket Connections**: API Gateway supports 100,000+ concurrent connections
- **Lambda Concurrency**: Default 1,000 concurrent executions per region
- **S3**: Unlimited storage, 5,500 PUT requests/second per prefix

### Performance Optimization
1. **Batch Processing**: Process 10 files at a time to reduce message frequency
2. **Async Updates**: Send updates without blocking processing
3. **S3 Presigned URLs**: Direct download from S3, no Lambda proxy
4. **Lambda Layers**: Shared dependencies, faster cold starts

## Cost Breakdown (Example: 6600 files)

| Service | Usage | Cost |
|---------|-------|------|
| Lambda | 15 min × 2 GB × $0.0000166667 | ~$0.50 |
| API Gateway WebSocket | 15 min × $0.25/M min | ~$0.004 |
| S3 Storage | 1 MB × $0.023/GB | ~$0.0001 |
| Textract | 6600 pages × $0.0015/page | ~$9.90 |
| **Total per run** | | **~$10.40** |

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

1. **Step Functions**: For processing > 6600 files (beyond 15-min Lambda limit)
2. **DynamoDB**: Store connection mappings, processing state
3. **SQS**: Queue files for distributed processing
4. **CloudFront**: Host frontend static assets
5. **Cognito**: User authentication
6. **EventBridge**: Scheduled processing triggers
7. **SNS**: Email notifications on completion

## Development vs Production

| Aspect | Development | Production |
|--------|-------------|------------|
| Files | 100 (demo) | 6,600+ |
| Authentication | None | Cognito/API Key |
| Monitoring | Basic logs | Full observability |
| Error handling | Simple | Retry logic, DLQ |
| Frontend | Local (localhost:3000) | CloudFront |
| Cost | ~$0.50/day | ~$10/run |

## Deployment Topology

```
Developer Machine
    ↓ (cdk deploy)
AWS CloudFormation Stack
    ↓ (creates)
├─ API Gateway WebSocket API
├─ Lambda Functions (4)
├─ S3 Bucket
├─ IAM Roles & Policies
└─ CloudWatch Log Groups
```

## References

- [AWS API Gateway WebSocket API](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api.html)
- [AWS Lambda](https://docs.aws.amazon.com/lambda/)
- [AWS CDK](https://docs.aws.amazon.com/cdk/)
- [React WebSocket](https://github.com/robtaussig/react-use-websocket)
