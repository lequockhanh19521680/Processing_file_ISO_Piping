import json
import os
import boto3
import uuid
import re
from datetime import datetime
from typing import Dict, List, Any
import traceback
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaIoBaseDownload
import io

# AWS clients
sqs_client = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')
secretsmanager_client = boto3.client('secretsmanager')
lambda_client = boto3.client('lambda')  # Client để tự gọi lại Lambda

# Environment variables
QUEUE_URL = os.environ.get('QUEUE_URL', '')
TABLE_NAME = os.environ.get('TABLE_NAME', '')
WEBSOCKET_API_ENDPOINT = os.environ.get('WEBSOCKET_API_ENDPOINT', '')
GOOGLE_DRIVE_SECRET_ARN = os.environ.get('GOOGLE_DRIVE_SECRET_ARN', '')

# Cache for secrets to avoid repeated API calls
_secrets_cache = {}


def get_google_drive_credentials() -> Dict[str, str]:
    """
    Retrieve Google Drive API credentials from AWS Secrets Manager.
    """
    global _secrets_cache
    
    # Return cached credentials if available
    if 'google_drive' in _secrets_cache:
        return _secrets_cache['google_drive']
    
    if not GOOGLE_DRIVE_SECRET_ARN:
        print("Warning: GOOGLE_DRIVE_SECRET_ARN not set. Using simulation mode.")
        return {'access_token': '', 'refresh_token': '', 'client_id': '', 'client_secret': ''}
    
    try:
        response = secretsmanager_client.get_secret_value(SecretId=GOOGLE_DRIVE_SECRET_ARN)
        secret_data = json.loads(response['SecretString'])
        
        credentials = {
            'access_token': secret_data.get('access_token', ''),
            'refresh_token': secret_data.get('refresh_token', ''),
            'client_id': secret_data.get('client_id', ''),
            'client_secret': secret_data.get('client_secret', '')
        }
        
        # Cache the credentials
        _secrets_cache['google_drive'] = credentials
        
        print("Successfully retrieved Google Drive credentials from Secrets Manager")
        return credentials
        
    except Exception as e:
        print(f"Error retrieving Google Drive credentials: {str(e)}")
        print("Falling back to simulation mode")
        return {'access_token': '', 'refresh_token': '', 'client_id': '', 'client_secret': ''}


def validate_environment_variables():
    """
    Validate required environment variables at startup.
    """
    required_vars = {
        'QUEUE_URL': QUEUE_URL,
        'TABLE_NAME': TABLE_NAME,
        'WEBSOCKET_API_ENDPOINT': WEBSOCKET_API_ENDPOINT
    }
    
    missing = [name for name, value in required_vars.items() if not value]
    
    if missing:
        print(f"Warning: Missing required environment variables: {', '.join(missing)}")
        print("The application may not function correctly without these variables.")
    
    if not GOOGLE_DRIVE_SECRET_ARN:
        print("Info: GOOGLE_DRIVE_SECRET_ARN not set. Using simulation mode for file fetching.")
    else:
        print("Info: Google Drive API credentials will be retrieved from Secrets Manager.")


validate_environment_variables()


