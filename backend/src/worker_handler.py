import json
import os
import boto3
import re
import io
from datetime import datetime
from typing import Dict, List, Any
import traceback
from openpyxl import Workbook
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaIoBaseDownload
from pypdf import PdfReader
from decimal import Decimal  # <--- QUAN TRỌNG: Import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
secretsmanager_client = boto3.client('secretsmanager')

# Environment variables
TABLE_NAME = os.environ.get('TABLE_NAME', '')
RESULTS_BUCKET = os.environ.get('RESULTS_BUCKET', '')
WEBSOCKET_API_ENDPOINT = os.environ.get('WEBSOCKET_API_ENDPOINT', '')
GOOGLE_DRIVE_SECRET_ARN = os.environ.get('GOOGLE_DRIVE_SECRET_ARN', '')

# Cache for secrets to avoid repeated API calls
_secrets_cache = {}
# Cache for Google Drive service to reuse across invocations
_drive_service_cache = None

# --- CLASS XỬ LÝ LỖI DECIMAL (FIX LỖI JSON SERIALIZABLE) ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Nếu là số nguyên (ví dụ 5.0) thì trả về int, ngược lại float
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)
# -----------------------------------------------------------

def get_google_drive_credentials() -> Dict[str, str]:
    """
    Retrieve Google Drive API credentials from AWS Secrets Manager.
    """
    global _secrets_cache
    
    # Return cached credentials if available
    if 'google_drive' in _secrets_cache:
        return _secrets_cache['google_drive']
    
    if not GOOGLE_DRIVE_SECRET_ARN:
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
        
        return credentials
        
    except Exception as e:
        print(f"Error retrieving Google Drive credentials: {str(e)}")
        return {'access_token': '', 'refresh_token': '', 'client_id': '', 'client_secret': ''}


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
            # SỬA DÒNG NÀY: Dùng cls=DecimalEncoder để xử lý số từ DynamoDB
            self.client.post_to_connection(
                ConnectionId=self.connection_id,
                Data=json.dumps(data, cls=DecimalEncoder).encode('utf-8')
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


def get_google_drive_service(credentials: Dict[str, str]):
    """
    Create Google Drive API service client with caching.
    """
    global _drive_service_cache
    
    # Return cached service if available
    if _drive_service_cache is not None:
        return _drive_service_cache
    
    if not credentials.get('access_token'):
        return None
    
    try:
        creds = Credentials(
            token=credentials['access_token'],
            refresh_token=credentials.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=credentials.get('client_id'),
            client_secret=credentials.get('client_secret')
        )
        
        service = build('drive', 'v3', credentials=creds)
        # Cache the service for reuse
        _drive_service_cache = service
        return service
    except Exception as e:
        print(f"Error creating Google Drive service: {str(e)}")
        return None


def download_file_from_drive(service, file_id: str) -> bytes:
    """
    Download file content from Google Drive.
    """
    if not service:
        return b""
    
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
        return b""


def extract_text_with_pypdf(pdf_bytes: bytes) -> str:
    """
    Extract text from PDF using pypdf library.
    """
    try:
        pdf_buffer = io.BytesIO(pdf_bytes)
        pdf_reader = PdfReader(pdf_buffer)
        
        text_parts = []
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        
        return ' '.join(text_parts)
        
    except Exception as e:
        print(f"Error extracting text with pypdf: {str(e)}")
        return ""


def process_single_file(file_id: str, file_name: str, target_hole_codes: List[str], use_simulation: bool = False) -> Dict[str, Any]:
    """
    Process a single file and check for EXACT WORD MATCHES.
    Example: Target "BC" will match "BC" or "Code-BC" but NOT "BCA".
    """
    
    found_matches = []
    
    if use_simulation:
        # Simulation logic placeholder
        pass
    else:
        try:
            # Get Google Drive credentials
            credentials = get_google_drive_credentials()
            service = get_google_drive_service(credentials)
            
            if not service:
                print(f"No Google Drive service available for {file_name}")
            else:
                # Download file from Google Drive
                pdf_bytes = download_file_from_drive(service, file_id)
                
                if not pdf_bytes:
                    print(f"Could not download {file_name}")
                else:
                    # Extract text using pypdf
                    text_content = extract_text_with_pypdf(pdf_bytes)
                    
                    # --- DEBUG LOG: In ra 100 ký tự đầu để kiểm tra ---
                    print(f"[DEBUG TEXT] {file_name}: {text_content[:100]}...")
                    # --------------------------------------------------
                    
                    for code in target_hole_codes:
                        code_str = str(code).strip()
                        if not code_str:
                            continue
                            
                        # LOGIC QUAN TRỌNG: Dùng \b (Word Boundary) để bắt chính xác từ
                        # \b : Ranh giới từ (khoảng trắng, dấu chấm, phẩy, gạch ngang...)
                        pattern = r'\b' + re.escape(code_str) + r'\b'
                        
                        if re.search(pattern, text_content, re.IGNORECASE):
                            found_matches.append(code_str)
                            print(f"Found EXACT match: '{code_str}' in {file_name}")

        except Exception as e:
            print(f"Error processing {file_name}: {str(e)}")
            traceback.print_exc()
    
    result = {
        'file_name': file_name,
        'found_codes': found_matches,
        'status': f"{len(found_matches)} Match{'es' if len(found_matches) != 1 else ''}" if found_matches else "No Match"
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


def process_file_with_metadata(message_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single file with its metadata. 
    This function is designed to be called in parallel.
    """
    session_id = message_data['session_id']
    file_id = message_data.get('file_id', '')
    file_name = message_data['file_name']
    pdf_link = message_data['pdf_link']
    target_hole_codes = message_data['target_hole_codes']
    use_simulation = message_data.get('use_simulation', False)
    
    print(f"Processing file: {file_name} for session: {session_id}")
    start_time = time.time()
    
    # Process the file
    result = process_single_file(file_id, file_name, target_hole_codes, use_simulation)
    
    elapsed_time = time.time() - start_time
    print(f"Processed {file_name} in {elapsed_time:.2f} seconds")
    
    # Return result with metadata
    return {
        'session_id': session_id,
        'file_name': file_name,
        'pdf_link': pdf_link,
        'result': result
    }


def handler(event, context):
    """Worker Lambda handler - processes files from SQS in parallel"""
    print(f"Received SQS event with {len(event.get('Records', []))} records")
    
    table = dynamodb.Table(TABLE_NAME)
    
    try:
        # Prepare all message data for parallel processing
        messages_to_process = []
        for record in event.get('Records', []):
            message_body = json.loads(record['body'])
            messages_to_process.append(message_body)
        
        # Process files in parallel using ThreadPoolExecutor
        # Use max_workers=10 to process up to 10 files concurrently
        results_list = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all tasks
            future_to_message = {
                executor.submit(process_file_with_metadata, msg): msg 
                for msg in messages_to_process
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_message):
                try:
                    result_data = future.result()
                    results_list.append(result_data)
                except Exception as e:
                    msg = future_to_message[future]
                    print(f"Error processing file {msg.get('file_name', 'unknown')}: {str(e)}")
                    traceback.print_exc()
        
        print(f"Completed parallel processing of {len(results_list)} files")
        
        # Now update DynamoDB and send WebSocket updates for all results
        for result_data in results_list:
            session_id = result_data['session_id']
            file_name = result_data['file_name']
            pdf_link = result_data['pdf_link']
            result = result_data['result']
            
            # Write result to DynamoDB if matches found
            if result['found_codes']:
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
            
            # Ép kiểu int để tính toán an toàn
            total_files = int(meta.get('total_files', 0)) 
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
                
                # Send progress update (only for every 10th file to reduce noise)
                if processed_count % 10 == 0 or processed_count >= total_files:
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