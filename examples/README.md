# Example Files

This directory contains example files to help you get started with the ISO Piping File Processor.

## sample_input.xlsx

A sample input Excel file that demonstrates the correct format for processing.

### Structure:
- **Column A Header**: `ma_ho` (required)
- **Rows 2+**: Sample ma_ho identifiers

### Sample Values Included:
1. ISO-P-001
2. ISO-P-002
3. ISO-P-003
4. VALVE-A001
5. VALVE-A002
6. PIPE-2024-001
7. PIPE-2024-002
8. FLANGE-B123
9. FITTING-C456
10. SUPPORT-D789

### How to Use:

1. Download `sample_input.xlsx`
2. Modify the ma_ho values to match your actual identifiers
3. Upload the modified file to the application
4. Provide your Google Drive folder link
5. Process and download the results

### Creating Your Own Input File:

You can create your own Excel file following this format:
- Create a new Excel workbook (.xlsx)
- Name the first column header as "ma_ho" (case-insensitive)
- Add your ma_ho values in column A, starting from row 2
- Save the file

### Tips:
- Keep one ma_ho value per row
- Empty rows will be skipped
- The application searches for these values in PDF files
- Search is case-insensitive

### Generating Sample Files:

You can generate a sample file programmatically using:

```bash
cd backend
python create_sample_excel.py
```

This will create a new `sample_input.xlsx` file with test data.
