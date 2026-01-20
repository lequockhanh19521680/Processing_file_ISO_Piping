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
    
    Returns:
        Dictionary containing 'access_token' and 'refresh_token'
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
    
    This function checks for required AWS environment variables and prints warnings
    if they are missing. Google Drive API credentials are optional for simulation mode.
    
    Note: This function does not halt execution, it only logs warnings.
    The application will still start but may not function correctly without required variables.
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
    
    # Check if Google Drive Secret ARN is configured
    if not GOOGLE_DRIVE_SECRET_ARN:
        print("Info: GOOGLE_DRIVE_SECRET_ARN not set. Using simulation mode for file fetching.")
    else:
        print("Info: Google Drive API credentials will be retrieved from Secrets Manager.")


validate_environment_variables()


def extract_folder_id_from_url(drive_link: str) -> str:
    """
    Extract folder ID from Google Drive URL.
    Supports formats:
    - https://drive.google.com/drive/folders/FOLDER_ID
    - https://drive.google.com/drive/folders/FOLDER_ID?usp=sharing
    """
    patterns = [
        r'folders/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, drive_link)
        if match:
            return match.group(1)
    
    # If no pattern matches, assume the link itself is the folder ID
    return drive_link.strip()


def get_google_drive_service(credentials: Dict[str, str]):
    """
    Create Google Drive API service client.
    """
    if not credentials.get('access_token'):
        return None
    
    try:
        # Define required scopes for Google Drive API
        # https://www.googleapis.com/auth/drive.readonly - Read-only access to files and metadata
        scopes = ['https://www.googleapis.com/auth/drive.readonly']
        
        # Create credentials object with required scopes
        creds = Credentials(
            token=credentials['access_token'],
            refresh_token=credentials.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=credentials.get('client_id'),
            client_secret=credentials.get('client_secret'),
            scopes=scopes
        )
        
        # Build the Drive API service
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"Error creating Google Drive service: {str(e)}")
        return None


def fetch_files_from_google_drive(service, folder_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all PDF files from a Google Drive folder.
    
    Args:
        service: Google Drive API service
        folder_id: The ID of the folder to fetch files from
    
    Returns:
        List of file metadata dictionaries
    """
    if not service:
        print("No Google Drive service available, using simulation mode")
        return []
    
    try:
        files_list = []
        page_token = None
        
        while True:
            # Query for PDF files in the folder
            query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
            results = service.files().list(
                q=query,
                pageSize=100,
                fields="nextPageToken, files(id, name, webViewLink)",
                pageToken=page_token
            ).execute()
            
            items = results.get('files', [])
            files_list.extend(items)
            
            page_token = results.get('nextPageToken')
            if not page_token:
                break
        
        print(f"Found {len(files_list)} PDF files in Google Drive folder")
        return files_list
        
    except Exception as e:
        print(f"Error fetching files from Google Drive: {str(e)}")
        traceback.print_exc()
        return []


def download_file_content(service, file_id: str) -> str:
    """
    Download file content from Google Drive.
    Returns file content as string (for text extraction).
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
        
        # Return the content as bytes (will be processed by Textract later)
        file_buffer.seek(0)
        return file_buffer.read()
        
    except Exception as e:
        print(f"Error downloading file from Google Drive: {str(e)}")
        return ""


# Validate environment on module load
validate_environment_variables()


class WebSocketManager:
    """Manage WebSocket connections and send updates to clients"""
    
    def __init__(self, endpoint_url: str, connection_id: str):
        # Extract the API Gateway endpoint from WebSocket URL
        # Format: wss://xxxxx.execute-api.region.amazonaws.com/prod
        # We need: https://xxxxx.execute-api.region.amazonaws.com/prod
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


def handler(event, context):
    """Dispatcher Lambda handler - sends files to SQS for processing"""
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract connection ID from WebSocket event
        request_context = event.get('requestContext', {})
        connection_id = request_context.get('connectionId')
        
        if not connection_id:
            print("No connection ID found in event")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No connection ID'})
            }
        
        # Initialize WebSocket manager
        ws_manager = WebSocketManager(WEBSOCKET_API_ENDPOINT, connection_id)
        
        # Parse the body of the WebSocket message
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)
        
        # Extract parameters
        action = body.get('action', '')
        google_drive_link = body.get('drive_link', '')
        target_hole_codes = body.get('target_hole_codes', [])
        
        print(f"Action: {action}, Connection: {connection_id}")
        print(f"Received Google Drive link for processing: {google_drive_link}")
        
        # Retrieve Google Drive credentials from Secrets Manager
        credentials = get_google_drive_credentials()
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Try to fetch files from Google Drive
        files_list = []
        use_simulation = False
        
        if credentials.get('access_token'):
            # Real Google Drive integration
            try:
                folder_id = extract_folder_id_from_url(google_drive_link)
                print(f"Extracted folder ID: {folder_id}")
                
                service = get_google_drive_service(credentials)
                if service:
                    files_list = fetch_files_from_google_drive(service, folder_id)
                    
                    if not files_list:
                        print("No files found in Google Drive folder, falling back to simulation")
                        use_simulation = True
                else:
                    print("Could not create Google Drive service, falling back to simulation")
                    use_simulation = True
            except Exception as e:
                print(f"Error accessing Google Drive: {str(e)}")
                print("Falling back to simulation mode")
                use_simulation = True
        else:
            print("No Google Drive credentials available, using simulation mode")
            use_simulation = True
        
        # Fallback to simulation if needed
        if use_simulation or not files_list:
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
        
        # Store session metadata in DynamoDB
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
                'timestamp': datetime.now().isoformat()
            }
        )
        
        # Batch send file metadata to SQS
        # Files are now fetched from Google Drive API
        batch_size = 10
        for batch_start_idx in range(0, len(files_list), batch_size):
            batch = files_list[batch_start_idx:batch_start_idx + batch_size]
            entries = []
            
            for idx, file_data in enumerate(batch):
                # For real Google Drive files
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
            sqs_client.send_message_batch(
                QueueUrl=QUEUE_URL,
                Entries=entries
            )
        
        print(f"Dispatched {total_files} files to SQS for session {session_id}")
        
        # Send STARTED message
        ws_manager.send_update({
            'type': 'STARTED',
            'message': 'Processing started',
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Processing started',
                'session_id': session_id
            })
        }
        
    except Exception as e:
        error_message = f"Error in dispatcher: {str(e)}"
        print(error_message)
        traceback.print_exc()
        
        # Try to send error message via WebSocket if possible
        try:
            if connection_id and WEBSOCKET_API_ENDPOINT:
                ws_manager = WebSocketManager(WEBSOCKET_API_ENDPOINT, connection_id)
                ws_manager.send_update({
                    'type': 'ERROR',
                    'message': error_message
                })
        except:
            pass
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
