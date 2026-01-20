# Google Drive API Setup Guide

## Problem Fixed
The application was encountering a 403 "insufficient authentication scopes" error when trying to access Google Drive files. This has been fixed by adding the required scope in the code.

## Required OAuth Scope
The application now requires the following OAuth scope when generating credentials:
- `https://www.googleapis.com/auth/drive.readonly` - Read-only access to files and metadata

## Important: Regenerate Your OAuth Tokens
**If you already have OAuth tokens stored in AWS Secrets Manager, you MUST regenerate them with the correct scope.**

### Steps to Regenerate OAuth Tokens

#### Option 1: Using Google OAuth 2.0 Playground
1. Go to [Google OAuth 2.0 Playground](https://developers.google.com/oauthplayground/)
2. Click the gear icon (⚙️) in the top right
3. Check "Use your own OAuth credentials"
4. Enter your OAuth Client ID and Client Secret from Google Cloud Console
5. In "Step 1 - Select & authorize APIs", find and select:
   - `https://www.googleapis.com/auth/drive.readonly`
6. Click "Authorize APIs"
7. Sign in with your Google account and grant permissions
8. In "Step 2 - Exchange authorization code for tokens", click "Exchange authorization code for tokens"
9. Copy the `access_token` and `refresh_token`

#### Option 2: Using Google Cloud Console
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select your project
3. Enable Google Drive API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
5. Download the credentials JSON file
6. Use a tool like `google-auth-oauthlib` to generate tokens with the correct scope:

```python
from google_auth_oauthlib.flow import Flow

# Create flow with the correct scope
flow = Flow.from_client_secrets_file(
    'credentials.json',
    scopes=['https://www.googleapis.com/auth/drive.readonly']
)

# Follow the authorization flow
# This will give you access_token and refresh_token
```

### Update AWS Secrets Manager
After generating new tokens with the correct scope, update your AWS Secrets Manager secret with:

```json
{
  "access_token": "ya29.xxx...",
  "refresh_token": "1//xxx...",
  "client_id": "xxx.apps.googleusercontent.com",
  "client_secret": "xxx"
}
```

You can update the secret using AWS CLI:
```bash
aws secretsmanager update-secret \
  --secret-id <YOUR_SECRET_ARN> \
  --secret-string '{"access_token":"...","refresh_token":"...","client_id":"...","client_secret":"..."}'
```

Or use the AWS Console:
1. Go to AWS Secrets Manager
2. Find your secret (the ARN stored in `GOOGLE_DRIVE_SECRET_ARN` environment variable)
3. Click "Retrieve secret value" → "Edit"
4. Update the JSON with new tokens
5. Save

## Verification
After updating the tokens, test the integration:
1. Deploy your Lambda function with the updated code
2. Try accessing a Google Drive folder
3. Check CloudWatch logs - you should no longer see the 403 error
4. The logs should show: "Found X PDF files in Google Drive folder"

## Troubleshooting

### Still Getting 403 Error?
- Verify the scope is correct in the OAuth token generation
- Make sure you authorized the correct Google account (the one that has access to the Drive folder)
- Check that the folder ID is correct
- Ensure the folder is shared with the authenticated Google account

### Token Expired?
If you see token expiration errors, the `refresh_token` will automatically be used to get a new `access_token`. Make sure your `refresh_token` is valid and includes the correct scope.

### Need Additional Permissions?
If you need to download files (not just list them), you may need additional scopes:
- `https://www.googleapis.com/auth/drive` - Full access to Drive (not recommended for production)
- `https://www.googleapis.com/auth/drive.file` - Per-file access to files created by the app

The current implementation uses `drive.readonly` which is sufficient for listing and reading files.

## Security Notes
- Never commit OAuth tokens to version control
- Always store tokens in AWS Secrets Manager or similar secure storage
- Use the most restrictive scope that meets your needs (readonly is better than full access)
- Rotate tokens periodically for security
- Consider using service accounts instead of user OAuth tokens for production deployments

## References
- [Google Drive API Scopes](https://developers.google.com/drive/api/guides/api-specific-auth)
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
