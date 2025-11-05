'use client';

import { useState, useEffect } from 'react';

export default function VOFCProcessingDashboard() {
  const [status, setStatus] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);
  const [processing, setProcessing] = useState(false);

  const loadStatus = async () => {
    try {
      const response = await fetch('/api/dashboard/status');
      const data = await response.json();
      if (data.success) {
        setStatus(data.status);
        setLoading(false);
      }
    } catch (error) {
      console.error('Failed to load status:', error);
    }
  };

  // Load status every 5 seconds
  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  // Connect to log stream
  useEffect(() => {
    const eventSource = new EventSource('/api/dashboard/stream?mode=live');
    
    eventSource.onopen = () => {
      setConnected(true);
      addLog('🔌 Connected to live monitoring stream', 'system');
    };

    eventSource.onmessage = (event) => {
      const match = event.data.match(/\[([^\]]+)\] \[([^\]]+)\] (.+)/);
      if (match) {
        const [, timestamp, type, message] = match;
        addLog(message, type.toLowerCase(), timestamp);
      } else {
        addLog(event.data, 'info');
      }
    };

    eventSource.onerror = (error) => {
      setConnected(false);
      addLog('❌ Connection lost', 'error');
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, []);

  const addLog = (message, type, timestamp) => {
    setLogs(prev => {
      const newLog = { message, type, timestamp: timestamp || new Date().toISOString() };
      const updated = [newLog, ...prev].slice(0, 100); // Keep last 100 logs
      return updated;
    });
  };

  const getServiceStatus = (service) => {
    if (!service || !status?.services || !status.services[service]) {
      return { color: 'gray', text: 'Unknown', icon: '❓' };
    }
    
    const svc = status.services[service];
    const serviceStatus = svc?.status || 'unknown';
    
    switch (serviceStatus) {
      case 'online':
      case 'configured':
      case 'running':
        return { color: 'green', text: 'Online', icon: '✅' };
      case 'error':
        return { color: 'yellow', text: 'Error', icon: '⚠️' };
      case 'offline':
      case 'stopped':
      case 'not_configured':
        return { color: 'red', text: 'Offline', icon: '❌' };
      default:
        return { color: 'gray', text: 'Unknown', icon: '❓' };
    }
  };

  const getLogColor = (type) => {
    switch (type) {
      case 'error': return 'text-red-600 bg-red-50';
      case 'warning': return 'text-yellow-600 bg-yellow-50';
      case 'success': return 'text-green-600 bg-green-50';
      case 'system': return 'text-blue-600 bg-blue-50';
      default: return 'text-gray-700 bg-gray-50';
    }
  };

  const handleProcessPending = async () => {
    if (processing) return;
    
    setProcessing(true);
    addLog('🔄 Starting batch processing of pending files...', 'system');
    
    // Try Flask backend first (processes files directly from incoming folder)
    try {
      addLog('📡 Attempting to connect to Flask backend...', 'system');
      const flaskResponse = await fetch('/api/proxy/flask/process-pending', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      const flaskResult = await flaskResponse.json();
      
      if (flaskResult.success) {
        const processedCount = flaskResult.processed || 0;
        addLog(`✅ Flask processing complete: ${processedCount} file(s) processed`, 'success');
        if (flaskResult.flask_response?.processed) {
          flaskResult.flask_response.processed.forEach(subId => {
            addLog(`✅ Submission ${subId} processed successfully`, 'success');
          });
        }
        // Reload status after a short delay
        setTimeout(() => {
          loadStatus();
        }, 3000);
        setProcessing(false);
        return;
      } else {
        addLog(`⚠️ Flask processing failed: ${flaskResult.error || 'Unknown error'}`, 'warning');
        if (flaskResult.hint) {
          addLog(`💡 Hint: ${flaskResult.hint}`, 'warning');
        }
        // Fall through to try Next.js API route
      }
    } catch (flaskError) {
      console.warn('Flask backend not available, trying Next.js API route:', flaskError);
      addLog('⚠️ Flask backend not available, trying alternative method...', 'warning');
    }
    
    // Fallback: Try Next.js API route (processes files from database)
    try {
      addLog('📋 Attempting to process via Next.js API...', 'system');
      const response = await fetch('/api/documents/process-pending', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      const result = await response.json();
      
      if (result.success) {
        addLog(`✅ Processing complete: ${result.processed || 0} files processed, ${result.failed || 0} failed`, 'success');
        if (result.results && result.results.length > 0) {
          result.results.forEach(r => {
            if (r.success) {
              addLog(`✅ ${r.filename}: ${r.count || 0} vulnerabilities extracted`, 'success');
            } else {
              addLog(`❌ ${r.filename}: ${r.error || 'Failed'}`, 'error');
            }
          });
        } else if (result.message) {
          addLog(`ℹ️ ${result.message}`, 'info');
        }
        // Reload status after a short delay
        setTimeout(() => {
          loadStatus();
        }, 2000);
      } else {
        addLog(`❌ Processing failed: ${result.error || 'Unknown error'}`, 'error');
      }
    } catch (error) {
      console.error('Error processing pending files:', error);
      addLog(`❌ Error: ${error.message}`, 'error');
    } finally {
      setProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Service Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Flask Server (Python) */}
        <ServiceCard
          title="Flask Server (Python)"
          service={getServiceStatus('flask')}
          details={status?.services.flask}
          icon="🐍"
        />
        
        {/* Ollama Service */}
        <ServiceCard
          title="Ollama API"
          service={getServiceStatus('ollama')}
          details={status?.services.ollama}
          icon="🤖"
        />
        
        {/* Supabase */}
        <ServiceCard
          title="Supabase"
          service={getServiceStatus('supabase')}
          details={status?.services.supabase}
          icon="🗄️"
        />
        
        {/* Connection Status */}
        <ServiceCard
          title="Live Stream"
          service={connected ? { color: 'green', text: 'Connected', icon: '✅' } : { color: 'red', text: 'Disconnected', icon: '❌' }}
          details={{ stream: connected ? 'Active' : 'Inactive' }}
          icon="📡"
        />
      </div>

      {/* File Processing Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatCard label="Incoming" value={status?.files?.incoming || 0} color="yellow" icon="📥" />
        <StatCard label="Processed" value={status?.files?.library || 0} color="green" icon="📚" />
        <StatCard label="Extracted Text" value={status?.files?.extracted_text || 0} color="blue" icon="📄" />
        <StatCard label="Errors" value={status?.files?.errors || 0} color="red" icon="❌" />
        <StatCard label="Active Jobs" value={status?.processing?.active_jobs || 0} color={status?.processing?.active_jobs > 0 ? 'yellow' : 'gray'} icon="⚙️" />
      </div>

      {/* Process Pending Files Button */}
      {(status?.files?.incoming > 0 || status?.processing?.active_jobs > 0) && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-gray-900 mb-2">File Processing Control</h2>
              <p className="text-sm text-gray-600">
                {status?.files?.incoming || 0} file(s) waiting in incoming folder. Click to start processing.
              </p>
            </div>
            <button
              onClick={handleProcessPending}
              disabled={processing}
              className={`px-6 py-3 rounded-lg font-semibold text-white transition-all ${
                processing
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800'
              }`}
            >
              {processing ? (
                <>
                  <span className="inline-block animate-spin mr-2">⏳</span>
                  Processing...
                </>
              ) : (
                <>
                  🚀 Process Pending Files ({status?.files?.incoming || 0})
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Real-time Activity Log */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-gray-900">Real-time Activity</h2>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            connected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
          }`}>
            {connected ? '🟢 Live' : '🔴 Disconnected'}
          </span>
        </div>
        <div className="bg-gray-900 text-green-400 font-mono text-sm p-4 rounded-lg h-96 overflow-y-auto" style={{ fontFamily: 'monospace' }}>
          {logs.length === 0 ? (
            <div className="text-gray-500">Waiting for activity...</div>
          ) : (
            logs.map((log, idx) => (
              <div key={idx} className={`mb-1 px-2 py-1 rounded ${getLogColor(log.type)}`}>
                <span className="text-gray-400">[{new Date(log.timestamp).toLocaleTimeString()}]</span>{' '}
                <span className={log.type === 'error' ? 'text-red-400' : log.type === 'success' ? 'text-green-400' : ''}>
                  {log.message}
                </span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Python & Flask Service Information */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Python Service */}
        {status?.python && (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
              <span>🐍</span> Python Runtime
            </h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Status</span>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  status.python.status === 'running' || status.python.runtime_status === 'running'
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-red-100 text-red-800'
                }`}>
                  {status.python.status === 'running' || status.python.runtime_status === 'running' ? '✅ Running' : '❌ Stopped'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Version</span>
                <span className="text-sm font-mono font-semibold">{status.python.version || 'N/A'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Model</span>
                <span className="text-sm font-semibold">{status.python.model || 'N/A'}</span>
              </div>
              {status.python.executable && status.python.executable !== 'unknown' && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Executable</span>
                  <span className="text-xs font-mono text-gray-500 truncate ml-2">{status.python.executable}</span>
                </div>
              )}
              {status.python.platform && Object.keys(status.python.platform).length > 0 && (
                <div className="pt-2 border-t border-gray-200">
                  <div className="text-xs text-gray-500 space-y-1">
                    <div>Platform: {status.python.platform.system} {status.python.platform.release}</div>
                    {status.python.platform.machine && <div>Architecture: {status.python.platform.machine}</div>}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Flask Service */}
        {status?.flask && (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
              <span>🔧</span> Flask Server
            </h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Version</span>
                <span className="text-sm font-mono font-semibold">{status.flask.version || 'N/A'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Environment</span>
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  status.flask.environment === 'production' ? 'bg-blue-100 text-blue-800' : 'bg-yellow-100 text-yellow-800'
                }`}>
                  {status.flask.environment || 'N/A'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Debug Mode</span>
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  status.flask.debug ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                }`}>
                  {status.flask.debug ? '⚠️ Enabled' : '✅ Disabled'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Ollama Models */}
      {status?.services?.ollama_models && status.services.ollama_models.length > 0 && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
            <span>🤖</span> Available Ollama Models
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {status.services.ollama_models.map((model, idx) => (
              <div key={idx} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                <div className="font-mono text-sm font-semibold text-gray-900">{model}</div>
                <div className="text-xs text-gray-500 mt-1">Model {idx + 1}</div>
              </div>
            ))}
          </div>
          {status.services.ollama_base_url && (
            <div className="mt-4 text-xs text-gray-500">
              Ollama Base URL: <span className="font-mono">{status.services.ollama_base_url}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ServiceCard({ title, service, details, icon }) {
  const bgColor = {
    green: 'bg-green-50 border-green-200',
    yellow: 'bg-yellow-50 border-yellow-200',
    red: 'bg-red-50 border-red-200',
    gray: 'bg-gray-50 border-gray-200'
  }[service.color] || 'bg-gray-50 border-gray-200';

  return (
    <div className={`border-2 rounded-lg p-4 ${bgColor}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <span className="text-2xl">{icon}</span>
          <h3 className="font-semibold text-gray-900">{title}</h3>
        </div>
        <span className={`px-2 py-1 rounded text-xs font-medium ${
          service.color === 'green' ? 'bg-green-200 text-green-800' :
          service.color === 'yellow' ? 'bg-yellow-200 text-yellow-800' :
          service.color === 'red' ? 'bg-red-200 text-red-800' :
          'bg-gray-200 text-gray-800'
        }`}>
          {service.icon} {service.text}
        </span>
      </div>
      {details && (
        <div className="text-xs text-gray-600 space-y-1 mt-2">
          {details.url && <div>URL: <span className="font-mono">{details.url}</span></div>}
          {details.models_count !== undefined && <div>Models: {details.models_count}</div>}
          {details.error && <div className="text-red-600">Error: {details.error}</div>}
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, color, icon }) {
  const bgColor = {
    yellow: 'bg-yellow-50 border-yellow-200',
    green: 'bg-green-50 border-green-200',
    blue: 'bg-blue-50 border-blue-200',
    red: 'bg-red-50 border-red-200',
    gray: 'bg-gray-50 border-gray-200'
  }[color] || 'bg-gray-50 border-gray-200';

  return (
    <div className={`border rounded-lg p-4 ${bgColor}`}>
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm text-gray-600 mb-1">{label}</div>
          <div className="text-2xl font-bold text-gray-900">{value}</div>
        </div>
        <span className="text-3xl">{icon}</span>
      </div>
    </div>
  );
}
