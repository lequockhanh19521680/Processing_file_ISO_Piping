# Quick Start Guide

## Prerequisites Check

Before deploying, ensure you have:

- [ ] Node.js 18+ installed: `node --version`
- [ ] Python 3.11+ installed: `python3 --version`
- [ ] AWS CLI configured: `aws sts get-caller-identity`
- [ ] AWS CDK CLI installed: `npm install -g aws-cdk`

## Deployment Steps

### 1. Infrastructure Deployment (~5 minutes)

```bash
# Navigate to infrastructure directory
cd infra

# Install dependencies
npm install

# Bootstrap CDK (first time only in your AWS account/region)
cdk bootstrap

# Build TypeScript
npm run build

# Preview changes (optional)
cdk diff

# Deploy the stack
cdk deploy

# Save the outputs
# WebSocketURL: wss://xxxxx.execute-api.us-east-1.amazonaws.com/prod
# ResultsBucketName: processingfileisopiping-resultsbucketxxxxx
# WebSocketApiId: xxxxx
```

### 2. Frontend Setup (~2 minutes)

```bash
# Navigate to frontend directory
cd ../frontend

# Install dependencies
npm install

# Start development server
npm run dev

# The app will open at http://localhost:3000
```

### 3. Using the Application

1. **Copy WebSocket URL** from CDK output
2. **Paste it** into the Dashboard WebSocket URL field
3. **Enter** your Google Drive Token
4. **Upload** Excel file with hole codes (optional for demo)
5. **Click** "Start Processing"
6. **Watch** real-time updates:
   - Connection status turns green
   - Progress bar moves from 0% to 100%
   - Results appear row by row
7. **Download** final Excel when complete

## Testing Without Real Data

The system includes demo mode with simulated data:

- Simulates 100 files (instead of 6600)
- Generates sample hole codes: HOLE-0 through HOLE-9
- Processing takes ~5 seconds
- Perfect for testing the WebSocket flow

## Architecture Verification

After deployment, verify:

### Check Lambda Function
```bash
aws lambda get-function --function-name ProcessingFileISOPipingStack-ProcessHandler
```

### Check WebSocket API
```bash
aws apigatewayv2 get-apis --query 'Items[?Name==`ProcessingFileWebSocket`]'
```

### Check S3 Bucket
```bash
aws s3 ls | grep results
```

### Test WebSocket Connection
Use a WebSocket client or the frontend to test:
```javascript
const ws = new WebSocket('wss://YOUR_API_ID.execute-api.REGION.amazonaws.com/prod');
ws.onopen = () => console.log('Connected!');
ws.onmessage = (event) => console.log('Message:', event.data);
```

## Cleanup

To avoid AWS charges, destroy the stack when done:

```bash
cd infra
cdk destroy
```

This will:
- Delete Lambda functions
- Delete API Gateway
- Delete S3 bucket and contents
- Remove all CloudWatch logs

## Common Issues

### Issue: CDK Bootstrap Failed
**Solution**: Ensure AWS credentials are configured
```bash
aws configure
aws sts get-caller-identity
```

### Issue: Lambda Deployment Failed
**Solution**: Check Lambda layer dependencies
```bash
cd backend/layer
pip install -r requirements.txt -t python/
```

### Issue: WebSocket Connection Failed
**Solution**: 
1. Verify WebSocket URL format: `wss://` not `https://`
2. Check API Gateway stage deployment
3. Review CloudWatch logs

### Issue: Frontend Build Failed
**Solution**: Clear node_modules and reinstall
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

## Development Tips

### Watch CDK Changes
```bash
cd infra
npm run watch
```

### View Lambda Logs
```bash
aws logs tail /aws/lambda/ProcessingFileISOPipingStack-ProcessHandler --follow
```

### Hot Reload Frontend
```bash
cd frontend
npm run dev
# Changes auto-reload at http://localhost:3000
```

### Update Lambda Code Only
```bash
cd infra
cdk deploy --hotswap
# Faster deployment, skips CloudFormation for Lambda changes
```

## Cost Estimation

**Development/Testing**: ~$0.50/day
- Lambda: $0.0000166667 per GB-second
- API Gateway WebSocket: $0.25 per million minutes
- S3: $0.023 per GB
- CloudWatch: Free tier covers most logs

**Production (6600 files/run)**: ~$5-10/run
- Mainly Textract costs (~$1.50 per 1000 pages)
- Lambda execution: ~$2-3
- S3 storage: minimal

## Next Steps

1. ✅ Deploy infrastructure
2. ✅ Test with demo data
3. 🔄 Integrate Google Drive API
4. 🔄 Add AWS Textract processing
5. 🔄 Implement authentication
6. 🔄 Deploy frontend to S3/CloudFront
7. 🔄 Add CloudWatch alarms
8. 🔄 Implement Step Functions for large batches

## Support

For issues or questions:
1. Check CloudWatch logs
2. Review README.md
3. Check AWS CloudFormation events
4. Verify IAM permissions
