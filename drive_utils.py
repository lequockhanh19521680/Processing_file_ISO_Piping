"""
Google Drive API utilities for listing and downloading PDF files.
"""
import re
import io
from typing import List, Dict, Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account


def extract_folder_id(drive_link: str) -> str:
    """
    Extract folder ID from a Google Drive link.
    
    Args:
        drive_link: Google Drive folder link
        
    Returns:
        Folder ID
    """
    # Pattern for folder links: https://drive.google.com/drive/folders/FOLDER_ID
    patterns = [
        r'folders/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)',
        r'^([a-zA-Z0-9_-]+)$'  # Just the ID itself
    ]
    
    for pattern in patterns:
        match = re.search(pattern, drive_link)
        if match:
            return match.group(1)
    
    raise ValueError("Invalid Google Drive folder link. Could not extract folder ID.")


def create_drive_service(credentials_path: str):
    """
    Create Google Drive API service using service account credentials.
    
    Args:
        credentials_path: Path to service account JSON file
        
    Returns:
        Google Drive service object
    """
    try:
        SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES)
        service = build('drive', 'v3', credentials=credentials)
        return service
    except Exception as e:
        raise Exception(f"Error creating Drive service: {str(e)}")


def list_drive_pdfs(service, folder_id: str, parent_path: str = "") -> List[Dict[str, str]]:
    """
    Recursively list all PDF files in a Google Drive folder and its subfolders.
    
    Args:
        service: Google Drive service object
        folder_id: ID of the folder to search
        parent_path: Path of parent folders (for tracking folder hierarchy)
        
    Returns:
        List of dictionaries containing PDF file information
    """
    pdf_files = []
    
    try:
        # Query for all files and folders in the current folder
        query = f"'{folder_id}' in parents and trashed=false"
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType, parents)",
            pageSize=1000
        ).execute()
        
        items = results.get('files', [])
        
        for item in items:
            file_name = item['name']
            file_id = item['id']
            mime_type = item['mimeType']
            
            current_path = f"{parent_path}/{file_name}" if parent_path else file_name
            
            # If it's a folder, recurse into it
            if mime_type == 'application/vnd.google-apps.folder':
                subfolder_pdfs = list_drive_pdfs(service, file_id, current_path)
                pdf_files.extend(subfolder_pdfs)
            
            # If it's a PDF, add it to the list
            elif mime_type == 'application/pdf' or file_name.lower().endswith('.pdf'):
                pdf_files.append({
                    'file_id': file_id,
                    'file_name': file_name,
                    'folder_path': parent_path if parent_path else '/',
                    'mime_type': mime_type
                })
        
        return pdf_files
    
    except Exception as e:
        raise Exception(f"Error listing files from Drive: {str(e)}")


def download_pdf_content(service, file_id: str) -> bytes:
    """
    Download PDF file content from Google Drive.
    
    Args:
        service: Google Drive service object
        file_id: ID of the file to download
        
    Returns:
        PDF file content as bytes
    """
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
        raise Exception(f"Error downloading file {file_id}: {str(e)}")