def extract_folder_id_from_url(drive_link: str) -> str:
    """
    Extract folder ID from Google Drive URL.
    Validates that the extracted ID matches expected Google Drive ID format.
    """
    patterns = [
        r'folders/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, drive_link)
        if match:
            folder_id = match.group(1)
            # Validate folder ID format (alphanumeric, underscore, hyphen only)
            if re.match(r'^[a-zA-Z0-9_-]+$', folder_id):
                return folder_id
    
    # If no pattern matched, return the stripped input but validate it
    folder_id = drive_link.strip()
    if re.match(r'^[a-zA-Z0-9_-]+$', folder_id):
        return folder_id
    
    # If validation fails, return empty string
    print(f"Warning: Invalid folder ID format: {drive_link}")
    return ""


def update_google_drive_credentials_in_secrets_manager(new_credentials: Dict[str, str]):
    """
    Update Google Drive credentials in AWS Secrets Manager.
    """
    global _secrets_cache
    
    if not GOOGLE_DRIVE_SECRET_ARN:
        print("Warning: GOOGLE_DRIVE_SECRET_ARN not set. Cannot update credentials.")
        return False
    
    try:
        # Update the secret in AWS Secrets Manager
        secretsmanager_client.put_secret_value(
            SecretId=GOOGLE_DRIVE_SECRET_ARN,
            SecretString=json.dumps(new_credentials)
        )
        
        # Clear the cache so next call fetches the new credentials
        _secrets_cache.pop('google_drive', None)
        
        print("Successfully updated Google Drive credentials in Secrets Manager")
        return True
        
    except Exception as e:
        print(f"Error updating Google Drive credentials in Secrets Manager: {str(e)}")
        traceback.print_exc()
        return False


def get_google_drive_service(credentials: Dict[str, str], ws_manager=None):
    """
    Create Google Drive API service client with auto-refresh capability.
    If access token is expired, automatically refreshes it and updates AWS Secrets Manager.
    """
    if not credentials.get('access_token'):
        return None
    
    try:
        # Define required scopes for Google Drive API
        scopes = ['https://www.googleapis.com/auth/drive.readonly']
        
        creds = Credentials(
            token=credentials['access_token'],
            refresh_token=credentials.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=credentials.get('client_id'),
            client_secret=credentials.get('client_secret'),
            scopes=scopes
        )
        
        # Check if token is expired and refresh if needed
        if creds.expired and creds.refresh_token:
            try:
                print("Access token is expired. Attempting to refresh...")
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                
                print("Successfully refreshed access token")
                
                # Update credentials dict with new token
                new_credentials = {
                    'access_token': creds.token,
                    'refresh_token': creds.refresh_token or credentials.get('refresh_token'),
                    'client_id': credentials.get('client_id'),
                    'client_secret': credentials.get('client_secret')
                }
                
                # Persist new credentials to AWS Secrets Manager
                update_success = update_google_drive_credentials_in_secrets_manager(new_credentials)
                
                if update_success:
                    print("Auto-refresh completed: new tokens saved to Secrets Manager")
                else:
                    print("Warning: Token refreshed but failed to save to Secrets Manager")
                    
            except Exception as refresh_error:
                error_msg = f"Failed to refresh Google Drive token: {str(refresh_error)}"
                print(error_msg)
                traceback.print_exc()
                
                # Notify client via WebSocket if available
                if ws_manager:
                    ws_manager.send_update({
                        'type': 'ERROR',
                        'message': f"Google Drive authentication failed. {error_msg}. Please re-authenticate your Google Drive account."
                    })
                
                return None
        
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"Error creating Google Drive service: {str(e)}")
        traceback.print_exc()
        return None


