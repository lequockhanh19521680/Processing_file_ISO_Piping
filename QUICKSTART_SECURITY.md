# Quick Reference Guide - Security & Deployment

## 🚀 Quick Start

### 1️⃣ Deploy Backend (5 minutes)
```bash
cd infra
npm install
npm run build
cdk deploy
```

**Save these outputs:**
- `WebSocketURL` - for frontend configuration
- `GoogleDriveSecretArn` - for setting credentials
- `AmplifyAppUrl` - your deployed frontend URL

### 2️⃣ Set Credentials (1 minute)
```bash
aws secretsmanager put-secret-value \
  --secret-id processing-file-iso/google-drive-credentials \
  --secret-string '{"api_key":"YOUR_KEY","api_token":"YOUR_TOKEN"}'
```

### 3️⃣ Deploy Frontend (2 minutes)
**Option A: AWS Amplify (Recommended)**
1. Go to AWS Amplify Console
2. Find app: `ProcessingFileISOPipingFrontend`
3. Connect GitHub repository
4. Branch: `main`
5. Done! Auto-deploys on every push

**Option B: Local Development**
```bash
cd frontend
echo "VITE_WEBSOCKET_URL=<WebSocketURL from step 1>" > .env
npm install
npm run dev
```

## 📋 Key Files

| File | Purpose |
|------|---------|
| `SECURITY_DEPLOYMENT.md` | Complete deployment guide (detailed) |
| `IMPLEMENTATION_CHANGES.md` | Technical implementation details |
| `README.md` | Project overview and features |
| `amplify.yml` | Amplify build configuration |
| `infra/lib/stack.ts` | CDK infrastructure code |

## 🔒 Security Features

- ✅ Secrets in AWS Secrets Manager
- ✅ No hardcoded credentials
- ✅ IAM role-based access
- ✅ Automatic environment injection
- ✅ WebSocket URL in Parameter Store

## 🔑 Environment Variables

### Backend (Automatic via CDK)
- `GOOGLE_DRIVE_SECRET_ARN` ✅ Auto-set
- `WEBSOCKET_API_ENDPOINT` ✅ Auto-set
- `QUEUE_URL` ✅ Auto-set
- `TABLE_NAME` ✅ Auto-set
- `RESULTS_BUCKET` ✅ Auto-set

### Frontend
- `VITE_WEBSOCKET_URL` 
  - Amplify: ✅ Auto-injected from CDK
  - Local: 🔧 Set in `.env` file

## 📦 What's Deployed?

```
AWS Resources:
├── Secrets Manager
│   └── processing-file-iso/google-drive-credentials
├── Parameter Store
│   └── /processing-file-iso/websocket-url
├── Lambda Functions
│   ├── ScanDispatcher (with Secrets Manager access)
│   └── ScanWorker (with Secrets Manager access)
├── API Gateway WebSocket
├── DynamoDB Table
├── SQS Queue
├── S3 Bucket
└── Amplify App
    └── Auto-deployment on git push
```

## 🛠️ Common Commands

### View Logs
```bash
# Dispatcher logs
aws logs tail /aws/lambda/ProcessingFileISOPipingStack-ScanDispatcher --follow

# Worker logs
aws logs tail /aws/lambda/ProcessingFileISOPipingStack-ScanWorker --follow
```

### Get WebSocket URL
```bash
aws ssm get-parameter \
  --name /processing-file-iso/websocket-url \
  --query 'Parameter.Value' \
  --output text
```

### Update Credentials
```bash
aws secretsmanager update-secret \
  --secret-id processing-file-iso/google-drive-credentials \
  --secret-string '{"api_key":"NEW_KEY","api_token":"NEW_TOKEN"}'
```

### Redeploy Frontend
```bash
# Automatic: Just push to main
git push origin main

# Manual trigger in Amplify Console
# Or rebuild CDK to update env vars
cd infra && cdk deploy
```

## 🐛 Troubleshooting

### Can't access Secrets Manager
```bash
# Check IAM permissions
aws iam get-role-policy \
  --role-name ProcessingFileISOPipingStack-ScanDispatcher-Role \
  --policy-name SecretsManagerPolicy
```

### Frontend can't connect
1. Check WebSocket URL in Amplify environment variables
2. Verify API Gateway is deployed
3. Check browser console for errors

### Build fails
```bash
# CDK build
cd infra && npm run build

# Frontend build
cd frontend && npm run build
```

## 💰 Cost Estimate

| Service | Monthly Cost |
|---------|--------------|
| Secrets Manager | ~$0.50 |
| Lambda (light usage) | ~$0.10 |
| API Gateway | ~$0.05 |
| DynamoDB | ~$0.10 |
| S3 | ~$0.05 |
| Amplify | ~$0-5 |
| **Total** | **~$1-6/month** |

## 📚 Learn More

- [SECURITY_DEPLOYMENT.md](./SECURITY_DEPLOYMENT.md) - Detailed deployment guide
- [IMPLEMENTATION_CHANGES.md](./IMPLEMENTATION_CHANGES.md) - Technical details
- [README.md](./README.md) - Project overview

## ✅ Checklist

- [ ] CDK deployed successfully
- [ ] Credentials set in Secrets Manager
- [ ] Amplify connected to GitHub
- [ ] Frontend accessible via Amplify URL
- [ ] WebSocket connection working
- [ ] First test scan completed
- [ ] CloudWatch logs visible
- [ ] Excel report downloadable

---

**Need help?** Check the detailed guides or CloudWatch Logs for error messages.

🎉 **You're all set!** Your application is now secure and auto-deploying!
