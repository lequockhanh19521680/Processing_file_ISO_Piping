import React, { useState, useEffect, useRef } from "react";
import useWebSocket, { ReadyState } from "react-use-websocket";
import * as ExcelJS from "exceljs";

const Dashboard = () => {
  // WebSocket configuration from environment variable with fallback
  // Set VITE_WEBSOCKET_URL in .env file or the connection will fail
  const websocketUrl = import.meta.env.VITE_WEBSOCKET_URL || "";
  const [shouldConnect, setShouldConnect] = useState(!!websocketUrl);

  // Form state
  const [googleDriveLink, setGoogleDriveLink] = useState("");
  const [excelFile, setExcelFile] = useState(null);
  const [targetHoleCodes, setTargetHoleCodes] = useState([]);

  // Processing state
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [processedFiles, setProcessedFiles] = useState(0);
  const [totalFiles, setTotalFiles] = useState(0);
  const [results, setResults] = useState([]);
  const [downloadUrl, setDownloadUrl] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [liveScanLog, setLiveScanLog] = useState([]);
  const [validationError, setValidationError] = useState("");

  // WebSocket connection
  const { sendMessage, lastMessage, readyState } = useWebSocket(
    websocketUrl,
    {
      shouldReconnect: () => true,
      reconnectAttempts: 10,
      reconnectInterval: 3000,
      heartbeat: {
        message: JSON.stringify({ action: 'ping' }),
        returnMessage: 'pong',
        timeout: 60000,
        interval: 25000,
      },
    },
    shouldConnect,
  );

  // Connection status
  const connectionStatus = {
    [ReadyState.CONNECTING]: "Connecting",
    [ReadyState.OPEN]: "Connected",
    [ReadyState.CLOSING]: "Closing",
    [ReadyState.CLOSED]: "Disconnected",
    [ReadyState.UNINSTANTIATED]: "Uninstantiated",
  }[readyState];

  const connectionColor = {
    [ReadyState.CONNECTING]: "bg-yellow-500",
    [ReadyState.OPEN]: "bg-green-500",
    [ReadyState.CLOSING]: "bg-orange-500",
    [ReadyState.CLOSED]: "bg-red-500",
    [ReadyState.UNINSTANTIATED]: "bg-gray-500",
  }[readyState];

  // Handle incoming WebSocket messages
  useEffect(() => {
    if (lastMessage !== null) {
      try {
        const data = JSON.parse(lastMessage.data);
        console.log("Received message:", data);

        switch (data.type) {
          case "STARTED":
            setStatusMessage(data.message || "Processing started");
            setIsProcessing(true);
            setProgress(0);
            setResults([]);
            setDownloadUrl("");
            setLiveScanLog([]);
            setValidationError("");
            // Set total files from STARTED event
            if (data.total_files) {
              setTotalFiles(data.total_files);
              setProcessedFiles(0);
            }
            break;

          case "PROGRESS":
            // Update progress ensuring it never goes backward
            const newProgress = data.value || 0;
            setProgress(prevProgress => Math.max(prevProgress, newProgress));
            
            const newProcessed = data.processed || 0;
            const newTotal = data.total || 0;
            
            setProcessedFiles(prevProcessed => Math.max(prevProcessed, newProcessed));
            setTotalFiles(prevTotal => Math.max(prevTotal, newTotal));
            
            setStatusMessage(
              `Processing: ${newProcessed}/${newTotal} files`,
            );
            
            // Add to live scan log (show last file being processed)
            if (data.file_name) {
              setLiveScanLog(prevLog => [
                { 
                  id: Date.now() + Math.random(), 
                  fileName: data.file_name, 
                  timestamp: new Date().toLocaleTimeString(),
                  status: 'processing'
                },
                ...prevLog.slice(0, 49) // Keep last 50 entries
              ]);
            }
            break;

          case "MATCH_FOUND":
            // Add new match to results table
            const matchData = data.data || {};
            setResults((prevResults) => [
              ...prevResults,
              {
                id: Date.now() + Math.random(),
                holeCode: matchData.hole_code || "",
                fileName: matchData.file_name || "",
                status: matchData.status || "",
                pdfLink: matchData.pdf_link || "",
              },
            ]);
            
            // Add to live scan log
            setLiveScanLog(prevLog => [
              { 
                id: Date.now() + Math.random(), 
                fileName: matchData.file_name || "Unknown", 
                timestamp: new Date().toLocaleTimeString(),
                status: 'match_found',
                holeCode: matchData.hole_code
              },
              ...prevLog.slice(0, 49) // Keep last 50 entries
            ]);
            break;

          case "COMPLETE":
            setProgress(100);
            setIsProcessing(false);
            setDownloadUrl(data.download_url || "");
            setStatusMessage(data.message || "Processing completed successfully!");
            break;

          case "ERROR":
            setIsProcessing(false);
            setStatusMessage(`Error: ${data.message || "Unknown error"}`);
            break;

          default:
            console.log("Unknown message type:", data.type);
        }
      } catch (error) {
        console.error("Error parsing WebSocket message:", error);
      }
    }
  }, [lastMessage]);

  // Handle file upload
  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (file) {
      setExcelFile(file);
      
      try {
        // Parse Excel file to extract target hole codes
        const arrayBuffer = await file.arrayBuffer();
        const workbook = new ExcelJS.Workbook();
        await workbook.xlsx.load(arrayBuffer);
        
        // Assume first worksheet contains hole codes in the first column
        const worksheet = workbook.worksheets[0];
        const holeCodes = [];
        
        worksheet.eachRow((row, rowNumber) => {
          // Skip header row
          if (rowNumber > 1) {
            const cellValue = row.getCell(1).value;
            if (cellValue) {
              // Convert to string and trim
              const holeCode = String(cellValue).trim();
              if (holeCode) {
                holeCodes.push(holeCode);
              }
            }
          }
        });
        
        setTargetHoleCodes(holeCodes);
        console.log(`Extracted ${holeCodes.length} hole codes from Excel file`);
      } catch (error) {
        console.error("Error parsing Excel file:", error);
        alert("Failed to parse Excel file. Please ensure it's a valid Excel file with hole codes in the first column.");
      }
    }
  };

  // Start processing
  const handleStartProcessing = () => {
    // Clear previous validation error
    setValidationError("");
    
    if (!websocketUrl) {
      setValidationError(
        "WebSocket URL is not configured. Please set VITE_WEBSOCKET_URL in your .env file.",
      );
      return;
    }

    // Validate Google Drive URL
    if (!googleDriveLink) {
      setValidationError("Please enter a Google Drive Link");
      return;
    }
    
    if (!googleDriveLink.includes("drive.google.com")) {
      setValidationError("Please enter a valid Google Drive URL (must contain 'drive.google.com')");
      return;
    }

    // Validate Excel file has been uploaded and processed
    if (!excelFile || targetHoleCodes.length === 0) {
      setValidationError("Please upload an Excel file with target hole codes");
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
      setValidationError("WebSocket is not connected. Please wait...");
    }
  };

  const sendProcessingRequest = () => {
    const message = {
      action: "start_scan",
      drive_link: googleDriveLink,
      target_hole_codes: targetHoleCodes,
    };

    console.log("Sending message:", message);
    sendMessage(JSON.stringify(message));
    setStatusMessage("Request sent, waiting for response...");
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
              <div
                className={`w-3 h-3 rounded-full ${connectionColor} animate-pulse`}
              ></div>
              <span className="text-sm font-medium text-gray-700">
                WebSocket: {connectionStatus}
              </span>
            </div>
            {statusMessage && (
              <span className="text-sm text-gray-600">{statusMessage}</span>
            )}
          </div>
          {validationError && (
            <div className="mt-3 p-3 bg-red-100 border border-red-400 text-red-700 rounded-md text-sm">
              {validationError}
            </div>
          )}
        </div>

        {/* Control Panel */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            Control Panel
          </h2>

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
                Enter the Google Drive folder link containing the files to
                process
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
                Selected: {excelFile.name} | Target codes:{" "}
                {targetHoleCodes.length}
              </p>
            )}
          </div>

          <div className="flex space-x-4">
            <button
              onClick={handleStartProcessing}
              disabled={isProcessing || !googleDriveLink || !websocketUrl}
              className="px-6 py-3 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center"
            >
              {isProcessing ? (
                <>
                  <svg
                    className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  Scanning...
                </>
              ) : (
                "Start Scan"
              )}
            </button>

            {downloadUrl && (
              <a
                href={downloadUrl}
                download
                className="px-6 py-3 bg-green-600 text-white font-medium rounded-md hover:bg-green-700 transition-colors inline-flex items-center"
              >
                <svg
                  className="w-5 h-5 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                  />
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

        {/* Live Scan Log */}
        {(isProcessing || liveScanLog.length > 0) && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">
              Live Scan Log {liveScanLog.length > 0 && `(${liveScanLog.length} entries)`}
            </h2>
            <div className="max-h-64 overflow-y-auto border border-gray-200 rounded-md">
              {liveScanLog.length === 0 ? (
                <div className="text-center py-8 text-gray-500 text-sm">
                  Waiting for files to be processed...
                </div>
              ) : (
                <div className="divide-y divide-gray-100">
                  {liveScanLog.map((entry) => (
                    <div
                      key={entry.id}
                      className={`px-4 py-2 hover:bg-gray-50 text-sm ${
                        entry.status === 'match_found' 
                          ? 'bg-green-50 border-l-4 border-green-500' 
                          : ''
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-gray-900 truncate">
                            {entry.fileName}
                          </p>
                          {entry.holeCode && (
                            <p className="text-xs text-green-600 mt-1">
                              Match: {entry.holeCode}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center ml-4 space-x-2">
                          {entry.status === 'match_found' && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                              Match
                            </span>
                          )}
                          <span className="text-xs text-gray-500 whitespace-nowrap">
                            {entry.timestamp}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Showing real-time file processing activity. Latest entries appear at the top.
            </p>
          </div>
        )}

        {/* Completion Message */}
        {!isProcessing && downloadUrl && (
          <div className="bg-green-50 border-l-4 border-green-500 rounded-lg shadow-md p-6 mb-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg
                  className="h-8 w-8 text-green-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <div className="ml-4 flex-1">
                <h3 className="text-lg font-semibold text-green-800">
                  Processing Complete!
                </h3>
                <p className="mt-1 text-sm text-green-700">
                  Successfully processed {totalFiles} files and found {results.length} matches.
                  Your report is ready for download.
                </p>
              </div>
              <div className="ml-4">
                <a
                  href={downloadUrl}
                  download
                  className="inline-flex items-center px-4 py-2 bg-green-600 text-white font-medium rounded-md hover:bg-green-700 transition-colors"
                >
                  <svg
                    className="w-5 h-5 mr-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                    />
                  </svg>
                  Download Report
                </a>
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
              <svg
                className="w-16 h-16 mx-auto mb-4 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
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
                    <tr
                      key={result.id}
                      className="hover:bg-gray-50 transition-colors"
                    >
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
