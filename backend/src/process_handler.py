import json
import os
import boto3
import time
from datetime import datetime
from typing import Dict, List, Any
import traceback

# AWS clients
s3_client = boto3.client('s3')
textract_client = boto3.client('textract')

# Environment variables
RESULTS_BUCKET = os.environ.get('RESULTS_BUCKET', '')
WEBSOCKET_API_ENDPOINT = os.environ.get('WEBSOCKET_API_ENDPOINT', '')


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


def extract_hole_codes_from_text(text: str) -> List[str]:
    """Extract hole codes from text (simplified logic - customize as needed)"""
    # Example: Looking for patterns like "HOLE-123", "HC-456", etc.
    # This is a placeholder - customize based on your actual hole code format
    import re
    hole_codes = re.findall(r'\b(?:HOLE|HC)-\d+\b', text, re.IGNORECASE)
    return hole_codes


def process_single_file(file_data: Dict[str, Any], target_hole_codes: List[str]) -> Dict[str, Any]:
    """Process a single file and check for hole code matches"""
    file_name = file_data.get('name', 'unknown')
    file_content = file_data.get('content', '')
    
    # Simulate text extraction (in real scenario, use Textract for PDFs)
    # For now, we'll use simple text search
    found_hole_codes = extract_hole_codes_from_text(file_content)
    
    # Check for matches with target hole codes
    matches = [code for code in found_hole_codes if code in target_hole_codes]
    
    result = {
        'file_name': file_name,
        'found_codes': matches,
        'status': f"{len(matches)} Code{'s' if len(matches) != 1 else ''}" if matches else "No Match"
    }
    
    return result


def generate_excel_report(results: List[Dict[str, Any]], bucket: str) -> str:
    """Generate Excel report and upload to S3"""
    try:
        from openpyxl import Workbook
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Processing Results"
        
        # Headers
        ws.append(['File Name', 'Hole Codes Found', 'Status', 'PDF Link'])
        
        # Data
        for result in results:
            hole_codes = ', '.join(result.get('found_codes', []))
            ws.append([
                result.get('file_name', ''),
                hole_codes,
                result.get('status', ''),
                result.get('pdf_link', '')
            ])
        
        # Save to temporary file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_name = f'results_{timestamp}.xlsx'
        temp_path = f'/tmp/{file_name}'
        wb.save(temp_path)
        
        # Upload to S3
        s3_key = f'reports/{file_name}'
        s3_client.upload_file(temp_path, bucket, s3_key)
        
        # Generate presigned URL (valid for 1 hour)
        download_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': s3_key},
            ExpiresIn=3600
        )
        
        print(f"Excel report generated and uploaded: {s3_key}")
        return download_url
        
    except Exception as e:
        print(f"Error generating Excel report: {str(e)}")
        traceback.print_exc()
        return ""


def handler(event, context):
    """Main Lambda handler for WebSocket events"""
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
        google_drive_token = body.get('token', '')
        file_content = body.get('file_content', '')
        target_hole_codes = body.get('target_hole_codes', [])
        
        print(f"Action: {action}, Connection: {connection_id}")
        
        # Send initial acknowledgment
        ws_manager.send_update({
            'type': 'STARTED',
            'message': 'Processing started',
            'timestamp': datetime.now().isoformat()
        })
        
        # Simulate processing multiple files
        # In real scenario, you would:
        # 1. Use google_drive_token to access Google Drive API
        # 2. List files from the drive
        # 3. Process each file with Textract
        
        # For demonstration, simulate processing 100 files (instead of 6600)
        total_files = 100
        results = []
        
        # Simulate files data (replace with actual Google Drive file fetching)
        simulated_files = [
            {
                'name': f'drawing_{i}.pdf',
                'content': f'Sample content for file {i} with HOLE-{i % 10}',
                'pdf_link': f'https://drive.google.com/file/{i}'
            }
            for i in range(total_files)
        ]
        
        # Process files in batches
        batch_size = 10
        for i in range(0, total_files, batch_size):
            batch = simulated_files[i:i + batch_size]
            
            for file_data in batch:
                # Process the file
                result = process_single_file(file_data, target_hole_codes)
                result['pdf_link'] = file_data.get('pdf_link', '')
                
                # If match found, send immediate update
                if result.get('found_codes'):
                    ws_manager.send_update({
                        'type': 'MATCH_FOUND',
                        'data': {
                            'hole_code': ', '.join(result['found_codes']),
                            'file_name': result['file_name'],
                            'status': result['status'],
                            'pdf_link': result['pdf_link']
                        }
                    })
                    results.append(result)
                
                # Small delay to simulate processing time
                time.sleep(0.05)
            
            # Send progress update after each batch
            progress = min(100, int((i + batch_size) / total_files * 100))
            ws_manager.send_update({
                'type': 'PROGRESS',
                'value': progress,
                'processed': min(i + batch_size, total_files),
                'total': total_files
            })
            
            print(f"Processed {min(i + batch_size, total_files)}/{total_files} files ({progress}%)")
        
        # Generate Excel report
        print("Generating Excel report...")
        download_url = generate_excel_report(results, RESULTS_BUCKET)
        
        # Send completion message
        ws_manager.send_update({
            'type': 'COMPLETE',
            'download_url': download_url,
            'total_matches': len(results),
            'total_processed': total_files,
            'message': 'Processing completed successfully'
        })
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Processing completed'})
        }
        
    except Exception as e:
        error_message = f"Error in handler: {str(e)}"
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
