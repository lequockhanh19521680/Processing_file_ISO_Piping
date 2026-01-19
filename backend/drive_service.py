"""
Google Drive Service Module

Handles authentication and file operations with Google Drive API
using a service account for server-to-server authentication.
"""

import os
import re
from typing import List, Dict, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io


class DriveService:
    """
    Manages Google Drive API operations including authentication,
    folder listing, and file downloads.
    """
    
    def __init__(self, service_account_file: str = "service-account.json"):
        """
        Initialize the Drive service with service account credentials.
        
        Args:
            service_account_file: Path to the service account JSON file
        """
        self.service_account_file = service_account_file
        self.service = None
        
    def authenticate(self) -> None:
        """
        Authenticate with Google Drive using service account credentials.
        
        Raises:
            FileNotFoundError: If service account file is not found
            Exception: If authentication fails
        """
        if not os.path.exists(self.service_account_file):
            raise FileNotFoundError(
                f"Service account file not found: {self.service_account_file}\n"
                "Please place your service-account.json in the backend directory."
            )
        
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            self.service = build('drive', 'v3', credentials=credentials)
        except Exception as e:
            raise Exception(f"Failed to authenticate with Google Drive: {str(e)}")
    
    def extract_folder_id(self, drive_link: str) -> str:
        """
        Extract folder ID from Google Drive URL.
        
        Supports formats:
        - https://drive.google.com/drive/folders/FOLDER_ID
        - https://drive.google.com/drive/u/0/folders/FOLDER_ID
        
        Args:
            drive_link: Google Drive folder URL
            
        Returns:
            Extracted folder ID
            
        Raises:
            ValueError: If folder ID cannot be extracted
        """
        patterns = [
            r'/folders/([a-zA-Z0-9_-]+)',
            r'id=([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, drive_link)
            if match:
                return match.group(1)
        
        raise ValueError(f"Could not extract folder ID from link: {drive_link}")
    
    def list_pdf_files_recursive(self, folder_id: str, parent_path: str = "") -> List[Dict]:
        """
        Recursively list all PDF files in a folder and its subfolders.
        
        Args:
            folder_id: Google Drive folder ID
            parent_path: Path of parent folders (for tracking location)
            
        Returns:
            List of dictionaries containing file information:
            - file_id: Google Drive file ID
            - file_name: Name of the file
            - folder_path: Full path to the file
        """
        pdf_files = []
        
        try:
            # Query for all items in the folder
            query = f"'{folder_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType)",
                pageSize=1000
            ).execute()
            
            items = results.get('files', [])
            
            for item in items:
                item_id = item['id']
                item_name = item['name']
                mime_type = item['mimeType']
                
                # If it's a folder, recurse into it
                if mime_type == 'application/vnd.google-apps.folder':
                    subfolder_path = f"{parent_path}/{item_name}" if parent_path else item_name
                    pdf_files.extend(
                        self.list_pdf_files_recursive(item_id, subfolder_path)
                    )
                # If it's a PDF file, add it to the list
                elif mime_type == 'application/pdf':
                    pdf_files.append({
                        'file_id': item_id,
                        'file_name': item_name,
                        'folder_path': parent_path if parent_path else '/'
                    })
            
            return pdf_files
            
        except Exception as e:
            # Log error and return partial results rather than failing completely
            import logging
            logging.error(f"Error listing files in folder {folder_id}: {str(e)}")
            return pdf_files
    
    def download_file(self, file_id: str) -> Optional[bytes]:
        """
        Download a file from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            File content as bytes, or None if download fails
        """
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            file_buffer.seek(0)
            return file_buffer.read()
            
        except Exception as e:
            # Log error for debugging but return None to allow processing to continue
            import logging
            logging.error(f"Error downloading file {file_id}: {str(e)}")
            return None
