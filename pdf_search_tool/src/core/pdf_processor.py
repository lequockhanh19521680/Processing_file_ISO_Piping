"""
PDF processing module for PDF Search Tool.

This module handles PDF text extraction using pdfplumber and provides
utilities for finding PDF files in directories.
"""

import os
from pathlib import Path
from typing import List, Optional

import pdfplumber

from ..config import PDF_EXTENSIONS
from ..utils.logger import get_logger

logger = get_logger(__name__)


def find_pdf_files(root_directory: str) -> List[str]:
    """
    Recursively find all PDF files in a directory and its subdirectories.
    
    Args:
        root_directory: Root directory to search for PDF files
        
    Returns:
        List of absolute paths to PDF files (sorted)
        
    Raises:
        FileNotFoundError: If the root directory does not exist
    """
    logger.info(f"Scanning for PDF files in: {root_directory}")
    
    if not os.path.exists(root_directory):
        error_msg = f"Directory not found: {root_directory}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    pdf_files = []
    root_path = Path(root_directory)
    
    # Recursively find all PDF files with different extensions
    for ext in PDF_EXTENSIONS:
        for pdf_file in root_path.rglob(f"*{ext}"):
            if pdf_file.is_file():
                abs_path = str(pdf_file.absolute())
                if abs_path not in pdf_files:
                    pdf_files.append(abs_path)
    
    logger.info(f"Found {len(pdf_files)} PDF files")
    return sorted(pdf_files)


def extract_text_from_pdf(pdf_path: str) -> Optional[str]:
    """
    Extract text content from a PDF file using pdfplumber.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text from all pages, or None if extraction fails
    """
    try:
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        
        full_text = " ".join(text_parts)
        logger.debug(f"Extracted {len(full_text)} characters from {os.path.basename(pdf_path)}")
        return full_text
        
    except Exception as e:
        logger.warning(f"Failed to extract text from {pdf_path}: {str(e)}")
        return None


def count_keyword_occurrences(text: str, keyword: str, case_sensitive: bool = False) -> int:
    """
    Count how many times a keyword appears in the text.
    
    Args:
        text: Text to search in
        keyword: Keyword to search for
        case_sensitive: Whether to perform case-sensitive search
        
    Returns:
        Number of times the keyword appears in the text
    """
    if not text or not keyword:
        return 0
    
    if case_sensitive:
        count = text.count(keyword)
    else:
        # Case-insensitive search
        text_lower = text.lower()
        keyword_lower = keyword.lower()
        count = text_lower.count(keyword_lower)
    
    return count
