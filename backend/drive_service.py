"""
Google Drive Service Module
Handles authentication and file operations with Google Drive API.
"""
import os
import re
import logging
import ssl
import json
import urllib.request
from typing import List, Dict, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.auth.transport.requests import Request as GoogleAuthRequest

# --- FIX SSL (Level 1): Global Patch ---
# Giữ lại patch này để đảm bảo các hàm list/search hoạt động tốt
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context


class DriveService:
    def __init__(self, service_account_file: str = "service-account.json"):
        self.service_account_file = service_account_file
        self.service = None
        self.credentials = None # Lưu credentials để dùng lại khi tải file
        self.scopes = ['https://www.googleapis.com/auth/drive.readonly']

    def authenticate(self) -> None:
        """
        Authenticate with Google Drive using service account credentials.
        """
        if not os.path.exists(self.service_account_file):
            raise FileNotFoundError(
                f"Service account file not found: {self.service_account_file}\n"
                "Please place your service-account.json in the backend directory."
            )
        
        try:
            # 1. Load Credentials
            self.credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=self.scopes
            )
            
            # 2. Build Service (Standard way)
            self.service = build('drive', 'v3', credentials=self.credentials)
            
        except Exception as e:
            raise Exception(f"Failed to authenticate with Google Drive: {str(e)}")

    def extract_folder_id(self, drive_link: str) -> str:
        """Extract folder ID from various Google Drive URL formats."""
        match = re.search(r'folders/([a-zA-Z0-9_-]+)', drive_link)
        if match:
            return match.group(1)
            
        match = re.search(r'id=([a-zA-Z0-9_-]+)', drive_link)
        if match:
            return match.group(1)
            
        if 'http' not in drive_link and '/' not in drive_link:
             return drive_link.strip()
             
        raise ValueError("Could not extract Folder ID from the provided link")

    def list_pdf_files_recursive(self, folder_id: str) -> List[Dict]:
        """List all PDF files in folder and subfolders."""
        if not self.service:
            self.authenticate()
            
        files_list = []
        
        def _search_folder(f_id, current_path=""):
            page_token = None
            while True:
                try:
                    response = self.service.files().list(
                        q=f"'{f_id}' in parents and trashed = false",
                        fields="nextPageToken, files(id, name, mimeType)",
                        pageToken=page_token
                    ).execute()
                    
                    for file in response.get('files', []):
                        if file['mimeType'] == 'application/pdf':
                            files_list.append({
                                'file_id': file['id'],
                                'file_name': file['name'],
                                'folder_path': current_path
                            })
                        elif file['mimeType'] == 'application/vnd.google-apps.folder':
                            new_path = f"{current_path}/{file['name']}" if current_path else file['name']
                            _search_folder(file['id'], new_path)
                    
                    page_token = response.get('nextPageToken', None)
                    if not page_token:
                        break
                except Exception as e:
                    logging.error(f"Error searching folder {f_id}: {str(e)}")
                    break
        
        _search_folder(folder_id)
        return files_list

    def download_file(self, file_id: str) -> Optional[bytes]:
        """
        Download file content manually using urllib to bypass SSL/Proxy issues.
        """
        if not self.credentials:
            self.authenticate()
            
        try:
            # 1. Đảm bảo token còn hạn (Refresh nếu cần)
            if not self.credentials.valid:
                self.credentials.refresh(GoogleAuthRequest())
            
            token = self.credentials.token
            
            # 2. Cấu hình request thủ công
            url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
            headers = {"Authorization": f"Bearer {token}"}
            req = urllib.request.Request(url, headers=headers)
            
            # 3. Tạo SSL Context "lỏng lẻo" riêng cho request này
            # (Giúp vượt qua lỗi WRONG_VERSION_NUMBER mà thư viện chuẩn google hay gặp)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            # 4. Thực hiện tải file
            with urllib.request.urlopen(req, context=ctx) as response:
                return response.read()
                
        except Exception as e:
            logging.error(f"Error downloading file {file_id}: {str(e)}")
            return None