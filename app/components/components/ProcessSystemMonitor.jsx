'use client';

import { useState, useEffect } from 'react';

export default function ProcessSystemMonitor() {
  const [systemData, setSystemData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedView, setSelectedView] = useState('overview');

  useEffect(() => {
    loadSystemData();
    
    if (autoRefresh) {
      const interval = setInterval(loadSystemData, 10000); // Refresh every 10 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const loadSystemData = async () => {
    try {
      const response = await fetch('/api/monitor/system');
      const data = await response.json();
      
      if (data.success) {
        setSystemData(data.system);
        setError('');
      } else {
        setError(data.error || 'Failed to load system data');
      }
    } catch (err) {
      setError('Error loading system data: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'online': return 'text-green-600 bg-green-100';
      case 'offline': return 'text-red-600 bg-red-100';
      case 'processing': return 'text-yellow-600 bg-yellow-100';
      case 'error': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'online': return '✅';
      case 'offline': return '❌';
      case 'processing': return '⏳';
      case 'error': return '⚠️';
      default: return '❓';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading system monitor...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-600 text-xl mb-4">⚠️ Error</div>
          <p className="text-gray-600">{error}</p>
          <button 
            onClick={loadSystemData}
            className="btn btn-primary mt-4"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-blue-900 text-white p-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold">Process System Monitor</h1>
              <p className="text-blue-200">Complete system monitoring and process mapping</p>
            </div>
            <div className="flex items-center space-x-4">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="mr-2"
                />
                <span className="text-sm">Auto-refresh</span>
              </label>
              <button
                onClick={loadSystemData}
                className="btn btn-secondary btn-sm"
              >
                <i className="fas fa-sync-alt mr-2"></i>
                Refresh
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6">
        {/* View Toggle */}
        <div className="mb-6">
          <div className="flex space-x-4">
            <button
              onClick={() => setSelectedView('overview')}
              className={`px-4 py-2 rounded-lg font-medium ${
                selectedView === 'overview' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              System Overview
            </button>
            <button
              onClick={() => setSelectedView('processes')}
              className={`px-4 py-2 rounded-lg font-medium ${
                selectedView === 'processes' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              Process Map
            </button>
            <button
              onClick={() => setSelectedView('performance')}
              className={`px-4 py-2 rounded-lg font-medium ${
                selectedView === 'performance' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              Performance
            </button>
            <button
              onClick={() => setSelectedView('alerts')}
              className={`px-4 py-2 rounded-lg font-medium ${
                selectedView === 'alerts' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              Alerts & Logs
            </button>
          </div>
        </div>

        {/* System Overview */}
        {selectedView === 'overview' && (
          <div className="space-y-6">
            {/* System Health Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="card">
                <div className="card-header">
                  <h3 className="text-lg font-semibold">Database</h3>
                </div>
                <div className="card-body">
                  <div className="flex items-center mb-2">
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(systemData?.database?.status)}`}>
                      {getStatusIcon(systemData?.database?.status)} {systemData?.database?.status || 'Unknown'}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600">
                    <p>Connections: {systemData?.database?.connections || 'N/A'}</p>
                    <p>Response: {systemData?.database?.response_time || 'N/A'}ms</p>
                  </div>
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <h3 className="text-lg font-semibold">Ollama Service</h3>
                </div>
                <div className="card-body">
                  <div className="flex items-center mb-2">
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(systemData?.ollama?.status)}`}>
                      {getStatusIcon(systemData?.ollama?.status)} {systemData?.ollama?.status || 'Unknown'}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600">
                    <p>Model: {systemData?.ollama?.model || 'N/A'}</p>
                    <p>Queue: {systemData?.ollama?.queue_size || 'N/A'}</p>
                  </div>
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <h3 className="text-lg font-semibold">File System</h3>
                </div>
                <div className="card-body">
                  <div className="flex items-center mb-2">
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(systemData?.filesystem?.status)}`}>
                      {getStatusIcon(systemData?.filesystem?.status)} {systemData?.filesystem?.status || 'Unknown'}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600">
                    <p>Space: {systemData?.filesystem?.free_space || 'N/A'}</p>
                    <p>Files: {systemData?.filesystem?.total_files || 'N/A'}</p>
                  </div>
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <h3 className="text-lg font-semibold">API Server</h3>
                </div>
                <div className="card-body">
                  <div className="flex items-center mb-2">
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(systemData?.api?.status)}`}>
                      {getStatusIcon(systemData?.api?.status)} {systemData?.api?.status || 'Unknown'}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600">
                    <p>Uptime: {systemData?.api?.uptime || 'N/A'}</p>
                    <p>Requests: {systemData?.api?.requests_per_minute || 'N/A'}/min</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Processing Pipeline Status */}
            <div className="card">
              <div className="card-header">
                <h3 className="text-lg font-semibold">Processing Pipeline</h3>
              </div>
              <div className="card-body">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-blue-600">{systemData?.pipeline?.pending || 0}</div>
                    <div className="text-sm text-gray-600">Pending</div>
                  </div>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-yellow-600">{systemData?.pipeline?.processing || 0}</div>
                    <div className="text-sm text-gray-600">Processing</div>
                  </div>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-green-600">{systemData?.pipeline?.completed || 0}</div>
                    <div className="text-sm text-gray-600">Completed</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Process Map */}
        {selectedView === 'processes' && (
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-semibold">Process Flow Map</h3>
            </div>
            <div className="card-body">
              <div className="bg-gray-50 p-6 rounded-lg">
                <div className="flex items-center justify-between mb-8">
                  <div className="text-center">
                    <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-2">
                      <i className="fas fa-upload text-blue-600 text-2xl"></i>
                    </div>
                    <p className="text-sm font-medium">Document Upload</p>
                    <p className="text-xs text-gray-600">{systemData?.pipeline?.pending || 0} pending</p>
                  </div>
                  
                  <div className="flex-1 h-1 bg-gray-300 mx-4 relative">
                    <div className="absolute inset-0 bg-blue-500 rounded-full" style={{width: '60%'}}></div>
                  </div>
                  
                  <div className="text-center">
                    <div className="w-20 h-20 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-2">
                      <i className="fas fa-cog text-yellow-600 text-2xl"></i>
                    </div>
                    <p className="text-sm font-medium">Processing</p>
                    <p className="text-xs text-gray-600">{systemData?.pipeline?.processing || 0} active</p>
                  </div>
                  
                  <div className="flex-1 h-1 bg-gray-300 mx-4 relative">
                    <div className="absolute inset-0 bg-yellow-500 rounded-full" style={{width: '40%'}}></div>
                  </div>
                  
                  <div className="text-center">
                    <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-2">
                      <i className="fas fa-check text-green-600 text-2xl"></i>
                    </div>
                    <p className="text-sm font-medium">Completed</p>
                    <p className="text-xs text-gray-600">{systemData?.pipeline?.completed || 0} done</p>
                  </div>
                </div>

                {/* Detailed Process Steps */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-8">
                  <div className="bg-white p-4 rounded-lg border">
                    <h4 className="font-medium text-sm mb-2">1. Document Reception</h4>
                    <p className="text-xs text-gray-600">Files uploaded to docs folder</p>
                    <div className="mt-2 text-xs text-green-600">✅ Active</div>
                  </div>
                  
                  <div className="bg-white p-4 rounded-lg border">
                    <h4 className="font-medium text-sm mb-2">2. Ollama Analysis</h4>
                    <p className="text-xs text-gray-600">AI processing with Ollama</p>
                    <div className="mt-2 text-xs text-yellow-600">⏳ Processing</div>
                  </div>
                  
                  <div className="bg-white p-4 rounded-lg border">
                    <h4 className="font-medium text-sm mb-2">3. Data Extraction</h4>
                    <p className="text-xs text-gray-600">Vulnerabilities and OFCs extracted</p>
                    <div className="mt-2 text-xs text-blue-600">🔄 Queued</div>
                  </div>
                  
                  <div className="bg-white p-4 rounded-lg border">
                    <h4 className="font-medium text-sm mb-2">4. Database Storage</h4>
                    <p className="text-xs text-gray-600">Results stored in Supabase</p>
                    <div className="mt-2 text-xs text-green-600">✅ Complete</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Performance Metrics */}
        {selectedView === 'performance' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="card">
              <div className="card-header">
                <h3 className="text-lg font-semibold">Processing Performance</h3>
              </div>
              <div className="card-body">
                <div className="space-y-4">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Avg Processing Time</span>
                    <span className="font-medium">{systemData?.performance?.avg_processing_time || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Success Rate</span>
                    <span className="font-medium text-green-600">{systemData?.performance?.success_rate || 'N/A'}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Throughput</span>
                    <span className="font-medium">{systemData?.performance?.throughput || 'N/A'} docs/hour</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h3 className="text-lg font-semibold">System Resources</h3>
              </div>
              <div className="card-body">
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-sm text-gray-600">CPU Usage</span>
                      <span className="text-sm font-medium">{systemData?.resources?.cpu || 'N/A'}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div className="bg-blue-600 h-2 rounded-full" style={{width: `${systemData?.resources?.cpu || 0}%`}}></div>
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-sm text-gray-600">Memory Usage</span>
                      <span className="text-sm font-medium">{systemData?.resources?.memory || 'N/A'}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div className="bg-green-600 h-2 rounded-full" style={{width: `${systemData?.resources?.memory || 0}%`}}></div>
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-sm text-gray-600">Disk Usage</span>
                      <span className="text-sm font-medium">{systemData?.resources?.disk || 'N/A'}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div className="bg-yellow-600 h-2 rounded-full" style={{width: `${systemData?.resources?.disk || 0}%`}}></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Alerts and Logs */}
        {selectedView === 'alerts' && (
          <div className="space-y-6">
            <div className="card">
              <div className="card-header">
                <h3 className="text-lg font-semibold">System Alerts</h3>
              </div>
              <div className="card-body">
                {systemData?.alerts?.length > 0 ? (
                  <div className="space-y-2">
                    {systemData.alerts.map((alert, idx) => (
                      <div key={idx} className={`p-3 rounded-lg ${
                        alert.level === 'error' ? 'bg-red-50 border-red-200' :
                        alert.level === 'warning' ? 'bg-yellow-50 border-yellow-200' :
                        'bg-blue-50 border-blue-200'
                      }`}>
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium text-sm">{alert.message}</p>
                            <p className="text-xs text-gray-600 mt-1">{alert.timestamp}</p>
                          </div>
                          <span className={`px-2 py-1 rounded text-xs ${
                            alert.level === 'error' ? 'bg-red-100 text-red-800' :
                            alert.level === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-blue-100 text-blue-800'
                          }`}>
                            {alert.level}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-600 text-center py-4">No alerts at this time</p>
                )}
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h3 className="text-lg font-semibold">Recent Activity</h3>
              </div>
              <div className="card-body">
                <div className="space-y-2">
                  {systemData?.activity?.slice(0, 10).map((activity, idx) => (
                    <div key={idx} className="flex justify-between items-center py-2 border-b border-gray-100">
                      <div>
                        <p className="text-sm font-medium">{activity.action}</p>
                        <p className="text-xs text-gray-600">{activity.details}</p>
                      </div>
                      <span className="text-xs text-gray-500">{activity.timestamp}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Last Updated */}
        <div className="mt-6 text-center text-sm text-gray-500">
          Last updated: {systemData?.timestamp ? new Date(systemData.timestamp).toLocaleString() : 'Never'}
        </div>
      </div>
    </div>
  );
}
