import json
import os
import boto3
import re
from datetime import datetime
from typing import Dict, List, Any
import traceback
from openpyxl import Workbook

# AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Environment variables
TABLE_NAME = os.environ.get('TABLE_NAME', '')
RESULTS_BUCKET = os.environ.get('RESULTS_BUCKET', '')
WEBSOCKET_API_ENDPOINT = os.environ.get('WEBSOCKET_API_ENDPOINT', '')


class WebSocketManager:
    """Manage WebSocket connections and send updates to clients"""
    
    def __init__(self, endpoint_url: str, connection_id: str):
        # Extract the API Gateway endpoint from WebSocket URL
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
    """Extract hole codes from text"""
    hole_codes = re.findall(r'\b(?:HOLE|HC)-\d+\b', text, re.IGNORECASE)
    return hole_codes


def process_single_file(file_name: str, file_content: str, target_hole_codes: List[str]) -> Dict[str, Any]:
    """Process a single file and check for hole code matches"""
    # Simulate text extraction (in real scenario, use Textract for PDFs)
    found_hole_codes = extract_hole_codes_from_text(file_content)
    
    # Check for matches with target hole codes
    matches = [code for code in found_hole_codes if code in target_hole_codes]
    
    result = {
        'file_name': file_name,
        'found_codes': matches,
        'status': f"{len(matches)} Code{'s' if len(matches) != 1 else ''}" if matches else "No Match"
    }
    
    return result


def generate_excel_report(session_id: str, bucket: str) -> str:
    """Generate Excel report from DynamoDB results and upload to S3"""
    try:
        table = dynamodb.Table(TABLE_NAME)
        
        # Query all items for this session
        response = table.query(
            KeyConditionExpression='session_id = :sid',
            ExpressionAttributeValues={':sid': session_id}
        )
        
        items = response.get('Items', [])
        
        # Filter out metadata item and only get actual file results
        results = [item for item in items if item.get('file_name') != 'meta' and item.get('found_codes')]
        
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
        file_name = f'results_{session_id}_{timestamp}.xlsx'
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
    """Worker Lambda handler - processes files from SQS"""
    print(f"Received SQS event with {len(event.get('Records', []))} records")
    
    table = dynamodb.Table(TABLE_NAME)
    
    try:
        # Process each SQS message
        for record in event.get('Records', []):
            message_body = json.loads(record['body'])
            
            session_id = message_body['session_id']
            file_name = message_body['file_name']
            file_content = message_body['file_content']
            pdf_link = message_body['pdf_link']
            target_hole_codes = message_body['target_hole_codes']
            
            print(f"Processing file: {file_name} for session: {session_id}")
            
            # Process the file
            result = process_single_file(file_name, file_content, target_hole_codes)
            
            # Write result to DynamoDB
            table.put_item(
                Item={
                    'session_id': session_id,
                    'file_name': file_name,
                    'status': result['status'],
                    'found_codes': result['found_codes'],
                    'pdf_link': pdf_link,
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            # Atomically increment processed_count in meta item
            response = table.update_item(
                Key={'session_id': session_id, 'file_name': 'meta'},
                UpdateExpression='SET processed_count = processed_count + :inc',
                ExpressionAttributeValues={':inc': 1},
                ReturnValues='ALL_NEW'
            )
            
            meta = response['Attributes']
            connection_id = meta.get('connection_id')
            total_files = meta.get('total_files')
            processed_count = int(meta.get('processed_count', 0))
            
            # Send progress update via WebSocket
            if connection_id and WEBSOCKET_API_ENDPOINT:
                ws_manager = WebSocketManager(WEBSOCKET_API_ENDPOINT, connection_id)
                
                # If match found, send immediate notification
                if result['found_codes']:
                    ws_manager.send_update({
                        'type': 'MATCH_FOUND',
                        'data': {
                            'hole_code': ', '.join(result['found_codes']),
                            'file_name': file_name,
                            'status': result['status'],
                            'pdf_link': pdf_link
                        }
                    })
                
                # Send progress update
                progress = min(100, int((processed_count / total_files) * 100)) if total_files > 0 else 0
                ws_manager.send_update({
                    'type': 'PROGRESS',
                    'value': progress,
                    'processed': processed_count,
                    'total': total_files
                })
                
                # Check if processing is complete
                if processed_count >= total_files:
                    print(f"Processing complete for session {session_id}. Generating report...")
                    
                    # Generate Excel report
                    download_url = generate_excel_report(session_id, RESULTS_BUCKET)
                    
                    # Query to count matches
                    query_response = table.query(
                        KeyConditionExpression='session_id = :sid',
                        ExpressionAttributeValues={':sid': session_id}
                    )
                    
                    matches = [item for item in query_response.get('Items', []) 
                              if item.get('file_name') != 'meta' and item.get('found_codes')]
                    
                    # Send completion message
                    ws_manager.send_update({
                        'type': 'COMPLETE',
                        'download_url': download_url,
                        'total_matches': len(matches),
                        'total_processed': total_files,
                        'message': 'Processing completed successfully'
                    })
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Worker processed successfully'})
        }
        
    except Exception as e:
        error_message = f"Error in worker: {str(e)}"
        print(error_message)
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
