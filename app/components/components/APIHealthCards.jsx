'use client';
import { useState, useEffect } from 'react';

export default function APIHealthCards() {
  const [healthStatus, setHealthStatus] = useState({
    overall: 'checking',
    apis: {
      auth: 'checking',
      documents: 'checking', 
      admin: 'checking',
      learning: 'checking'
    },
    lastChecked: null
  });

  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    checkAPIHealth();
    // Check every 30 seconds
    const interval = setInterval(checkAPIHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkAPIHealth = async () => {
    try {
      const endpoints = [
        { key: 'auth', url: '/api/auth/verify', method: 'GET' },
        { key: 'documents', url: '/api/documents/status', method: 'GET' },
        { key: 'admin', url: '/api/admin/users', method: 'GET' },
        { key: 'learning', url: '/api/learning/start', method: 'POST' }
      ];

      const results = {};
      let healthyCount = 0;

      for (const endpoint of endpoints) {
        try {
          const response = await fetch(endpoint.url, {
            method: endpoint.method,
            headers: { 'Content-Type': 'application/json' }
          });
          
          if (response.ok) {
            results[endpoint.key] = 'healthy';
            healthyCount++;
          } else if (response.status === 401) {
            results[endpoint.key] = 'auth_required';
            healthyCount++; // 401 is expected for protected endpoints
          } else {
            results[endpoint.key] = 'error';
          }
        } catch (error) {
          results[endpoint.key] = 'error';
        }
      }

      const overall = healthyCount === endpoints.length ? 'healthy' : 
                     healthyCount > endpoints.length / 2 ? 'degraded' : 'unhealthy';

      setHealthStatus({
        overall,
        apis: results,
        lastChecked: new Date()
      });
    } catch (error) {
      console.error('Health check failed:', error);
      setHealthStatus(prev => ({
        ...prev,
        overall: 'error',
        lastChecked: new Date()
      }));
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy': return 'var(--cisa-green)';
      case 'auth_required': return 'var(--cisa-blue)';
      case 'degraded': return 'var(--cisa-yellow)';
      case 'error': return 'var(--cisa-red)';
      case 'checking': return 'var(--cisa-gray-medium)';
      default: return 'var(--cisa-gray-medium)';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy': return '✓';
      case 'auth_required': return '🔒';
      case 'degraded': return '⚠';
      case 'error': return '✗';
      case 'checking': return '⟳';
      default: return '?';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'healthy': return 'Healthy';
      case 'auth_required': return 'Auth Required';
      case 'degraded': return 'Degraded';
      case 'error': return 'Error';
      case 'checking': return 'Checking...';
      default: return 'Unknown';
    }
  };

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <div 
        className="bg-white rounded-lg shadow-lg border"
        style={{ 
          borderColor: getStatusColor(healthStatus.overall),
          borderWidth: '2px',
          minWidth: '200px'
        }}
      >
        {/* Header */}
        <div 
          className="px-3 py-2 cursor-pointer flex items-center justify-between"
          onClick={() => setIsExpanded(!isExpanded)}
          style={{ 
            backgroundColor: getStatusColor(healthStatus.overall),
            color: 'white',
            borderRadius: '6px 6px 0 0'
          }}
        >
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium">
              {getStatusIcon(healthStatus.overall)} API Health
            </span>
            <span className="text-xs opacity-90">
              {getStatusText(healthStatus.overall)}
            </span>
          </div>
          <button className="text-white hover:text-gray-200 transition-colors">
            {isExpanded ? '−' : '+'}
          </button>
        </div>

        {/* Expanded Details */}
        {isExpanded && (
          <div className="p-3 space-y-2">
            <div className="text-xs text-gray-600 mb-2">
              Last checked: {healthStatus.lastChecked ? 
                healthStatus.lastChecked.toLocaleTimeString() : 'Never'}
            </div>
            
            <div className="space-y-1">
              {Object.entries(healthStatus.apis).map(([key, status]) => (
                <div key={key} className="flex items-center justify-between text-xs">
                  <span className="capitalize">{key}</span>
                  <div className="flex items-center space-x-1">
                    <span style={{ color: getStatusColor(status) }}>
                      {getStatusIcon(status)}
                    </span>
                    <span style={{ color: getStatusColor(status) }}>
                      {getStatusText(status)}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            <div className="pt-2 border-t border-gray-200">
              <button
                onClick={checkAPIHealth}
                className="text-xs text-blue-600 hover:text-blue-800 transition-colors"
              >
                🔄 Refresh Status
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
