# PDF Keyword Search Tool

A professional, modular Python application for searching keywords (Manhole Codes - "Mã hố") from an Excel file across a massive directory of PDFs with concurrent processing and a modern terminal UI.

## 🎯 Features

- **Modular Architecture**: Clean separation of concerns with organized folder structure
- **High Performance**: Concurrent processing with 50 worker threads using ThreadPoolExecutor
- **Modern UI**: Professional terminal interface using Rich library with:
  - Smooth progress bars showing overall completion
  - Live status updates with current keyword and location
  - Beautiful, dashboard-like appearance
- **Smart Matching**: 
  - Counts keyword occurrences in each PDF
  - Reports "Single Match" or "Multi Match (N)" in results
- **Professional Logging**: 
  - Detailed DEBUG-level logging to `logs/system.log`
  - Clean console output with Rich UI only
- **Robust**: Handles large directories, recursive scanning, comprehensive error handling

## 📁 Project Structure

```
pdf_search_tool/
├── data/                  # Input Excel and target PDFs (user data)
├── logs/                  # Log files (system.log)
├── output/                # Result Excel files
├── src/                   # Source code
│   ├── __init__.py
│   ├── config.py          # Configuration (Constants, Path settings)
│   ├── core/              # Backend logic
│   │   ├── __init__.py
│   │   ├── pdf_processor.py   # PDF reading & text extraction
│   │   └── search_engine.py   # Multithreading & Matching logic
│   ├── utils/             # Helper functions
│   │   ├── __init__.py
│   │   ├── file_io.py     # Excel reading/writing
│   │   └── logger.py      # Logging configuration
│   └── ui/                # Frontend logic
│       ├── __init__.py
│       └── display.py     # Rich library UI handlers
├── main.py                # Entry point
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## 🚀 Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package installer)

### Setup

1. Navigate to the project directory:
```bash
cd pdf_search_tool
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv

# Activate on macOS/Linux:
source venv/bin/activate

# Activate on Windows:
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## 📖 Usage

### Basic Usage

```bash
python main.py <input_excel> <pdf_directory> [output_excel]
```

**Arguments:**
- `input_excel`: Path to Excel file with keywords (must have "ma_ho" column)
- `pdf_directory`: Root directory containing PDF files to search
- `output_excel`: (Optional) Path for output file. Defaults to `output/results.xlsx`

### Examples

**Example 1: Basic usage with default output**
```bash
python main.py data/keywords.xlsx /path/to/pdfs/
```

**Example 2: Custom output path**
```bash
python main.py data/keywords.xlsx /path/to/pdfs/ output/results_2024.xlsx
```

**Example 3: Relative paths**
```bash
python main.py ../input.xlsx ../pdf_files/ ../output.xlsx
```

## 📊 Input/Output Format

### Input Excel File

Your input Excel file must contain a column with one of these names (case-insensitive):
- `ma_ho`
- `Mã hố`
- `ma ho`
- `keyword`
- `keywords`

**Example:**

| ma_ho |
|-------|
| PPMZD-AU-1 |
| PPMZD-AU-2 |
| VALVE-123 |

### Output Excel File

The output file will contain:
1. **Original sheet(s)** from your input file (preserved)
2. **New "RESULT" sheet** with these columns:

| Column | Description |
|--------|-------------|
| `ma_ho` | The keyword that was searched |
| `found` | "YES" if found, "NO" if not found |
| `file_name` | Name of the PDF file where found (empty if not found) |
| `file_path` | Full path to the PDF file (empty if not found) |
| `Match_Type` | "Single Match" or "Multi Match (N)" showing occurrence count |

**Example output:**

| ma_ho | found | file_name | file_path | Match_Type |
|-------|-------|-----------|-----------|------------|
| PPMZD-AU-1 | YES | Drawing_001.pdf | /path/to/Drawing_001.pdf | Single Match |
| PPMZD-AU-2 | YES | Spec_Sheet.pdf | /path/to/Spec_Sheet.pdf | Multi Match (3) |
| VALVE-123 | NO | | | |

## 🎨 User Interface

The tool provides a modern terminal UI using the Rich library:

### During Processing:
```
╔══════════════════════════════════════════════════════════════╗
║            PDF Keyword Search Tool v2.0.0                     ║
╚══════════════════════════════════════════════════════════════╝

Step 3/4: Processing keywords (this may take a while)...

⠋ Processing Keywords [110/6633] ━━━━━━━━━━━━━━━━━━╺━━━━━━━━━━━ 
   2:15 • 1:45:30 remaining
```

