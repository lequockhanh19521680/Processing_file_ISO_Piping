"""
PDF text extraction utilities with caching support.
"""
import pdfplumber
import io
from typing import Dict, Optional


class PDFTextCache:
    """Cache for storing extracted PDF text to avoid re-downloading."""
    
    def __init__(self):
        self.cache: Dict[str, str] = {}
    
    def get(self, file_id: str) -> Optional[str]:
        """Get cached text for a file ID."""
        return self.cache.get(file_id)
    
    def set(self, file_id: str, text: str):
        """Cache text for a file ID."""
        self.cache[file_id] = text
    
    def clear(self):
        """Clear the cache."""
        self.cache.clear()


def extract_pdf_text(pdf_content: bytes, file_id: str, cache: PDFTextCache) -> str:
    """
    Extract text from PDF content with caching support.
    
    Args:
        pdf_content: PDF file content as bytes
        file_id: File ID for caching
        cache: PDFTextCache instance
        
    Returns:
        Extracted text from the PDF
    """
    # Check if text is already cached
    cached_text = cache.get(file_id)
    if cached_text is not None:
        return cached_text
    
    try:
        # Extract text from PDF
        text = ""
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        # Cache the extracted text
        cache.set(file_id, text)
        
        return text
    
    except Exception as e:
        # If extraction fails, cache empty string to avoid retrying
        cache.set(file_id, "")
        raise Exception(f"Error extracting text from PDF: {str(e)}")


def search_codes(codes: list, pdf_files: list, service, cache: PDFTextCache, 
                 progress_callback=None) -> list:
    """
    Search for codes in PDF files.
    
    Args:
        codes: List of ma_ho codes to search for
        pdf_files: List of PDF file information dictionaries
        service: Google Drive service object
        cache: PDFTextCache instance
        progress_callback: Optional callback function for progress updates
        
    Returns:
        List of result dictionaries
    """
    from drive_utils import download_pdf_content
    
    results = []
    total_codes = len(codes)
    
    for idx, code in enumerate(codes):
        result = {
            'ma_ho': code,
            'found': 'NO',
            'file_name': '',
            'file_id': '',
            'folder_path': ''
        }
        
        # Search in each PDF
        for pdf_info in pdf_files:
            file_id = pdf_info['file_id']
            
            # Get or extract PDF text
            cached_text = cache.get(file_id)
            if cached_text is None:
                try:
                    # Download and extract text
                    pdf_content = download_pdf_content(service, file_id)
                    text = extract_pdf_text(pdf_content, file_id, cache)
                except Exception as e:
                    # Skip this file if there's an error
                    continue
            else:
                text = cached_text
            
            # Check if code exists in the text (exact match)
            if code in text:
                result['found'] = 'YES'
                result['file_name'] = pdf_info['file_name']
                result['file_id'] = file_id
                result['folder_path'] = pdf_info['folder_path']
                break  # Found, no need to check other PDFs
        
        results.append(result)
        
        # Call progress callback if provided
        if progress_callback:
            progress = (idx + 1) / total_codes
            progress_callback(progress, f"Processed {idx + 1}/{total_codes} codes")
    
    return results
