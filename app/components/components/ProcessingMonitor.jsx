'use client';

import { useState, useEffect } from 'react';

export default function ProcessingMonitor() {
  const [monitoringData, setMonitoringData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    loadMonitoringData();
    
    if (autoRefresh) {
      const interval = setInterval(loadMonitoringData, 5000); // Refresh every 5 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const loadMonitoringData = async () => {
    try {
      const response = await fetch('/api/monitor/processing');
      const data = await response.json();
      
      if (data.success) {
        setMonitoringData(data.monitoring);
        setError('');
      } else {
        setError(data.error || 'Failed to load monitoring data');
      }
    } catch (err) {
      setError('Error loading monitoring data: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'online': return 'text-green-600 bg-green-100';
      case 'offline': return 'text-red-600 bg-red-100';
      case 'processing': return 'text-yellow-600 bg-yellow-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'online': return '✅';
      case 'offline': return '❌';
      case 'processing': return '⏳';
      default: return '❓';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading monitoring data...</p>
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
            onClick={loadMonitoringData}
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
              <h1 className="text-2xl font-bold">Document Processing Monitor</h1>
              <p className="text-blue-200">Real-time monitoring of document processing pipeline</p>
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
                onClick={loadMonitoringData}
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
        {/* System Status Overview */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {/* Ollama Service Status */}
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-semibold">Ollama Service</h3>
            </div>
            <div className="card-body">
              <div className="flex items-center mb-4">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(monitoringData?.ollama_service?.status)}`}>
                  {getStatusIcon(monitoringData?.ollama_service?.status)} {monitoringData?.ollama_service?.status || 'Unknown'}
                </span>
              </div>
              <div className="text-sm text-gray-600 space-y-1">
                <p><strong>URL:</strong> {monitoringData?.ollama_service?.url || 'N/A'}</p>
                <p><strong>Model:</strong> {monitoringData?.ollama_service?.model || 'N/A'}</p>
                {monitoringData?.ollama_service?.target_model_found && (
                  <p className="text-green-600">✅ Target model available</p>
                )}
                {monitoringData?.ollama_service?.error && (
                  <p className="text-red-600">❌ {monitoringData.ollama_service.error}</p>
                )}
              </div>
            </div>
          </div>

          {/* Submission Processing Status */}
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-semibold">Submissions</h3>
            </div>
            <div className="card-body">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-gray-600">Total</p>
                  <p className="text-2xl font-bold">{monitoringData?.submissions?.analysis?.total || 0}</p>
                </div>
                <div>
                  <p className="text-gray-600">Pending</p>
                  <p className="text-2xl font-bold text-yellow-600">{monitoringData?.submissions?.analysis?.pending || 0}</p>
                </div>
                <div>
                  <p className="text-gray-600">Processed</p>
                  <p className="text-2xl font-bold text-green-600">{monitoringData?.submissions?.analysis?.processed || 0}</p>
                </div>
                <div>
                  <p className="text-gray-600">With Ollama</p>
                  <p className="text-2xl font-bold text-blue-600">{monitoringData?.submissions?.analysis?.with_ollama_results || 0}</p>
                </div>
              </div>
            </div>
          </div>

          {/* File Processing Status */}
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-semibold">File Processing</h3>
            </div>
            <div className="card-body">
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span>📁 Docs</span>
                  <span className="font-medium">{monitoringData?.file_processing?.docs?.count || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>⏳ Processing</span>
                  <span className="font-medium text-yellow-600">{monitoringData?.file_processing?.processing?.count || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>✅ Completed</span>
                  <span className="font-medium text-green-600">{monitoringData?.file_processing?.completed?.count || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>❌ Failed</span>
                  <span className="font-medium text-red-600">{monitoringData?.file_processing?.failed?.count || 0}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Submissions */}
        <div className="card mb-8">
          <div className="card-header">
            <h3 className="text-lg font-semibold">Recent Submissions</h3>
          </div>
          <div className="card-body">
            {monitoringData?.submissions?.recent_submissions?.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="table table-striped">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Type</th>
                      <th>Status</th>
                      <th>Created</th>
                      <th>Ollama Results</th>
                    </tr>
                  </thead>
                  <tbody>
                    {monitoringData.submissions.recent_submissions.map((submission) => (
                      <tr key={submission.id}>
                        <td className="font-mono text-sm">{submission.id.slice(0, 8)}...</td>
                        <td>
                          <span className="badge badge-primary">{submission.type}</span>
                        </td>
                        <td>
                          <span className={`badge ${
                            submission.status === 'pending_review' ? 'badge-warning' :
                            submission.status === 'approved' ? 'badge-success' :
                            'badge-danger'
                          }`}>
                            {submission.status}
                          </span>
                        </td>
                        <td className="text-sm text-gray-600">
                          {new Date(submission.created_at).toLocaleString()}
                        </td>
                        <td>
                          {submission.has_ollama_results ? (
                            <span className="text-green-600">✅ Yes</span>
                          ) : (
                            <span className="text-gray-400">❌ No</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-gray-600 text-center py-8">No recent submissions found</p>
            )}
          </div>
        </div>

        {/* Processing Pipeline Flow */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold">Processing Pipeline Flow</h3>
          </div>
          <div className="card-body">
            <div className="flex items-center justify-between">
              <div className="text-center">
                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-2">
                  <i className="fas fa-upload text-blue-600 text-xl"></i>
                </div>
                <p className="text-sm font-medium">Document Upload</p>
                <p className="text-xs text-gray-600">{monitoringData?.file_processing?.docs?.count || 0} files</p>
              </div>
              
              <div className="flex-1 h-1 bg-gray-200 mx-4"></div>
              
              <div className="text-center">
                <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-2">
                  <i className="fas fa-cog text-yellow-600 text-xl"></i>
                </div>
                <p className="text-sm font-medium">Processing</p>
                <p className="text-xs text-gray-600">{monitoringData?.file_processing?.processing?.count || 0} files</p>
              </div>
              
              <div className="flex-1 h-1 bg-gray-200 mx-4"></div>
              
              <div className="text-center">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-2">
                  <i className="fas fa-check text-green-600 text-xl"></i>
                </div>
                <p className="text-sm font-medium">Completed</p>
                <p className="text-xs text-gray-600">{monitoringData?.file_processing?.completed?.count || 0} files</p>
              </div>
            </div>
          </div>
        </div>

        {/* Last Updated */}
        <div className="mt-6 text-center text-sm text-gray-500">
          Last updated: {monitoringData?.timestamp ? new Date(monitoringData.timestamp).toLocaleString() : 'Never'}
        </div>
      </div>
    </div>
  );
}
