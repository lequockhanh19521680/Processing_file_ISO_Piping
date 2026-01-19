# Deployment Guide

This guide provides instructions for deploying the ISO Piping File Processor to production environments.

## Pre-Deployment Checklist

Before deploying to production:

- [ ] Service account credentials secured (not in code)
- [ ] Environment variables configured
- [ ] CORS origins restricted to frontend domain
- [ ] API URL configured for production frontend
- [ ] HTTPS enabled for all communications
- [ ] Error logging and monitoring set up
- [ ] File size limits configured
- [ ] Rate limiting configured (if needed)
- [ ] Backup and recovery plan in place

## Deployment Options

### Option 1: Docker Deployment (Recommended)

#### Create Dockerfile for Backend

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py .

# Create directory for credentials (mounted as volume)
RUN mkdir -p /app/credentials

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Create Dockerfile for Frontend

Create `frontend/Dockerfile`:

```dockerfile
# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy source files
COPY . .

# Build the app
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files to nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

#### Create nginx.conf

Create `frontend/nginx.conf`:

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

#### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./service-account.json:/app/credentials/service-account.json:ro
    environment:
      - SERVICE_ACCOUNT_FILE=/app/credentials/service-account.json
      - CORS_ORIGINS=http://localhost:3000,https://your-frontend-domain.com
      - LOG_LEVEL=INFO
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - backend
    restart: unless-stopped
```

#### Deploy with Docker

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

### Option 2: AWS Deployment

#### Backend on AWS Elastic Beanstalk

1. **Prepare Application**:
   ```bash
   cd backend
   zip -r app.zip *.py requirements.txt
   ```

2. **Create Elastic Beanstalk Application**:
   - Go to AWS Elastic Beanstalk console
   - Create new application
   - Choose Python platform
   - Upload `app.zip`

3. **Configure Environment Variables**:
   - Go to Configuration > Software
   - Add environment variables:
     - `SERVICE_ACCOUNT_FILE`: Store in AWS Secrets Manager
     - `CORS_ORIGINS`: Your frontend URL
     - `LOG_LEVEL`: INFO

4. **Store Service Account in Secrets Manager**:
   ```bash
   aws secretsmanager create-secret \
     --name iso-piping/service-account \
     --secret-string file://service-account.json
   ```

5. **Update Code to Load from Secrets Manager**:
   ```python
   import boto3
   import json
   
   def get_service_account():
       client = boto3.client('secretsmanager')
       response = client.get_secret_value(SecretId='iso-piping/service-account')
       return json.loads(response['SecretString'])
   ```

#### Frontend on AWS S3 + CloudFront

1. **Build Frontend**:
   ```bash
   cd frontend
   npm run build
   ```

2. **Create S3 Bucket**:
   ```bash
   aws s3 mb s3://iso-piping-frontend
   aws s3 website s3://iso-piping-frontend \
     --index-document index.html \
     --error-document index.html
   ```

3. **Upload Build Files**:
   ```bash
   aws s3 sync dist/ s3://iso-piping-frontend --delete
   ```

4. **Create CloudFront Distribution**:
   - Go to CloudFront console
   - Create distribution
   - Origin: S3 bucket
   - Enable HTTPS
   - Configure custom domain (optional)

5. **Configure API URL**:
   - Update `.env` with API Gateway or Elastic Beanstalk URL
   - Rebuild and redeploy

---

### Option 3: Azure Deployment

#### Backend on Azure App Service

1. **Create App Service**:
   ```bash
   az group create --name iso-piping-rg --location eastus
   
   az appservice plan create \
     --name iso-piping-plan \
     --resource-group iso-piping-rg \
     --sku B1 \
     --is-linux
   
   az webapp create \
     --name iso-piping-api \
     --resource-group iso-piping-rg \
     --plan iso-piping-plan \
     --runtime "PYTHON:3.11"
   ```

2. **Deploy Code**:
   ```bash
   cd backend
   zip -r app.zip *.py requirements.txt
   az webapp deployment source config-zip \
     --resource-group iso-piping-rg \
     --name iso-piping-api \
     --src app.zip
   ```

3. **Configure App Settings**:
   ```bash
   az webapp config appsettings set \
     --resource-group iso-piping-rg \
     --name iso-piping-api \
     --settings CORS_ORIGINS=https://your-frontend.azurewebsites.net
   ```

4. **Store Service Account in Key Vault**:
   ```bash
   az keyvault create \
     --name iso-piping-kv \
     --resource-group iso-piping-rg \
     --location eastus
   
   az keyvault secret set \
     --vault-name iso-piping-kv \
     --name service-account \
     --file service-account.json
   ```

#### Frontend on Azure Static Web Apps

1. **Create Static Web App**:
   ```bash
   az staticwebapp create \
     --name iso-piping-frontend \
     --resource-group iso-piping-rg \
     --location eastus \
     --source https://github.com/YOUR-USERNAME/Processing_file_ISO_Piping \
     --branch main \
     --app-location "/frontend" \
     --api-location "" \
     --output-location "dist"
   ```

2. **Configure Environment Variables**:
   - Go to Configuration in Azure portal
   - Add `VITE_API_URL` with backend URL

---

### Option 4: Heroku Deployment

#### Backend on Heroku

