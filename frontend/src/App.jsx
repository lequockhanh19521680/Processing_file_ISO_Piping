import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [file, setFile] = useState(null);
  const [driveLink, setDriveLink] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [downloadUrl, setDownloadUrl] = useState(null);

  // Backend API base URL - use environment variable in production
  // Example: const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const API_BASE_URL = 'http://localhost:8000';

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    
    if (selectedFile) {
      // Validate file type
      if (!selectedFile.name.endsWith('.xlsx')) {
        setError('Please select a valid Excel file (.xlsx)');
        setFile(null);
        return;
      }
      setFile(selectedFile);
      setError('');
      setSuccess('');
    }
  };

  const handleDriveLinkChange = (event) => {
    setDriveLink(event.target.value);
    setError('');
    setSuccess('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    // Validation
    if (!file) {
      setError('Please select an Excel file');
      return;
    }

    if (!driveLink.trim()) {
      setError('Please enter a Google Drive folder link');
      return;
    }

    // Validate Google Drive link format
    if (!driveLink.includes('drive.google.com')) {
      setError('Please enter a valid Google Drive folder link');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');
    setDownloadUrl(null);

    try {
      // Create FormData for multipart/form-data request
      const formData = new FormData();
      formData.append('file', file);
      formData.append('drive_link', driveLink);

      // Send POST request to backend
      const response = await axios.post(`${API_BASE_URL}/process`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        responseType: 'blob', // Important for file download
      });

      // Create a download URL for the processed file
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const url = window.URL.createObjectURL(blob);
      setDownloadUrl(url);

      setSuccess('Processing completed successfully! Click the download button below.');
      
    } catch (err) {
      console.error('Error processing file:', err);
      
      if (err.response) {
        // Server responded with error
        if (err.response.data instanceof Blob) {
          // Error message might be in blob format
          const text = await err.response.data.text();
          try {
            const errorData = JSON.parse(text);
            setError(errorData.detail || 'An error occurred during processing');
          } catch {
            setError(text || 'An error occurred during processing');
          }
        } else {
          setError(err.response.data.detail || 'An error occurred during processing');
        }
      } else if (err.request) {
        // Request made but no response
        setError('Cannot connect to server. Please ensure the backend is running on port 8000.');
      } else {
        // Other errors
        setError('An unexpected error occurred');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (downloadUrl) {
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = 'processed_result.xlsx';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  return (
    <div className="app">
      <div className="container">
        <h1 className="title">ISO Piping File Processor</h1>
        <p className="subtitle">
          Process Excel files with ma_ho values against PDF files in Google Drive
        </p>

        <form onSubmit={handleSubmit} className="form">
          {/* File Upload */}
          <div className="form-group">
            <label htmlFor="file-upload" className="label">
              Excel File (.xlsx)
            </label>
            <div className="file-input-wrapper">
              <input
                type="file"
                id="file-upload"
                accept=".xlsx"
                onChange={handleFileChange}
                className="file-input"
                disabled={loading}
              />
              <label htmlFor="file-upload" className="file-input-label">
                {file ? file.name : 'Choose Excel file...'}
              </label>
            </div>
          </div>

          {/* Drive Link Input */}
          <div className="form-group">
            <label htmlFor="drive-link" className="label">
              Google Drive Folder Link
            </label>
            <input
              type="text"
              id="drive-link"
              value={driveLink}
              onChange={handleDriveLinkChange}
              placeholder="https://drive.google.com/drive/folders/..."
              className="text-input"
              disabled={loading}
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            className="submit-button"
            disabled={loading || !file || !driveLink}
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                Processing...
              </>
            ) : (
              'OK - Start Processing'
            )}
          </button>
        </form>

        {/* Error Message */}
        {error && (
          <div className="alert alert-error">
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Success Message */}
        {success && (
          <div className="alert alert-success">
            <strong>Success:</strong> {success}
          </div>
        )}

        {/* Download Button */}
        {downloadUrl && (
          <button onClick={handleDownload} className="download-button">
            📥 Download Processed Excel File
          </button>
        )}

        {/* Instructions */}
        <div className="instructions">
          <h3>Instructions:</h3>
          <ol>
            <li>Upload an Excel file with column A header as "ma_ho"</li>
            <li>Paste the Google Drive folder link containing PDF files</li>
            <li>Click OK to start processing</li>
            <li>Download the result with a new "RESULT" sheet</li>
          </ol>
        </div>
      </div>
    </div>
  );
}

export default App;
