# Debugging Guide for Google Drive File Scanning

## Issue Fixed: "Found 0 files" Problem

### Root Causes Identified:

1. **Restrictive MIME Type Query**: The original query only searched for exact `application/pdf` MIME type
2. **Missing Error Feedback**: When no files were found, users didn't know why
3. **Insufficient Logging**: Hard to debug where files went missing

### Changes Made:

#### 1. Enhanced PDF Detection (process_handler.py, line 164)

**Before:**
```python
query = f"'{current_folder_id}' in parents and (mimeType='application/pdf' or mimeType='application/vnd.google-apps.folder') and trashed=false"
```

**After:**
```python
query = f"'{current_folder_id}' in parents and (mimeType='application/pdf' or mimeType='application/vnd.google-apps.folder' or (name contains '.pdf' and mimeType='application/octet-stream')) and trashed=false"
```

**Why this helps:**
- Some PDF files in Google Drive are stored with generic `application/octet-stream` MIME type
- The new query catches PDFs by both MIME type AND file extension
- This is especially common for uploaded PDFs vs Google-generated PDFs

#### 2. Comprehensive Logging

Added logging at every step:
- Each folder being scanned
- Each file and subfolder found
- Summary after each folder scan
- Progress updates during SQS batch sending

**Example output:**
```
Starting recursive scan from root folder: 1MnsVB49KF6A61JsY70vyVSAIJudTquM3
Scanning folder 1: 1MnsVB49KF6A61JsY70vyVSAIJudTquM3
  Found 5 items in current page (folder: 1MnsVB49KF6A61JsY70vyVSAIJudTquM3)
    Found subfolder: Drawings_Batch_1
    Found PDF: ISO-001.pdf (mime: application/pdf)
    Found PDF: ISO-002.pdf (mime: application/octet-stream)
  Folder scan complete: 2 PDFs, 1 subfolders
Scanning folder 2: <subfolder_id>
  Found 3 items in current page (folder: <subfolder_id>)
    Found PDF: ISO-003.pdf (mime: application/pdf)
    Found PDF: ISO-004.pdf (mime: application/pdf)
  Folder scan complete: 2 PDFs, 0 subfolders
Scan completed: 2 folders scanned, found 4 PDF files total
```

#### 3. Better Error Messages

**When no files are found:**
```
No PDF files found in Google Drive folder (ID: 1MnsVB49KF6A61JsY70vyVSAIJudTquM3). 
Please check: 
(1) Folder contains PDF files, 
(2) Files are not in trash, 
(3) Service account has proper permissions. 
Drive link provided: https://drive.google.com/drive/folders/1MnsVB49KF6A61JsY70vyVSAIJudTquM3
```

This error is also sent to the frontend via WebSocket so users see it immediately.

#### 4. Optimized Batch Processing

- Progress tracking during SQS batch sending
- Error logging for failed SQS messages
- Progress output every 100 files for large datasets

## How to Verify the Fix

### Step 1: Check CloudWatch Logs

After running a scan, check Lambda CloudWatch logs for:

1. **Look for folder scanning logs:**
   ```
   Scanning folder 1: <folder_id>
   Found <N> items in current page
   ```

2. **Verify files are being found:**
   ```
   Found PDF: <filename>.pdf (mime: application/pdf)
   ```

3. **Check final summary:**
   ```
   Scan completed: X folders scanned, found Y PDF files total
   ```

### Step 2: Test with Known Folder

1. Create a test Google Drive folder with 1-2 PDF files
2. Share it with your service account email
3. Run the scan and check the logs

### Step 3: Verify Permissions

Ensure your Google Drive service account has:
- `https://www.googleapis.com/auth/drive.readonly` scope
- Permission to access the target folder (shared or owned by service account)

### Common Issues & Solutions

#### Issue: Still seeing "0 files"

**Possible causes:**

1. **Service account doesn't have access to folder**
   - Solution: Share the folder with the service account email
   - Check: Look for "Error fetching files from Google Drive" in logs

2. **Files are in trash**
   - Solution: Restore files from trash
   - The query includes `trashed=false`

3. **No PDF files in folder**
   - Solution: Ensure folder contains `.pdf` files
   - Check subfolders - the scan is recursive

4. **Invalid folder ID**
   - Solution: Verify the Google Drive link format
   - Should be: `https://drive.google.com/drive/folders/FOLDER_ID`

#### Issue: Slow performance with 6600 files

**Optimizations already applied:**
- Batch size of 10 messages per SQS batch
- PageSize of 1000 items per Google Drive API call
- Progress tracking to avoid repeated API calls

**Additional tips:**
- Consider increasing Lambda memory (faster CPU)
- Monitor Google Drive API quota
- Check SQS queue depth in CloudWatch

## Testing Checklist

- [ ] Test with 1 file in root folder
- [ ] Test with files in nested subfolders
- [ ] Test with mixed MIME types (native PDF and uploaded PDF)
- [ ] Test with empty folder (should show error)
- [ ] Test with 100+ files for performance
- [ ] Verify CloudWatch logs show file scanning progress
- [ ] Verify frontend receives file count in STARTED message
- [ ] Verify error messages appear in frontend when no files found

## Performance Metrics

### Expected Performance (6600 files):

- **Scanning phase**: 10-30 seconds (depends on folder structure)
- **SQS dispatch**: 5-10 seconds
- **Processing phase**: 10-15 minutes (parallel workers)
- **Total time**: ~15-20 minutes for 6600 files

### Bottlenecks to watch:

1. **Google Drive API rate limits**: 1000 queries per 100 seconds per user
2. **Lambda concurrency**: Default 1000, may need increase for large batches
3. **DynamoDB write capacity**: On-demand scales automatically
4. **SQS message processing**: 10 workers can process ~120 files/minute

## Debugging Commands

### View Lambda logs:
```bash
aws logs tail /aws/lambda/ProcessingStack-ScanDispatcher --follow
aws logs tail /aws/lambda/ProcessingStack-ScanWorker --follow
```

### Check SQS queue depth:
```bash
aws sqs get-queue-attributes \
  --queue-url <QUEUE_URL> \
  --attribute-names ApproximateNumberOfMessages
```

### Query DynamoDB session:
```bash
aws dynamodb query \
  --table-name ProcessingStack-ResultsTable \
  --key-condition-expression "session_id = :sid" \
  --expression-attribute-values '{":sid":{"S":"<session_id>"}}'
```

## Next Steps

After verifying the fix works:

1. **Monitor first production run** with CloudWatch
2. **Verify file count** matches expectation
3. **Check processing time** for 6600 files
4. **Optimize if needed** (increase Lambda memory, adjust batch sizes)
5. **Set up CloudWatch alarms** for errors and performance

## Contact

If issues persist, check:
1. Lambda CloudWatch logs for detailed error messages
2. Google Drive API quota usage in Google Cloud Console
3. IAM permissions for Lambda execution roles
