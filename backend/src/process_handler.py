import json
import os
import boto3
import uuid
from datetime import datetime
from typing import Dict, List, Any
import traceback

# AWS clients
sqs_client = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')

# Environment variables
QUEUE_URL = os.environ.get('QUEUE_URL', '')
TABLE_NAME = os.environ.get('TABLE_NAME', '')
WEBSOCKET_API_ENDPOINT = os.environ.get('WEBSOCKET_API_ENDPOINT', '')
GOOGLE_DRIVE_API_KEY = os.environ.get('GOOGLE_DRIVE_API_KEY', '')
GOOGLE_DRIVE_API_TOKEN = os.environ.get('GOOGLE_DRIVE_API_TOKEN', '')


def validate_environment_variables():
    """
    Validate required environment variables at startup.
    Note: Google Drive API credentials are optional for simulation mode.
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
    
    # Google Drive API credentials are optional for simulation mode
    if not GOOGLE_DRIVE_API_KEY or not GOOGLE_DRIVE_API_TOKEN:
        print("Info: Google Drive API credentials not set. Using simulation mode for file fetching.")
    else:
        print("Info: Google Drive API credentials configured.")


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
        file_content = body.get('file_content', '')
        target_hole_codes = body.get('target_hole_codes', [])
        
        print(f"Action: {action}, Connection: {connection_id}")
        print(f"Google Drive Link: {google_drive_link}")
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Simulate file list (replace with actual Google Drive file fetching)
        total_files = 100
        simulated_files = [
            {
                'name': f'drawing_{i}.pdf',
                'content': f'Sample content for file {i} with HOLE-{i % 10}',
                'pdf_link': f'https://drive.google.com/file/{i}'
            }
            for i in range(total_files)
        ]
        
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
        # TODO: Integrate with Google Drive API using environment variables
        # Use GOOGLE_DRIVE_API_KEY and GOOGLE_DRIVE_API_TOKEN to fetch actual files from google_drive_link
        # For now, simulating file list as placeholder
        batch_size = 10
        for batch_start_idx in range(0, len(simulated_files), batch_size):
            batch = simulated_files[batch_start_idx:batch_start_idx + batch_size]
            entries = []
            
            for idx, file_data in enumerate(batch):
                entries.append({
                    'Id': str(batch_start_idx + idx),
                    'MessageBody': json.dumps({
                        'session_id': session_id,
                        'file_name': file_data['name'],
                        'file_content': file_data['content'],
                        'pdf_link': file_data['pdf_link'],
                        'target_hole_codes': target_hole_codes
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
