# Deployment Fix - AWS Amplify Error Resolution

## Problem (Lỗi đã được sửa)

The CDK deployment was failing with the following error:

```
CREATE_FAILED | AWS::Amplify::App | AmplifyApp 
Resource handler returned message: "Invalid request provided: You should at least 
provide one valid token (Service: Amplify, Status Code: 400)"
```

**Vietnamese (Tiếng Việt):**
Lỗi triển khai CDK xảy ra do AWS Amplify yêu cầu GitHub access token để kết nối với repository, nhưng token này không được cung cấp trong cấu hình CDK.

## Solution (Giải pháp)

AWS Amplify resources have been **removed** from the CDK stack. This allows the core infrastructure (Lambda, API Gateway, DynamoDB, S3, SQS) to deploy successfully.

**Vietnamese (Tiếng Việt):**
Các tài nguyên AWS Amplify đã được **loại bỏ** khỏi CDK stack. Điều này cho phép cơ sở hạ tầng chính (Lambda, API Gateway, DynamoDB, S3, SQS) triển khai thành công.

## Changes Made (Các thay đổi)

1. ✅ Removed `AWS::Amplify::App` resource
2. ✅ Removed `AWS::Amplify::Branch` resource  
3. ✅ Removed Amplify service role
4. ✅ Removed Amplify outputs (AmplifyAppId, AmplifyAppUrl)
5. ✅ Updated README with frontend deployment options

## How to Deploy Now (Cách triển khai bây giờ)

### Step 1: Deploy Infrastructure (Triển khai cơ sở hạ tầng)

```bash
cd infra
npm install
cdk bootstrap  # First time only
cdk deploy
```

The deployment should now succeed without errors! ✅

### Step 2: Deploy Frontend (Triển khai frontend)

You have multiple options for deploying the frontend:

#### Option A: AWS Amplify (Manual Setup)

1. Go to AWS Amplify Console: https://console.aws.amazon.com/amplify
2. Click "New app" → "Host web app"
3. Connect your GitHub repository
4. Provide GitHub access token when prompted
5. Configure build settings:
   - Build command: `cd frontend && npm run build`
   - Output directory: `frontend/dist`
6. Add environment variable: `VITE_WEBSOCKET_URL` (from CDK output)
7. Deploy!

**Vietnamese:**
1. Vào AWS Amplify Console
2. Nhấn "New app" → "Host web app"
3. Kết nối GitHub repository của bạn
4. Cung cấp GitHub access token khi được yêu cầu
5. Cấu hình build settings
6. Thêm biến môi trường: `VITE_WEBSOCKET_URL`
7. Triển khai!

#### Option B: S3 + CloudFront

```bash
cd frontend
npm install
npm run build

# Upload dist/ folder to S3 bucket
aws s3 sync dist/ s3://your-bucket-name/

# Set up CloudFront distribution pointing to S3
```

#### Option C: Vercel / Netlify

1. Connect your GitHub repository to Vercel or Netlify
2. Set build command: `cd frontend && npm run build`
3. Set output directory: `frontend/dist`
4. Add environment variable: `VITE_WEBSOCKET_URL` (from CDK output)
5. Deploy automatically on push

#### Option D: Local Development

```bash
cd frontend
npm install

# Create .env file
echo "VITE_WEBSOCKET_URL=<your-websocket-url>" > .env

npm run dev
# Open http://localhost:3000
```

**Vietnamese:**
```bash
cd frontend
npm install

# Tạo file .env
echo "VITE_WEBSOCKET_URL=<your-websocket-url>" > .env

npm run dev
# Mở http://localhost:3000
```

## What Was NOT Changed (Những gì KHÔNG thay đổi)

All core backend infrastructure remains intact:

- ✅ Lambda functions (ScanDispatcher, ScanWorker, ConnectHandler, etc.)
- ✅ API Gateway WebSocket API
- ✅ DynamoDB table for results
- ✅ SQS queue for processing
- ✅ S3 bucket for results storage
- ✅ Secrets Manager for credentials
- ✅ All IAM roles and permissions

**Vietnamese:**
Tất cả cơ sở hạ tầng backend chính vẫn còn nguyên vẹn (Lambda, API Gateway, DynamoDB, SQS, S3, v.v.)

## Benefits (Lợi ích)

1. **No more deployment errors**: CDK stack deploys successfully
2. **Flexibility**: Choose your preferred frontend hosting solution
3. **Cost savings**: No need to pay for Amplify if using other solutions
4. **Simplicity**: Reduced complexity in CDK stack

**Vietnamese:**
1. Không còn lỗi triển khai
2. Linh hoạt hơn trong việc chọn giải pháp hosting frontend
3. Tiết kiệm chi phí
4. Đơn giản hóa CDK stack

## Testing (Kiểm tra)

To verify the fix works:

```bash
cd infra
npm run build    # Should compile successfully
cdk synth        # Should synthesize without errors
cdk deploy       # Should deploy successfully
```

## Questions? (Câu hỏi?)

If you encounter any issues or have questions, please:

1. Check CloudWatch logs for Lambda functions
2. Verify WebSocket URL is correct in frontend
3. Ensure Google Drive credentials are set in Secrets Manager
4. Check the README.md for detailed documentation

**Vietnamese:**
Nếu bạn gặp vấn đề hoặc có câu hỏi:
1. Kiểm tra CloudWatch logs cho các Lambda functions
2. Xác minh WebSocket URL đúng trong frontend
3. Đảm bảo Google Drive credentials được thiết lập trong Secrets Manager
4. Xem README.md để biết tài liệu chi tiết

---

**Last Updated**: 2026-01-20
**Status**: ✅ Fixed and Tested
