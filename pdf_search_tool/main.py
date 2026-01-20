#!/usr/bin/env python3
"""
PDF Keyword Search Tool - Main Entry Point

A production-ready, modular Python application that searches for specific keywords
(Manhole Codes - "Mã hố") from an Excel file across a large directory of PDF files
using concurrent processing.

Features:
    - Modular architecture with separation of concerns
    - Concurrent processing with 50 workers using ThreadPoolExecutor
    - Professional Rich UI with progress bars and live status updates
    - Comprehensive logging to logs/system.log
    - Excel input/output with Match_Type column (Single Match / Multi Match (N))
    - Recursive PDF scanning in directories and subdirectories

Usage:
    python main.py <input_excel> <pdf_directory> [output_excel]

Arguments:
    input_excel    : Path to Excel file with keywords (ma_ho column)
    pdf_directory  : Root directory containing PDF files
    output_excel   : (Optional) Path for output Excel file. If not provided,
                     saves to output/results.xlsx

Example:
    python main.py data/input.xlsx ./pdf_files/ output/results.xlsx

Author: Generated for ISO Piping Project
Version: 2.0.0
"""

import sys
import os
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import APP_NAME, VERSION, OUTPUT_DIR
from src.core.pdf_processor import find_pdf_files
from src.core.search_engine import SearchEngine
from src.utils.file_io import read_keywords_from_excel, save_results_to_excel
from src.utils.logger import get_logger
from src.ui.display import (
    print_header,
    print_summary,
    print_error,
    SimpleProgressDisplay,
    console
)

logger = get_logger(__name__)


def main():
    """
    Main entry point for the PDF Keyword Search Tool.
    """
    # Print header
    print_header()
    
    # Check command line arguments
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        console.print("[bold yellow]Usage:[/bold yellow] python main.py <input_excel> <pdf_directory> [output_excel]")
        console.print()
        console.print("[bold cyan]Arguments:[/bold cyan]")
        console.print("  [yellow]input_excel[/yellow]    : Path to Excel file with keywords (ma_ho column)")
        console.print("  [yellow]pdf_directory[/yellow]  : Root directory containing PDF files")
        console.print("  [yellow]output_excel[/yellow]   : (Optional) Path for output Excel file")
        console.print()
        console.print("[bold cyan]Example:[/bold cyan]")
        console.print("  python main.py data/input.xlsx ./pdf_files/ output/results.xlsx")
        console.print()
        sys.exit(1)
    
    input_excel = sys.argv[1]
    pdf_directory = sys.argv[2]
    output_excel = sys.argv[3] if len(sys.argv) == 4 else str(OUTPUT_DIR / "results.xlsx")
    
    logger.info("=" * 80)
    logger.info(f"Starting {APP_NAME} v{VERSION}")
    logger.info(f"Input Excel: {input_excel}")
    logger.info(f"PDF Directory: {pdf_directory}")
    logger.info(f"Output Excel: {output_excel}")
    logger.info("=" * 80)
    
    try:
        # Step 1: Read keywords from Excel
        console.print("[bold cyan]Step 1/4:[/bold cyan] Reading keywords from Excel file...")
        keywords = read_keywords_from_excel(input_excel)
        console.print(f"[green]✓[/green] Loaded [bold]{len(keywords)}[/bold] keywords")
        console.print()
        
        # Step 2: Find PDF files
        console.print("[bold cyan]Step 2/4:[/bold cyan] Scanning for PDF files in directory...")
        pdf_files = find_pdf_files(pdf_directory)
        console.print(f"[green]✓[/green] Found [bold]{len(pdf_files)}[/bold] PDF files")
        console.print()
        
        if not pdf_files:
            console.print("[bold yellow]⚠ WARNING:[/bold yellow] No PDF files found!")
            logger.warning("No PDF files found in directory")
            
            # Create empty results
            results = [
                {
                    'ma_ho': kw,
                    'found': 'NO',
                    'file_name': '',
                    'file_path': '',
                    'match_type': ''
                }
                for kw in keywords
            ]
        else:
            # Step 3: Process keywords with Rich UI
            console.print("[bold cyan]Step 3/4:[/bold cyan] Processing keywords (this may take a while)...")
            console.print()
            
            # Initialize search engine
            search_engine = SearchEngine()
            
            # Create progress display
            display = SimpleProgressDisplay()
            display.start(len(keywords))
            
            # Define callbacks for progress updates
            def progress_callback(completed, total):
                display.update_progress(completed, total)
            
            def status_callback(keyword, location, status):
                display.update_status(keyword, location, status)
            
            # Process keywords with concurrent execution
            results = search_engine.process_keywords(
                keywords=keywords,
                pdf_files=pdf_files,
                progress_callback=progress_callback,
                status_callback=status_callback
            )
            
            # Stop progress display
            display.stop()
            console.print("[green]✓[/green] Keyword processing complete")
            console.print()
        
        # Step 4: Save results
        console.print("[bold cyan]Step 4/4:[/bold cyan] Saving results to Excel file...")
        save_results_to_excel(results, output_excel, input_excel)
        console.print("[green]✓[/green] Results saved successfully")
        
        # Print summary
        found_count = sum(1 for r in results if r['found'] == 'YES')
        not_found_count = len(results) - found_count
        print_summary(len(results), found_count, not_found_count, output_excel)
        
        logger.info("Script completed successfully")
        
    except FileNotFoundError as e:
        print_error(f"File not found: {str(e)}")
        logger.error(f"File not found: {str(e)}", exc_info=True)
        sys.exit(1)
        
    except ValueError as e:
        print_error(f"Invalid input: {str(e)}")
        logger.error(f"Invalid input: {str(e)}", exc_info=True)
        sys.exit(1)
        
    except Exception as e:
        print_error(f"An unexpected error occurred: {str(e)}\n\nCheck logs/system.log for detailed information")
        logger.error(f"Script failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
