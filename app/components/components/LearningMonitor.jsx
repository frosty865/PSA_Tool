'use client';

import { useState, useEffect } from 'react';
import { fetchWithAuth } from '../lib/fetchWithAuth';

export default function LearningMonitor() {
  const [learningStatus, setLearningStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    loadLearningStatus();
  }, []);

  useEffect(() => {
    if (mounted && autoRefresh) {
      const interval = setInterval(loadLearningStatus, 30000); // Refresh every 30 seconds
      return () => clearInterval(interval);
    }
  }, [mounted, autoRefresh]);

  const loadLearningStatus = async () => {
    try {
      setLoading(true);
      const response = await fetchWithAuth('/api/learning/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: 'status' })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setLearningStatus(data.status);
        setError('');
      } else {
        setError(data.error || 'Failed to load learning status');
      }
    } catch (err) {
      setError('Error loading learning status: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const startLearning = async () => {
    try {
      setLoading(true);
      const response = await fetchWithAuth('/api/learning/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: 'start' })
      });
      
      const data = await response.json();
      
      if (data.success) {
        const message = data.statistics 
          ? `Continuous Learning System is active!\n\nMode: ${data.mode || 'API/Database'}\nTotal events: ${data.statistics.total_learning_events || 0}\nApproved events: ${data.statistics.approved_events || 0}\n\n${data.note || ''}`
          : 'Continuous Learning System is active!';
        alert(message);
        loadLearningStatus();
      } else {
        alert(`Failed to start learning system: ${data.error || 'Unknown error'}\n\n${data.message || ''}`);
      }
    } catch (err) {
      alert('Error starting learning system: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const runLearningCycle = async () => {
    try {
      setLoading(true);
      const response = await fetchWithAuth('/api/learning/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: 'cycle' })
      });
      
      const data = await response.json();
      
      if (data.success) {
        const message = `Learning cycle completed!\n\nEvents processed: ${data.events_processed || 0}\nTotal events: ${data.statistics?.total_events || 0}\nApproved events: ${data.statistics?.approved_events || 0}`;
        alert(message);
        loadLearningStatus();
      } else {
        const errorMsg = data.details 
          ? `Learning cycle failed: ${data.error}\n\nDetails: ${data.details}\n\n${data.note || ''}`
          : `Learning cycle failed: ${data.error || 'Unknown error'}`;
        alert(errorMsg);
      }
    } catch (err) {
      alert('Error running learning cycle: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!mounted) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Loading learning status...</p>
      </div>
    );
  }

  if (loading && !learningStatus) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Loading learning status...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <div className="text-red-600 text-xl mb-4">⚠️ Error</div>
        <p className="text-gray-600">{error}</p>
        <button 
          onClick={loadLearningStatus}
          className="btn btn-primary mt-4"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-8">
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-3xl font-bold text-gray-900">Continuous Learning Monitor</h1>
          <div className="flex items-center space-x-4">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="form-checkbox h-4 w-4 text-blue-600"
              />
              <span className="ml-2 text-sm text-gray-700">Auto-refresh</span>
            </label>
            <button
              onClick={loadLearningStatus}
              disabled={loading}
              className="btn btn-secondary btn-sm"
            >
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
        </div>
        <p className="text-gray-600">
          Monitor and control the continuous learning system that improves PSA Tool processing over time.
        </p>
      </div>

      {/* Learning System Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <div className={`p-3 rounded-full ${learningStatus?.daemon_status === 'running' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'}`}>
                <i className="fas fa-brain text-xl"></i>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Learning Status</p>
                <p className={`text-2xl font-bold ${(learningStatus?.daemon_status === 'running' || learningStatus?.daemon_status === 'active') ? 'text-green-900' : 'text-red-900'}`}>
                  {learningStatus?.daemon_status === 'active' ? 'Active' : learningStatus?.daemon_status || 'Unknown'}
                </p>
                {learningStatus?.mode && (
                  <p className="text-xs text-gray-500 mt-1">Mode: {learningStatus.mode}</p>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-blue-100 text-blue-600">
                <i className="fas fa-clock text-xl"></i>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Last Learning Run</p>
                <p className="text-2xl font-bold text-gray-900">
                  {learningStatus?.last_learning_run ? 
                    new Date(learningStatus.last_learning_run).toLocaleDateString() : 
                    'Never'
                  }
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-purple-100 text-purple-600">
                <i className="fas fa-chart-line text-xl"></i>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Events Processed</p>
                <p className="text-2xl font-bold text-gray-900">
                  {learningStatus?.learning_stats?.total_events_processed || 0}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-yellow-100 text-yellow-600">
                <i className="fas fa-cogs text-xl"></i>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Rules Generated</p>
                <p className="text-2xl font-bold text-gray-900">
                  {learningStatus?.learning_stats?.rules_generated || 0}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Learning Controls */}
      <div className="card mb-8">
        <div className="card-header">
          <h2 className="card-title">Learning Controls</h2>
        </div>
        <div className="card-body">
          <div className="flex space-x-4">
            <button
              onClick={startLearning}
              disabled={loading}
              className="btn btn-success"
            >
              {loading ? 'Starting...' : 'Start Learning System'}
            </button>
            <button
              onClick={runLearningCycle}
              disabled={loading}
              className="btn btn-primary"
            >
              {loading ? 'Running...' : 'Run Learning Cycle'}
            </button>
          </div>
          <p className="text-sm text-gray-600 mt-2">
            Start the continuous learning daemon or run a single learning cycle to process recent events.
          </p>
        </div>
      </div>

      {/* Learning Statistics */}
      {learningStatus?.learning_stats && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Learning Statistics</h2>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="text-center">
                <p className="text-3xl font-bold text-blue-600">
                  {learningStatus.learning_stats.successful_retrains || 0}
                </p>
                <p className="text-sm text-gray-600">Successful Retrains</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-red-600">
                  {learningStatus.learning_stats.failed_retrains || 0}
                </p>
                <p className="text-sm text-gray-600">Failed Retrains</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-green-600">
                  {learningStatus.learning_stats.embeddings_updated || 0}
                </p>
                <p className="text-sm text-gray-600">Embeddings Updated</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-purple-600">
                  {learningStatus.learning_stats.rules_generated || 0}
                </p>
                <p className="text-sm text-gray-600">Rules Generated</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