### After Completion:
```
╔═══════════════════════════════════════════════════════════════╗
║                  ✓ Processing Complete                        ║
╠═══════════════════════════════════════════════════════════════╣
║ Metric                    │                          Value    ║
╠═══════════════════════════════════════════════════════════════╣
║ Total Keywords            │                          6633     ║
║ Keywords Found            │                          4521     ║
║ Keywords Not Found        │                          2112     ║
║ Success Rate              │                         68.2%     ║
╚═══════════════════════════════════════════════════════════════╝

Results saved to: output/results.xlsx
```

## 🔧 Configuration

You can modify settings in `src/config.py`:

```python
# Performance settings
DEFAULT_MAX_WORKERS = 50  # Adjust based on your CPU

# Search settings
CASE_SENSITIVE_SEARCH = False  # Set to True for case-sensitive matching

# Logging
LOG_LEVEL_FILE = "DEBUG"  # File logging verbosity
LOG_LEVEL_CONSOLE = "ERROR"  # Console logging (keep ERROR for clean UI)
```

## 📝 Logging

### File Logging (`logs/system.log`)
- **Level**: DEBUG (all details)
- **Includes**: 
  - Timestamps
  - Thread names
  - Full stack traces for errors
  - All processing details

### Console Logging
- **Level**: ERROR only
- **Purpose**: Keep terminal clean for Rich UI
- Only critical errors are shown

**View logs:**
```bash
# View recent logs
tail -f logs/system.log

# Search for errors
grep ERROR logs/system.log
```

## ⚡ Performance

- **Concurrent Processing**: 50 worker threads by default
- **Typical Speed**: 
  - ~1-2 seconds per PDF file (depends on size and content)
  - Can process thousands of PDFs efficiently
- **Memory Usage**: Moderate (text extraction per PDF)
- **Optimizations**:
  - ThreadPoolExecutor for I/O-bound PDF reading
  - Efficient text searching with string.count()
  - Minimal memory footprint per thread

## 🐛 Troubleshooting

### "Excel file not found"
- Verify the path to your Excel file is correct
- Use absolute paths or ensure you're in the correct directory

### "No keyword column found"
- Ensure your Excel has a column named "ma_ho" (or variations)
- Check column spelling and case

### "No PDF files found"
- Verify the PDF directory path is correct
- Ensure PDFs have .pdf or .PDF extension
- Check that you have read permissions

### Processing is slow
- Large PDFs take longer to process
- Scanned PDFs (images) may be slower
- Adjust MAX_WORKERS in config.py based on your CPU
- Consider processing in batches

### Import errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Activate your virtual environment if you created one

## 🔒 Best Practices

1. **Virtual Environment**: Always use a virtual environment
2. **Input Validation**: Verify your Excel format before processing
3. **Backup**: Keep backups of original Excel files
4. **Logging**: Check logs for any warnings or errors
5. **Testing**: Test with a small subset first for large jobs
6. **Resources**: Monitor CPU/memory for very large jobs

## 📚 Module Documentation

### `src/config.py`
Configuration constants, paths, and default values.

### `src/core/pdf_processor.py`
- `find_pdf_files()`: Recursively find all PDFs in a directory
- `extract_text_from_pdf()`: Extract text content from a PDF
- `count_keyword_occurrences()`: Count keyword frequency in text

### `src/core/search_engine.py`
- `SearchEngine`: Main class for concurrent PDF searching
- `search_keyword_in_pdf()`: Search a single PDF for a keyword
- `process_keywords()`: Process all keywords across all PDFs

### `src/utils/file_io.py`
- `read_keywords_from_excel()`: Read keywords from input Excel
- `save_results_to_excel()`: Write results to output Excel with RESULT sheet

### `src/utils/logger.py`
- `setup_logger()`: Configure logging with file and console handlers
- `get_logger()`: Get a configured logger instance

### `src/ui/display.py`
- `SimpleProgressDisplay`: Progress bar with Rich
- `print_header()`: Print application header
- `print_summary()`: Display results summary table
- `print_error()`: Display formatted error messages

## 🤝 Contributing

This is a production tool. If you want to modify or extend it:

1. Keep the modular structure intact
2. Update documentation for any changes
3. Test thoroughly with sample data
4. Update version number in `config.py`

## 📄 License

This project is part of the ISO Piping File Processor project.

## 🆘 Support

For issues or questions:
1. Check this README
2. Review `logs/system.log` for detailed error information
3. Verify input file format matches expectations
4. Test with smaller dataset first

## 🔮 Future Enhancements

Potential improvements:
- [ ] GUI version with tkinter or PyQt
- [ ] Database backend for caching results
- [ ] Support for other document formats (Word, images with OCR)
- [ ] REST API version
- [ ] Batch processing with job queue
- [ ] Real-time progress via WebSocket
- [ ] Advanced search (regex, fuzzy matching)
- [ ] Export to multiple formats (CSV, JSON, PDF report)

---

**Version**: 2.0.0  
**Created for**: ISO Piping Project  
**Architecture**: Modular, production-ready
