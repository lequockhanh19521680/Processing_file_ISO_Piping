"""
PDF Utilities Module

Handles PDF text extraction with caching for performance optimization.
"""

from typing import Dict, Optional
import io
from PyPDF2 import PdfReader


class PDFTextExtractor:
    """
    Extracts and caches text content from PDF files.
    Uses in-memory caching to avoid re-extracting text from the same PDF.
    """
    
    def __init__(self):
        """Initialize the extractor with an empty cache."""
        self.text_cache: Dict[str, str] = {}
    
    def extract_text(self, pdf_content: bytes, file_id: str) -> str:
        """
        Extract text from PDF content, using cache if available.
        
        Args:
            pdf_content: PDF file content as bytes
            file_id: Unique identifier for the PDF (used for caching)
            
        Returns:
            Extracted text from all pages, concatenated with spaces
        """
        # Check if already cached
        if file_id in self.text_cache:
            return self.text_cache[file_id]
        
        try:
            # Create PDF reader from bytes
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = PdfReader(pdf_file)
            
            # Extract text from all pages
            text_parts = []
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            # Combine all text with spaces
            full_text = " ".join(text_parts)
            
            # Cache the result
            self.text_cache[file_id] = full_text
            
            return full_text
            
        except Exception as e:
            print(f"Error extracting text from PDF {file_id}: {str(e)}")
            # Cache empty string for failed extractions to avoid retrying
            self.text_cache[file_id] = ""
            return ""
    
    def search_text(self, text: str, search_term: str) -> bool:
        """
        Search for a term in extracted text (case-insensitive).
        
        Args:
            text: The text to search in
            search_term: The term to search for
            
        Returns:
            True if search term is found, False otherwise
        """
        if not text or not search_term:
            return False
        
        return search_term.lower() in text.lower()
    
    def get_cache_size(self) -> int:
        """
        Get the number of cached PDF texts.
        
        Returns:
            Number of entries in cache
        """
        return len(self.text_cache)
    
    def clear_cache(self) -> None:
        """Clear the text cache."""
        self.text_cache.clear()
