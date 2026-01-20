# Security and Deployment Guide

This guide explains how to securely manage sensitive information and deploy the application using AWS services.

## Table of Contents
1. [Security Overview](#security-overview)
2. [Backend Secrets Management](#backend-secrets-management)
3. [Frontend Environment Configuration](#frontend-environment-configuration)
4. [AWS Amplify Deployment](#aws-amplify-deployment)
5. [Manual Deployment Alternative](#manual-deployment-alternative)

---

## Security Overview

The application now follows AWS security best practices by:

- ✅ **Backend secrets** stored in AWS Secrets Manager (Google Drive API credentials)
- ✅ **WebSocket URL** stored in AWS Systems Manager Parameter Store
- ✅ **Frontend environment variables** managed through AWS Amplify or `.env` files
- ✅ **No hardcoded credentials** in source code
- ✅ **IAM roles** with least-privilege permissions

---

## Backend Secrets Management

### 1. Deploy the Infrastructure

First, deploy the CDK stack which creates all necessary resources including the Secrets Manager secret:

```bash
cd infra
npm install
npm run build
cdk deploy
```

### 2. Set Google Drive API Credentials

After deployment, you need to set the actual Google Drive API credentials in AWS Secrets Manager.

The CDK stack creates a secret named `processing-file-iso/google-drive-credentials` with placeholder values.

#### Option A: Using AWS CLI

```bash
aws secretsmanager put-secret-value \
  --secret-id processing-file-iso/google-drive-credentials \
  --secret-string '{"api_key":"YOUR_ACTUAL_API_KEY","api_token":"YOUR_ACTUAL_TOKEN"}'
```

#### Option B: Using AWS Console

1. Go to **AWS Secrets Manager** console
2. Find the secret named `processing-file-iso/google-drive-credentials`
3. Click **"Retrieve secret value"**
4. Click **"Edit"**
5. Replace the placeholder values with your actual credentials:
   ```json
   {
     "api_key": "YOUR_ACTUAL_API_KEY",
     "api_token": "YOUR_ACTUAL_TOKEN"
   }
   ```
6. Click **"Save"**

### 3. Verify Secret Access

The Lambda functions automatically retrieve credentials from Secrets Manager at runtime. Check CloudWatch Logs to verify:

```bash
# View ScanDispatcher logs
aws logs tail /aws/lambda/ProcessingFileISOPipingStack-ScanDispatcher --follow

# View ScanWorker logs
aws logs tail /aws/lambda/ProcessingFileISOPipingStack-ScanWorker --follow
```

---

## Frontend Environment Configuration

The frontend needs the WebSocket URL to connect to the backend. This can be configured in multiple ways:

### Option 1: Using Amplify (Automatic - Recommended)

When deploying via AWS Amplify, the WebSocket URL is automatically injected as an environment variable. No manual configuration needed!

### Option 2: Local Development

For local development, create a `.env` file in the `frontend/` directory:

```bash
cd frontend
cp .env.example .env
```

Edit `.env` and set the WebSocket URL from CDK output:

```env
VITE_WEBSOCKET_URL=wss://xxxxx.execute-api.region.amazonaws.com/prod
```

### Option 3: Retrieve from Parameter Store

You can retrieve the WebSocket URL from AWS Systems Manager Parameter Store:

```bash
# Get the WebSocket URL
aws ssm get-parameter \
  --name /processing-file-iso/websocket-url \
  --query 'Parameter.Value' \
  --output text
```

---

## AWS Amplify Deployment

AWS Amplify provides automatic CI/CD deployment for the frontend with every Git push.

### Step 1: Get Amplify App ID from CDK Output

After running `cdk deploy`, note the `AmplifyAppId` and `AmplifyAppUrl` outputs:

```
Outputs:
ProcessingFileISOPipingStack.AmplifyAppId = d1234567890abc
ProcessingFileISOPipingStack.AmplifyAppUrl = https://main.d1234567890abc.amplifyapp.com
```

### Step 2: Connect GitHub Repository

#### Option A: Manual Connection (Recommended for first-time setup)

1. Go to **AWS Amplify** console
2. Find your app: `ProcessingFileISOPipingFrontend`
3. Click on the app name
4. Under **"App settings"** → **"General"**, click **"Edit"**
5. In the **"Repository"** section, click **"Connect repository"**
6. Choose **GitHub** and authorize AWS Amplify to access your repository
7. Select repository: `lequockhanh19521680/Processing_file_ISO_Piping`
8. Select branch: `main`
9. The build settings are already configured via CDK
10. Click **"Save and deploy"**

#### Option B: Automated with GitHub Token (Advanced)

To enable automatic deployment without manual GitHub connection:

1. Create a GitHub Personal Access Token:
   - Go to GitHub → Settings → Developer settings → Personal access tokens
   - Generate new token with `repo` scope
   
2. Store the token in AWS Secrets Manager:
   ```bash
   aws secretsmanager create-secret \
     --name processing-file-iso/github-token \
     --secret-string 'your_github_personal_access_token'
   ```

3. Update the CDK stack to use the token (uncomment lines in `stack.ts`):
   ```typescript
   const githubToken = secretsmanager.Secret.fromSecretNameV2(
     this, 
     'GitHubToken', 
     'processing-file-iso/github-token'
   );
   
   const amplifyApp = new amplify.CfnApp(this, 'AmplifyApp', {
     // ... other properties
     accessToken: githubToken.secretValue.unsafeUnwrap(),
   });
   ```

### Step 3: Verify Deployment

1. Go to the Amplify console
2. Check the build status under **"Builds"**
3. Once the build succeeds, access your app at the `AmplifyAppUrl`

### Step 4: Configure Environment Variables (Automatic)

The WebSocket URL is automatically set as an environment variable through the CDK stack. You can verify this:

1. Go to Amplify Console → Your App
2. Click **"Environment variables"** in the left menu
3. You should see `VITE_WEBSOCKET_URL` already configured

### Trigger New Deployments

Amplify automatically deploys on every push to the `main` branch. You can also manually trigger a deployment:

1. Go to Amplify Console → Your App
2. Click the **"Run build"** button

---

## Manual Deployment Alternative

If you prefer not to use AWS Amplify, you can manually build and deploy the frontend to S3 + CloudFront:

### Option 1: S3 Static Website Hosting

```bash
# Build the frontend
cd frontend
npm install
npm run build

# Create S3 bucket for hosting
aws s3 mb s3://your-bucket-name --region us-east-1

# Enable static website hosting
aws s3 website s3://your-bucket-name \
  --index-document index.html \
  --error-document index.html

# Upload built files
aws s3 sync dist/ s3://your-bucket-name --delete

# Make files public (use with caution, consider CloudFront instead)
aws s3api put-bucket-policy --bucket your-bucket-name --policy '{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::your-bucket-name/*"
  }]
}'
```

### Option 2: S3 + CloudFront (Recommended)

For production, use CloudFront for better performance and security:

```bash
# Create CloudFront distribution (simplified example)
aws cloudfront create-distribution \
  --origin-domain-name your-bucket-name.s3.amazonaws.com \
  --default-root-object index.html
```

Or add CloudFront to your CDK stack for automated deployment.

---

## Security Best Practices

### 1. Rotate Secrets Regularly

Set up automatic rotation for Google Drive API credentials:

```bash
aws secretsmanager rotate-secret \
  --secret-id processing-file-iso/google-drive-credentials \
  --rotation-lambda-arn arn:aws:lambda:region:account:function:rotation-function
```

### 2. Use IAM Roles, Not Access Keys

The Lambda functions use IAM roles to access AWS services. Never hardcode AWS access keys.

### 3. Enable CloudWatch Logs Encryption

Encrypt CloudWatch Logs at rest using KMS:

```bash
aws logs associate-kms-key \
  --log-group-name /aws/lambda/ProcessingFileISOPipingStack-ScanDispatcher \
  --kms-key-id arn:aws:kms:region:account:key/key-id
```

### 4. Restrict CORS Origins

In production, update the S3 bucket CORS configuration to only allow your frontend domain:

```typescript
// In stack.ts
cors: [{
  allowedOrigins: ['https://your-frontend-domain.com'],
  // ... other settings
}]
```

### 5. Enable AWS WAF

For production deployments, enable AWS WAF on your API Gateway and CloudFront distribution to protect against common web exploits.

---

## Troubleshooting

### Issue: Lambda can't access Secrets Manager

**Solution:** Verify IAM permissions. The CDK stack automatically grants `secretsmanager:GetSecretValue` permission, but check CloudWatch Logs for permission errors.

### Issue: Frontend can't connect to WebSocket

**Solution:** 
1. Verify the WebSocket URL is correct in environment variables
2. Check that CORS is properly configured
3. Verify the API Gateway WebSocket API is deployed

### Issue: Amplify build fails

**Solution:**
1. Check the build logs in Amplify Console
2. Verify `amplify.yml` configuration is correct
3. Ensure all dependencies are listed in `frontend/package.json`

---

## Additional Resources

- [AWS Secrets Manager Documentation](https://docs.aws.amazon.com/secretsmanager/)
- [AWS Amplify Documentation](https://docs.aws.amazon.com/amplify/)
- [AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)
- [CDK Best Practices](https://docs.aws.amazon.com/cdk/latest/guide/best-practices.html)

---

## Summary

✅ **Backend:** Secrets stored in AWS Secrets Manager, accessed via IAM roles  
✅ **Frontend:** Environment variables managed by Amplify or `.env` files  
✅ **Deployment:** Automated CI/CD with AWS Amplify  
✅ **Security:** No hardcoded credentials, least-privilege IAM policies

Your application is now secure and ready for production deployment! 🚀
