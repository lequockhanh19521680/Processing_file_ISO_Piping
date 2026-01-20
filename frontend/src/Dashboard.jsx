import React, { useState, useEffect, useRef } from 'react';
import useWebSocket, { ReadyState } from 'react-use-websocket';

const Dashboard = () => {
  // WebSocket configuration from environment variable with fallback
  // Set VITE_WEBSOCKET_URL in .env file or the connection will fail
  const websocketUrl = import.meta.env.VITE_WEBSOCKET_URL || '';
  const [shouldConnect, setShouldConnect] = useState(false);
  
  // Form state
  const [googleDriveLink, setGoogleDriveLink] = useState('');
  const [excelFile, setExcelFile] = useState(null);
  const [targetHoleCodes, setTargetHoleCodes] = useState([]);
  
  // Processing state
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [processedFiles, setProcessedFiles] = useState(0);
  const [totalFiles, setTotalFiles] = useState(0);
  const [results, setResults] = useState([]);
  const [downloadUrl, setDownloadUrl] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  
  // WebSocket connection
  const { sendMessage, lastMessage, readyState } = useWebSocket(
    websocketUrl,
    {
      shouldReconnect: () => true,
      reconnectAttempts: 10,
      reconnectInterval: 3000,
    },
    shouldConnect
  );
  
  // Connection status
  const connectionStatus = {
    [ReadyState.CONNECTING]: 'Connecting',
    [ReadyState.OPEN]: 'Connected',
    [ReadyState.CLOSING]: 'Closing',
    [ReadyState.CLOSED]: 'Disconnected',
    [ReadyState.UNINSTANTIATED]: 'Uninstantiated',
  }[readyState];
  
  const connectionColor = {
    [ReadyState.CONNECTING]: 'bg-yellow-500',
    [ReadyState.OPEN]: 'bg-green-500',
    [ReadyState.CLOSING]: 'bg-orange-500',
    [ReadyState.CLOSED]: 'bg-red-500',
    [ReadyState.UNINSTANTIATED]: 'bg-gray-500',
  }[readyState];
  
  // Handle incoming WebSocket messages
  useEffect(() => {
    if (lastMessage !== null) {
      try {
        const data = JSON.parse(lastMessage.data);
        console.log('Received message:', data);
        
        switch (data.type) {
          case 'STARTED':
            setStatusMessage(data.message || 'Processing started');
            setIsProcessing(true);
            setProgress(0);
            setResults([]);
            setDownloadUrl('');
            break;
            
          case 'PROGRESS':
            setProgress(data.value || 0);
            setProcessedFiles(data.processed || 0);
            setTotalFiles(data.total || 0);
            setStatusMessage(`Processing: ${data.processed || 0}/${data.total || 0} files`);
            break;
            
          case 'MATCH_FOUND':
            // Add new match to results table
            const matchData = data.data || {};
            setResults(prevResults => [...prevResults, {
              id: Date.now() + Math.random(),
              holeCode: matchData.hole_code || '',
              fileName: matchData.file_name || '',
              status: matchData.status || '',
              pdfLink: matchData.pdf_link || ''
            }]);
            break;
            
          case 'COMPLETE':
            setProgress(100);
            setIsProcessing(false);
            setDownloadUrl(data.download_url || '');
            setStatusMessage(data.message || 'Processing completed!');
            break;
            
          case 'ERROR':
            setIsProcessing(false);
            setStatusMessage(`Error: ${data.message || 'Unknown error'}`);
            break;
            
          default:
            console.log('Unknown message type:', data.type);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    }
  }, [lastMessage]);
  
  // Handle file upload
  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (file) {
      setExcelFile(file);
      // Parse Excel file to extract target hole codes (simplified)
      // In real implementation, use a library like xlsx to parse
      setTargetHoleCodes(['HOLE-1', 'HOLE-2', 'HOLE-3', 'HOLE-5', 'HOLE-7']);
    }
  };
  
  // Start processing
  const handleStartProcessing = () => {
    if (!websocketUrl) {
      alert('WebSocket URL is not configured. Please set VITE_WEBSOCKET_URL in your .env file.');
      return;
    }
    
    if (!googleDriveLink) {
      alert('Please enter Google Drive Link');
      return;
    }
    
    // Connect to WebSocket if not connected
    if (!shouldConnect) {
      setShouldConnect(true);
      // Wait a bit for connection to establish
      setTimeout(() => {
        sendProcessingRequest();
      }, 1000);
    } else if (readyState === ReadyState.OPEN) {
      sendProcessingRequest();
    } else {
      alert('WebSocket is not connected. Please wait...');
    }
  };
  
  const sendProcessingRequest = () => {
    const message = {
      action: 'start_scan',
      drive_link: googleDriveLink,
      file_content: excelFile ? 'file_data_here' : '',
      target_hole_codes: targetHoleCodes
    };
    
    console.log('Sending message:', message);
    sendMessage(JSON.stringify(message));
    setStatusMessage('Request sent, waiting for response...');
  };
  
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">
            ISO Piping File Processing Dashboard
          </h1>
          <p className="text-gray-600">
            Real-time processing with WebSocket updates
          </p>
        </div>
        
        {/* Connection Status */}
        <div className="bg-white rounded-lg shadow-md p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className={`w-3 h-3 rounded-full ${connectionColor} animate-pulse`}></div>
              <span className="text-sm font-medium text-gray-700">
                WebSocket: {connectionStatus}
              </span>
            </div>
            {statusMessage && (
              <span className="text-sm text-gray-600">
                {statusMessage}
              </span>
            )}
          </div>
        </div>
        
        {/* Control Panel */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">Control Panel</h2>
          
          <div className="grid grid-cols-1 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Google Drive Link
              </label>
              <input
                type="text"
                value={googleDriveLink}
                onChange={(e) => setGoogleDriveLink(e.target.value)}
                placeholder="https://drive.google.com/drive/folders/1a2b3c4d5e6f7g8h9i0j"
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={isProcessing}
              />
              <p className="text-xs text-gray-500 mt-1">
                Enter the Google Drive folder link containing the files to process
              </p>
            </div>
          </div>
          
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Upload Excel File (Target Hole Codes)
            </label>
            <input
              type="file"
              accept=".xlsx,.xls"
              onChange={handleFileUpload}
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isProcessing}
            />
            {excelFile && (
              <p className="text-sm text-gray-600 mt-2">
                Selected: {excelFile.name} | Target codes: {targetHoleCodes.length}
              </p>
            )}
          </div>
          
          <div className="flex space-x-4">
            <button
              onClick={handleStartProcessing}
              disabled={isProcessing || !googleDriveLink}
              className="px-6 py-3 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {isProcessing ? 'Processing...' : 'Start Processing'}
            </button>
            
            {downloadUrl && (
              <a
                href={downloadUrl}
                download
                className="px-6 py-3 bg-green-600 text-white font-medium rounded-md hover:bg-green-700 transition-colors inline-flex items-center"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download Final Excel
              </a>
            )}
          </div>
        </div>
        
        {/* Progress Bar */}
        {(isProcessing || progress > 0) && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <div className="flex justify-between items-center mb-2">
              <h2 className="text-xl font-semibold text-gray-800">Progress</h2>
              <span className="text-sm font-medium text-gray-700">
                {processedFiles} / {totalFiles} files ({progress}%)
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
              <div
                className="bg-blue-600 h-4 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${progress}%` }}
              >
                <div className="h-full w-full bg-blue-400 opacity-50 animate-pulse"></div>
              </div>
            </div>
          </div>
        )}
        
        {/* Results Table */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            Live Results {results.length > 0 && `(${results.length} matches)`}
          </h2>
          
          {results.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <svg className="w-16 h-16 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p>No matches found yet. Start processing to see results.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Hole Code
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Drawing Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {results.map((result) => (
                    <tr key={result.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {result.holeCode}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                        {result.fileName}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                          {result.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                        {result.pdfLink && (
                          <a
                            href={result.pdfLink}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 font-medium"
                          >
                            View PDF →
                          </a>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
