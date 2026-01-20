"""
Search engine module for PDF Search Tool.

This module implements concurrent PDF searching using ThreadPoolExecutor
and provides the main search orchestration logic.
"""

import os
from typing import List, Dict, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..config import DEFAULT_MAX_WORKERS, CASE_SENSITIVE_SEARCH
from ..core.pdf_processor import extract_text_from_pdf, count_keyword_occurrences
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SearchEngine:
    """
    Search engine that processes keywords across PDF files using concurrent execution.
    
    Uses ThreadPoolExecutor with configurable workers to search multiple PDFs
    in parallel, providing callbacks for progress updates.
    """
    
    def __init__(self, max_workers: int = DEFAULT_MAX_WORKERS):
        """
        Initialize the search engine.
        
        Args:
            max_workers: Maximum number of concurrent threads for PDF processing
        """
        self.max_workers = max_workers
        logger.info(f"SearchEngine initialized with {max_workers} workers")
    
    def search_keyword_in_pdf(
        self,
        pdf_path: str,
        keyword: str,
        case_sensitive: bool = CASE_SENSITIVE_SEARCH
    ) -> Dict:
        """
        Search for a keyword in a single PDF file and count occurrences.
        
        This function is designed to be called by multiple workers concurrently.
        
        Args:
            pdf_path: Path to the PDF file
            keyword: Keyword to search for
            case_sensitive: Whether to perform case-sensitive search
            
        Returns:
            Dictionary containing:
                - pdf_path (str): Path to the PDF file
                - keyword (str): The keyword searched
                - count (int): Number of occurrences found
                - found (bool): Whether the keyword was found
        """
        try:
            text = extract_text_from_pdf(pdf_path)
            if text is None:
                return {
                    'pdf_path': pdf_path,
                    'keyword': keyword,
                    'count': 0,
                    'found': False
                }
            
            count = count_keyword_occurrences(text, keyword, case_sensitive)
            return {
                'pdf_path': pdf_path,
                'keyword': keyword,
                'count': count,
                'found': count > 0
            }
            
        except Exception as e:
            logger.error(
                f"Error searching keyword '{keyword}' in {pdf_path}: {str(e)}",
                exc_info=True
            )
            return {
                'pdf_path': pdf_path,
                'keyword': keyword,
                'count': 0,
                'found': False
            }
    
    def process_keywords(
        self,
        keywords: List[str],
        pdf_files: List[str],
        progress_callback: Optional[Callable] = None,
        status_callback: Optional[Callable] = None
    ) -> List[Dict]:
        """
        Process all keywords against all PDF files using concurrent execution.
        
        Uses ThreadPoolExecutor with the configured number of workers to process
        multiple PDFs in parallel.
        
        Args:
            keywords: List of keywords to search for
            pdf_files: List of PDF file paths to search
            progress_callback: Optional callback function for progress updates.
                             Called with (keyword_index, total_keywords)
            status_callback: Optional callback function for status updates.
                           Called with (keyword, current_folder, status_message)
            
        Returns:
            List of result dictionaries for each keyword
        """
        logger.info(f"Starting concurrent processing with {self.max_workers} workers")
        logger.info(f"Processing {len(keywords)} keywords across {len(pdf_files)} PDF files")
        
        results = []
        
        for keyword_idx, keyword in enumerate(keywords):
            logger.info(f"Processing keyword {keyword_idx + 1}/{len(keywords)}: {keyword}")
            
            best_match = None
            max_count = 0
            
            # Process all PDFs for this keyword concurrently
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all PDF search tasks for this keyword
                future_to_pdf = {
                    executor.submit(self.search_keyword_in_pdf, pdf_path, keyword): pdf_path
                    for pdf_path in pdf_files
                }
                
                # Process completed tasks
                for future in as_completed(future_to_pdf):
                    pdf_path = future_to_pdf[future]
                    
                    # Update status callback with current location
                    if status_callback:
                        folder = os.path.dirname(pdf_path)
                        # Shorten path if too long
                        if len(folder) > 50:
                            folder = "..." + folder[-47:]
                        status_callback(keyword, folder, "Searching...")
                    
                    try:
                        result = future.result()
                        
                        # Keep track of the best match (highest count)
                        if result['found'] and result['count'] > max_count:
                            max_count = result['count']
                            best_match = result
                            
                            # Update status on finding a match
                            if status_callback:
                                folder = os.path.dirname(pdf_path)
                                if len(folder) > 50:
                                    folder = "..." + folder[-47:]
                                status_callback(keyword, folder, "Found Match")
                            
                    except Exception as e:
                        logger.error(f"Task failed for {pdf_path}: {str(e)}", exc_info=True)
                        if status_callback:
                            folder = os.path.dirname(pdf_path)
                            if len(folder) > 50:
                                folder = "..." + folder[-47:]
                            status_callback(keyword, folder, "Error")
            
            # Prepare result for this keyword with Match_Type
            if best_match:
                # Format match_type based on count
                if max_count == 1:
                    match_type = "Single Match"
                else:
                    match_type = f"Multi Match ({max_count})"
                
                results.append({
                    'ma_ho': keyword,
                    'found': 'YES',
                    'file_name': os.path.basename(best_match['pdf_path']),
                    'file_path': best_match['pdf_path'],
                    'match_type': match_type
                })
                logger.info(
                    f"✓ Keyword '{keyword}' found {max_count} time(s) in "
                    f"{os.path.basename(best_match['pdf_path'])}"
                )
            else:
                results.append({
                    'ma_ho': keyword,
                    'found': 'NO',
                    'file_name': '',
                    'file_path': '',
                    'match_type': ''
                })
                logger.info(f"✗ Keyword '{keyword}' not found")
            
            # Call progress callback
            if progress_callback:
                progress_callback(keyword_idx + 1, len(keywords))
        
        logger.info(
            f"Processing complete. Found matches for "
            f"{sum(1 for r in results if r['found'] == 'YES')} keywords"
        )
        return results