def fetch_files_from_google_drive_recursive(service, root_folder_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all PDF files from a Google Drive folder recursively (searching inside subfolders).
    """
    if not service:
        print("No Google Drive service available, using simulation mode")
        return []
    
    try:
        files_list = []
        folders_scanned = 0
        # Queue for folders to search, starting with root
        folders_to_search = [root_folder_id]
        
        print(f"Starting recursive scan from root folder: {root_folder_id}")

        while folders_to_search:
            current_folder_id = folders_to_search.pop(0)
            folders_scanned += 1
            page_token = None
            files_in_current_folder = 0
            subfolders_found = 0
            
            print(f"Scanning folder {folders_scanned}: {current_folder_id}")
            
            while True:
                # Query for both PDFs and sub-folders
                # Support various PDF MIME types including generic application/octet-stream
                query = f"'{current_folder_id}' in parents and (mimeType='application/pdf' or mimeType='application/vnd.google-apps.folder' or (name contains '.pdf' and mimeType='application/octet-stream')) and trashed=false"
                
                results = service.files().list(
                    q=query,
                    pageSize=1000,
                    fields="nextPageToken, files(id, name, webViewLink, mimeType)",
                    pageToken=page_token
                ).execute()
                
                items = results.get('files', [])
                print(f"  Found {len(items)} items in current page (folder: {current_folder_id})")
                
                for item in items:
                    if item.get('mimeType') == 'application/vnd.google-apps.folder':
                        # Add sub-folder to queue
                        folders_to_search.append(item['id'])
                        subfolders_found += 1
                        print(f"    Found subfolder: {item.get('name', 'Unknown')}")
                    else:
                        # Add PDF file to results
                        files_list.append(item)
                        files_in_current_folder += 1
                        print(f"    Found PDF: {item.get('name', 'Unknown')} (mime: {item.get('mimeType')})")
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            print(f"  Folder scan complete: {files_in_current_folder} PDFs, {subfolders_found} subfolders")
        
        print(f"Scan completed: {folders_scanned} folders scanned, found {len(files_list)} PDF files total")
        return files_list
        
    except Exception as e:
        print(f"Error fetching files from Google Drive: {str(e)}")
        traceback.print_exc()
        return []


def download_file_content(service, file_id: str) -> str:
    """
    Download file content from Google Drive.
    """
    if not service:
        return ""
    
    try:
        request = service.files().get_media(fileId=file_id)
        file_buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(file_buffer, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        file_buffer.seek(0)
        return file_buffer.read()
        
    except Exception as e:
        print(f"Error downloading file from Google Drive: {str(e)}")
        return ""


class WebSocketManager:
    """Manage WebSocket connections and send updates to clients"""
    
    def __init__(self, endpoint_url: str, connection_id: str):
        if endpoint_url.startswith('wss://'):
            endpoint_url = endpoint_url.replace('wss://', 'https://')
        
        self.connection_id = connection_id
        self.client = boto3.client('apigatewaymanagementapi', endpoint_url=endpoint_url)
    
    def send_update(self, data: Dict[str, Any]) -> bool:
        """Send update to the connected client via WebSocket"""
        try:
            self.client.post_to_connection(
                ConnectionId=self.connection_id,
                Data=json.dumps(data).encode('utf-8')
            )
            print(f"Sent update to connection {self.connection_id}: {data.get('type', 'UNKNOWN')}")
            return True
        except self.client.exceptions.GoneException:
            print(f"Connection {self.connection_id} is gone")
            return False
        except Exception as e:
            print(f"Error sending update: {str(e)}")
            traceback.print_exc()
            return False


def perform_scan_logic(event):
    """
    BACKGROUND TASK: Performs the heavy lifting of scanning files and sending to SQS.
    This runs asynchronously to avoid API Gateway timeout.
    """
    try:
        # Extract parameters passed from the main handler
        body = event.get('body_payload', {})
        connection_id = event.get('connection_id')
        
        if not connection_id:
            print("Error: No connection ID provided for async scan")
            return

        # Initialize WebSocket manager
        ws_manager = WebSocketManager(WEBSOCKET_API_ENDPOINT, connection_id)
        
        # Extract user parameters
        google_drive_link = body.get('drive_link', '')
        target_hole_codes = body.get('target_hole_codes', [])
        
        print(f"Async scan started for Connection: {connection_id}")
        print(f"Processing Google Drive link: {google_drive_link}")
        
        # Retrieve credentials
        credentials = get_google_drive_credentials()
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        files_list = []
        use_simulation = False
        
        # 1. Fetch files from Google Drive (Recursive)
        if credentials.get('access_token'):
            try:
                folder_id = extract_folder_id_from_url(google_drive_link)
                print(f"Extracted folder ID: {folder_id}")
                
                service = get_google_drive_service(credentials, ws_manager)
                if service:
                    # USE RECURSIVE FETCH HERE
                    files_list = fetch_files_from_google_drive_recursive(service, folder_id)
                    
                    if not files_list:
                        error_msg = (
                            f"No PDF files found in Google Drive folder (ID: {folder_id}). "
                            "Please check: (1) Folder contains PDF files, "
                            "(2) Files are not in trash, "
                            "(3) Service account has proper permissions. "
                            f"Drive link provided: {google_drive_link}"
                        )
                        print(error_msg)
                        
                        # Send error notification to client
                        ws_manager.send_update({
                            'type': 'ERROR',
                            'message': error_msg
                        })
                        return
                else:
                    print("Could not create Google Drive service, falling back to simulation")
                    use_simulation = True
            except Exception as e:
                error_msg = f"Error accessing Google Drive: {str(e)}"
                print(error_msg)
                traceback.print_exc()
                
                # Send error notification to client
                try:
                    ws_manager.send_update({
                        'type': 'ERROR',
                        'message': error_msg
                    })
                except Exception as ws_error:
                    print(f"Failed to send error to WebSocket: {str(ws_error)}")
                    
                print("Falling back to simulation mode")
                use_simulation = True
        else:
            print("No Google Drive credentials available, using simulation mode")
            use_simulation = True
        
        # Fallback to simulation if needed
        if use_simulation or (not files_list and not credentials.get('access_token')):
            print("Using simulated file list")
            total_files = 100
            files_list = [
                {
                    'id': f'sim_{i}',
                    'name': f'drawing_{i}.pdf',
                    'webViewLink': f'https://drive.google.com/file/d/sim_{i}/view'
                }
                for i in range(total_files)
            ]
        
        total_files = len(files_list)
        
        # 2. Store session metadata in DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(
            Item={
                'session_id': session_id,
                'file_name': 'meta',
                'connection_id': connection_id,
                'total_files': total_files,
                'processed_count': 0,
                'target_hole_codes': target_hole_codes,
                'google_drive_link': google_drive_link,
                'timestamp': datetime.now().isoformat(),
                'status': 'IN_PROGRESS'
            }
        )
        
        # 3. Batch send file metadata to SQS
        batch_size = 10
        total_sent = 0
        for batch_start_idx in range(0, len(files_list), batch_size):
            batch = files_list[batch_start_idx:batch_start_idx + batch_size]
            entries = []
            
            for idx, file_data in enumerate(batch):
                file_id = file_data.get('id', '')
                file_name = file_data.get('name', '')
                pdf_link = file_data.get('webViewLink', '')
                
                entries.append({
                    'Id': str(batch_start_idx + idx),
                    'MessageBody': json.dumps({
                        'session_id': session_id,
                        'file_id': file_id,
                        'file_name': file_name,
                        'pdf_link': pdf_link,
                        'target_hole_codes': target_hole_codes,
                        'use_simulation': use_simulation
                    })
                })
            
            # Send batch to SQS
            if entries:
                try:
                    response = sqs_client.send_message_batch(
                        QueueUrl=QUEUE_URL,
                        Entries=entries
                    )
                    total_sent += len(entries)
                    
                    # Log any failures
                    if response.get('Failed'):
                        print(f"Warning: {len(response['Failed'])} messages failed to send in batch")
                        for failed in response['Failed']:
                            print(f"  Failed message {failed['Id']}: {failed['Message']}")
                    
                    # Print progress every 100 files
                    if total_sent > 0 and (total_sent % 100 == 0 or total_sent == len(files_list)):
                        print(f"Sent {total_sent}/{len(files_list)} files to SQS queue")
                        
                except Exception as e:
                    print(f"Error sending batch to SQS: {str(e)}")
                    traceback.print_exc()
        
        print(f"Dispatched {total_sent} files to SQS for session {session_id}")
        
        # 4. Notify Client via WebSocket
        ws_manager.send_update({
            'type': 'STARTED',
            'message': f'Scanning completed. Found {total_files} files. Processing started.',
            'session_id': session_id,
            'total_files': total_files,
            'timestamp': datetime.now().isoformat()
        })
        
        print(f"Successfully started processing session {session_id} with {total_files} files")
        
    except Exception as e:
        error_message = f"Error in async scan logic: {str(e)}"
        print(error_message)
        traceback.print_exc()
        
        # Try to send error to client
        try:
            if 'ws_manager' in locals():
                ws_manager.send_update({
                    'type': 'ERROR',
                    'message': error_message
                })
        except:
            pass


def handle_reconnect_action(session_id: str, connection_id: str):
    """
    Handle reconnect action: fetch session state from DynamoDB and send back to client.
    """
    try:
        print(f"Handling reconnect for session {session_id}, connection {connection_id}")
        
        # Initialize WebSocket manager
        ws_manager = WebSocketManager(WEBSOCKET_API_ENDPOINT, connection_id)
        
        # Fetch session metadata from DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        
        # Get the meta item for this session
        response = table.get_item(
            Key={
                'session_id': session_id,
                'file_name': 'meta'
            }
        )
        
        if 'Item' not in response:
            print(f"Session {session_id} not found in DynamoDB")
            ws_manager.send_update({
                'type': 'ERROR',
                'message': f'Session {session_id} not found. It may have expired or does not exist.'
            })
            return
        
        session_meta = response['Item']
        
        # Fetch all results (matches) for this session
        results_response = table.query(
            KeyConditionExpression='session_id = :sid',
            FilterExpression='file_name <> :meta',
            ExpressionAttributeValues={
                ':sid': session_id,
                ':meta': 'meta'
            }
        )
        
        results = results_response.get('Items', [])
        
        # Calculate current progress
        total_files = int(session_meta.get('total_files', 0))
        processed_count = int(session_meta.get('processed_count', 0))
        progress = int((processed_count / total_files * 100)) if total_files > 0 else 0
        
        # Prepare results data
        results_data = []
        for item in results:
            results_data.append({
                'hole_code': item.get('hole_code', ''),
                'file_name': item.get('file_name', ''),
                'status': item.get('status', ''),
                'pdf_link': item.get('pdf_link', ''),
                'timestamp': item.get('timestamp', '')
            })
        
        # Send SYNC_STATE message to client
        sync_state = {
            'type': 'SYNC_STATE',
            'message': 'State synchronized from server',
            'session_id': session_id,
            'total_files': total_files,
            'processed_count': processed_count,
            'progress': progress,
            'results': results_data,
            'status': session_meta.get('status', 'IN_PROGRESS'),
            'drive_link': session_meta.get('google_drive_link', ''),
            'timestamp': datetime.now().isoformat()
        }
        
        ws_manager.send_update(sync_state)
        
        print(f"Successfully sent SYNC_STATE for session {session_id}: {processed_count}/{total_files} files")
        
    except Exception as e:
        error_message = f"Error handling reconnect: {str(e)}"
        print(error_message)
        traceback.print_exc()
        
        # Try to send error to client
        try:
            if 'ws_manager' in locals():
                ws_manager.send_update({
                    'type': 'ERROR',
                    'message': error_message
                })
        except:
            pass


def handler(event, context):
    """
    Main Lambda Handler (Dispatcher).
    Handles two types of events:
    1. WebSocket requests (via API Gateway) -> Triggers Async Invocation
    2. Async Invocations (Self-triggered) -> Executes perform_scan_logic
    """
    print(f"Received event: {json.dumps(event)}")
    
    # --- CASE 1: Async Execution (Self-triggered) ---
    if event.get('is_async_scan'):
        print("Executing async scan logic...")
        perform_scan_logic(event)
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Async scan completed'})
        }

    # --- CASE 2: WebSocket Request (API Gateway) ---
    try:
        request_context = event.get('requestContext', {})
        connection_id = request_context.get('connectionId')
        
        if not connection_id:
            print("No connection ID found in event")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No connection ID'})
            }
        
        # Parse body
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)
            
        action = body.get('action', '')
        
        # Handle different actions
        if action == 'reconnect':
            # Handle reconnect action
            session_id = body.get('session_id', '')
            
            if not session_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'session_id is required for reconnect action'})
                }
            
            print(f"Received reconnect request for session {session_id}, connection {connection_id}")
            
            # Handle reconnect in the same invocation (it's a fast operation)
            handle_reconnect_action(session_id, connection_id)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Reconnect request processed',
                    'session_id': session_id
                })
            }
            
        elif action == 'start_scan':
            # Handle start_scan action
            print(f"Received scan request for Connection: {connection_id}. Invoking async worker.")

            # Invoke self asynchronously
            # This returns immediately so API Gateway doesn't timeout
            lambda_client.invoke(
                FunctionName=context.function_name,
                InvocationType='Event',  # 'Event' = Async
                Payload=json.dumps({
                    'is_async_scan': True,
                    'body_payload': body,
                    'connection_id': connection_id,
                    'requestContext': request_context # Pass context if needed
                })
            )
            
            # Return success immediately to the client
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Scan request accepted. Processing in background.',
                    'status': 'ACCEPTED'
                })
            }
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid action. Supported actions: start_scan, reconnect'})
            }
        
    except Exception as e:
        error_message = f"Error in dispatcher: {str(e)}"
        print(error_message)
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }