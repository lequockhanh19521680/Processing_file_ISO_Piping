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
  const [progress, setProgress] = useState([]);
  const [currentStage, setCurrentStage] = useState('');
  const [showProgress, setShowProgress] = useState(false);

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
    setProgress([]);
    setCurrentStage('');
    setShowProgress(true);

    try {
      // Create FormData for multipart/form-data request
      const formData = new FormData();
      formData.append('file', file);
      formData.append('drive_link', driveLink);

      // Use the progress endpoint with SSE
      const response = await fetch(`${API_BASE_URL}/process-with-progress`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.substring(6));
              
              if (data.type === 'progress') {
                setCurrentStage(data.message);
                setProgress(prev => [...prev, { type: 'info', message: data.message, stage: data.stage }]);
              } else if (data.type === 'search_result') {
                const message = data.found 
                  ? `✓ ${data.ma_ho} found in ${data.file_name}` 
                  : `✗ ${data.ma_ho} not found`;
                setProgress(prev => [...prev, { 
                  type: data.found ? 'success' : 'warning', 
                  message,
                  current: data.current,
                  total: data.total 
                }]);
              } else if (data.type === 'complete') {
                setCurrentStage(data.message);
                setProgress(prev => [...prev, { type: 'success', message: data.message }]);
              } else if (data.type === 'file') {
                // Convert base64 back to blob - optimized version
                const binaryString = atob(data.data);
                const bytes = Uint8Array.from(binaryString, c => c.charCodeAt(0));
                const blob = new Blob([bytes], {
                  type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                });
                const url = window.URL.createObjectURL(blob);
                setDownloadUrl(url);
                setSuccess('Processing completed successfully! Click the download button below.');
              } else if (data.type === 'error') {
                setError(data.message);
                setProgress(prev => [...prev, { type: 'error', message: data.message }]);
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }
      
    } catch (err) {
      console.error('Error processing file:', err);
      setError(err.message || 'An error occurred during processing');
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

        {/* Progress Display */}
        {showProgress && (
          <div className="progress-container">
            <h3>Processing Progress:</h3>
            {currentStage && (
              <div className="current-stage">
                <strong>Current:</strong> {currentStage}
              </div>
            )}
            <div className="progress-list">
              {progress.map((item, index) => (
                <div key={index} className={`progress-item progress-${item.type}`}>
                  {item.message}
                  {item.current && item.total && (
                    <span className="progress-count"> ({item.current}/{item.total})</span>
                  )}
                </div>
              ))}
            </div>
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