1. **Create Heroku App**:
   ```bash
   heroku create iso-piping-api
   ```

2. **Add Procfile**:
   Create `backend/Procfile`:
   ```
   web: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

3. **Deploy**:
   ```bash
   cd backend
   git init
   heroku git:remote -a iso-piping-api
   git add .
   git commit -m "Deploy backend"
   git push heroku main
   ```

4. **Configure Environment Variables**:
   ```bash
   heroku config:set CORS_ORIGINS=https://your-frontend.herokuapp.com
   ```

5. **Upload Service Account**:
   ```bash
   # Store as config var
   heroku config:set SERVICE_ACCOUNT_JSON="$(cat service-account.json)"
   ```

#### Frontend on Netlify

1. **Install Netlify CLI**:
   ```bash
   npm install -g netlify-cli
   ```

2. **Build and Deploy**:
   ```bash
   cd frontend
   npm run build
   netlify deploy --prod --dir=dist
   ```

3. **Configure Environment Variables**:
   - Go to Netlify dashboard
   - Site settings > Build & deploy > Environment
   - Add `VITE_API_URL` with backend URL

---

## Environment Configuration

### Backend Environment Variables

Create `backend/.env` (never commit this file):

```bash
# Google Service Account
SERVICE_ACCOUNT_FILE=service-account.json

# CORS Configuration
CORS_ORIGINS=https://your-frontend-domain.com

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Logging
LOG_LEVEL=INFO
```

### Frontend Environment Variables

Create `frontend/.env` (never commit this file):

```bash
# API Configuration
VITE_API_URL=https://your-backend-domain.com
```

---

## Security Best Practices

### 1. Secrets Management

**Never commit secrets to version control**. Use:
- AWS Secrets Manager (AWS)
- Azure Key Vault (Azure)
- HashiCorp Vault (Self-hosted)
- Environment variables (Basic)

### 2. CORS Configuration

Update `backend/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-frontend-domain.com",
        "https://www.your-frontend-domain.com"
    ],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)
```

### 3. HTTPS

Always use HTTPS in production:
- Use Let's Encrypt for free SSL certificates
- Or use cloud provider's certificate manager
- Redirect HTTP to HTTPS

### 4. Rate Limiting

Add rate limiting to prevent abuse:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/process")
@limiter.limit("10/minute")
async def process_file(...):
    # Your code
```

### 5. File Size Limits

Configure maximum file sizes:

```python
from fastapi import File, UploadFile

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

@app.post("/process")
async def process_file(file: UploadFile = File(...)):
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large")
```

---

## Monitoring and Logging

### Application Monitoring

Use monitoring services:
- **AWS**: CloudWatch
- **Azure**: Application Insights
- **Self-hosted**: Prometheus + Grafana
- **Third-party**: Datadog, New Relic, Sentry

### Logging Configuration

Update logging in production:

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Health Checks

Add health check endpoints:

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }
```

---

## Performance Optimization

### 1. Enable Caching

Use Redis for caching:

```python
import redis
redis_client = redis.Redis(host='localhost', port=6379)

# Cache PDF text
redis_client.setex(f"pdf:{file_id}", 3600, extracted_text)
```

### 2. Async Processing

Use Celery for background jobs:

```python
from celery import Celery

celery = Celery('tasks', broker='redis://localhost:6379')

@celery.task
def process_excel_task(file_content, drive_link):
    # Process in background
    pass
```

### 3. CDN

Use CDN for frontend static assets:
- CloudFlare
- AWS CloudFront
- Azure CDN

---

## Backup and Recovery

### Database Backups

If using database for caching:
```bash
# PostgreSQL
pg_dump database_name > backup.sql

# Restore
psql database_name < backup.sql
```

### Application Backups

Backup service account credentials and environment variables securely.

---

## Troubleshooting Production Issues

### Check Logs

```bash
# Docker
docker-compose logs -f backend

# AWS
aws logs tail /aws/elasticbeanstalk/iso-piping-api

# Azure
az webapp log tail --name iso-piping-api --resource-group iso-piping-rg

# Heroku
heroku logs --tail --app iso-piping-api
```

### Common Issues

1. **CORS Errors**: Check CORS origins configuration
2. **Service Account Errors**: Verify credentials and permissions
3. **Timeout Errors**: Increase timeout limits
4. **Memory Errors**: Increase instance size or optimize caching

---

## Rollback Strategy

### Docker

```bash
# Rollback to previous version
docker-compose down
git checkout previous-commit
docker-compose up -d
```

### Cloud Platforms

Most platforms support deployment history and one-click rollback through their dashboards.

---

## Cost Optimization

### AWS
- Use spot instances for non-critical workloads
- Enable auto-scaling
- Use S3 lifecycle policies

### Azure
- Choose appropriate pricing tiers
- Enable auto-shutdown for dev environments
- Use reserved instances for production

### General
- Monitor usage and costs regularly
- Set up billing alerts
- Optimize resource allocation

---

## Support and Maintenance

- Monitor application metrics daily
- Review logs for errors weekly
- Update dependencies monthly
- Security patches: Apply immediately
- Feature updates: Test in staging first

---

For additional help, refer to:
- Main README.md for application overview
- CONTRIBUTING.md for development guidelines
- AI context files in `ai-context/` directory
