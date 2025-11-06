'use client'

import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Loader2, RefreshCw } from 'lucide-react'
import RoleGate from '@/components/RoleGate'
import '@/styles/cisa.css'

export default function ModelAnalytics() {
  const [stats, setStats] = useState([])
  const [health, setHealth] = useState(null)
  const [events, setEvents] = useState([])
  const [modelInfo, setModelInfo] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastRefresh, setLastRefresh] = useState(new Date())

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Fetch all data in parallel
      const [learnRes, healthRes, eventsRes, modelRes] = await Promise.all([
        fetch('/api/learning/stats?limit=50', { cache: 'no-store' }).catch(() => ({ ok: false })),
        fetch('/api/system/health', { cache: 'no-store' }).catch(() => ({ ok: false })),
        fetch('/api/system/events', { cache: 'no-store' }).catch(() => ({ ok: false })),
        fetch('/api/models/info', { cache: 'no-store' }).catch(() => ({ ok: false }))
      ])

      // Process learning stats
      if (learnRes.ok) {
        const learnData = await learnRes.json()
        const statsArray = Array.isArray(learnData) ? learnData : (learnData.stats || [])
        setStats(statsArray)
      } else {
        setStats([])
      }

      // Process health
      if (healthRes.ok) {
        const healthData = await healthRes.json()
        setHealth(healthData)
      } else {
        setHealth(null)
      }

      // Process events
      if (eventsRes.ok) {
        const eventsData = await eventsRes.json()
        setEvents(Array.isArray(eventsData) ? eventsData : [])
      } else {
        setEvents([])
      }

      // Process model info
      if (modelRes.ok) {
        const modelData = await modelRes.json()
        setModelInfo(modelData)
      } else {
        setModelInfo(null)
      }

      setLastRefresh(new Date())
    } catch (err) {
      console.error('Error fetching model analytics:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    // Auto-refresh every 60 seconds
    const interval = setInterval(fetchData, 60000)
    return () => clearInterval(interval)
  }, [])

  // Format timestamp for display
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return ''
    try {
      const date = new Date(timestamp)
      return date.toLocaleString('en-US', { 
        month: 'short', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    } catch {
      return timestamp
    }
  }

  // Prepare chart data
  const chartData = [...stats].reverse().map(s => ({
    timestamp: formatTimestamp(s.timestamp),
    fullTimestamp: s.timestamp,
    accept_rate: s.accept_rate ? (s.accept_rate * 100).toFixed(1) : 0,
    edited: s.edited || 0,
    rejected: s.rejected || 0,
    accepted: s.accepted || 0,
    total_events: s.total_events || 0
  }))

  return (
    <RoleGate requiredRole="admin">
      <div className="page-container">
        <div className="content-wrapper">
          {/* Header */}
          <div className="mb-6 flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Model Analytics & Performance</h1>
              <p className="text-gray-600 mt-2">
                Live model performance, retraining events, and system health metrics
              </p>
            </div>
            <button
              onClick={fetchData}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>

          {error && (
            <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              <p className="font-medium">Error loading analytics:</p>
              <p className="text-sm">{error}</p>
            </div>
          )}

          {loading && !stats.length && !modelInfo ? (
            <div className="flex justify-center items-center h-96">
              <div className="text-center">
                <Loader2 className="animate-spin w-8 h-8 mx-auto mb-4 text-blue-600" />
                <p className="text-gray-600">Loading model analytics...</p>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Current Model Summary */}
              <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">Current Model Status</h2>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-center">
                  <div>
                    <p className="text-sm font-medium text-gray-600 mb-2">Model</p>
                    <div className="inline-block px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-semibold">
                      {modelInfo?.name || 'Unknown'}
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-600 mb-2">Version</p>
                    <div className="inline-block px-3 py-1 bg-gray-100 text-gray-800 rounded-full text-sm font-semibold">
                      {modelInfo?.version || 'N/A'}
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-600 mb-2">Size</p>
                    <div className="inline-block px-3 py-1 bg-gray-100 text-gray-800 rounded-full text-sm font-semibold">
                      {modelInfo?.size_gb ? `${modelInfo.size_gb} GB` : '—'}
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-600 mb-2">Status</p>
                    <div className={`inline-block px-3 py-1 rounded-full text-sm font-semibold ${
                      health?.ollama === 'ok' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {health?.ollama === 'ok' ? 'Online' : 'Offline'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Learning Performance Trends */}
              {chartData.length > 0 && (
                <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
                  <h2 className="text-xl font-semibold text-gray-900 mb-4">Learning Performance Trends</h2>
                  <div style={{ height: '320px' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis 
                          dataKey="timestamp" 
                          angle={-45}
                          textAnchor="end"
                          height={80}
                          interval="preserveStartEnd"
                        />
                        <YAxis />
                        <Tooltip 
                          formatter={(value, name) => {
                            if (name === 'accept_rate') return [`${value}%`, 'Accept Rate']
                            return [value, name]
                          }}
                        />
                        <Legend />
                        <Line 
                          type="monotone" 
                          dataKey="accept_rate" 
                          stroke="#4CAF50" 
                          name="Accept Rate (%)"
                          strokeWidth={2}
                          dot={{ r: 4 }}
                        />
                        <Line 
                          type="monotone" 
                          dataKey="edited" 
                          stroke="#FFC107" 
                          name="Edited"
                          strokeWidth={2}
                          dot={{ r: 4 }}
                        />
                        <Line 
                          type="monotone" 
                          dataKey="rejected" 
                          stroke="#E53935" 
                          name="Rejected"
                          strokeWidth={2}
                          dot={{ r: 4 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Retraining & System Events Timeline */}
              <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">Retraining & System Events</h2>
                {events.length > 0 ? (
                  <div className="space-y-3">
                    {events.map((event, idx) => (
                      <div 
                        key={idx} 
                        className="border-l-4 border-blue-500 pl-4 py-2 hover:bg-gray-50 transition-colors"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <p className="font-semibold text-gray-900">
                              {event.event_type || 'System Event'}
                            </p>
                            <p className="text-sm text-gray-600 mt-1">
                              {event.notes || event.message || 'No details available'}
                            </p>
                          </div>
                          <div className="text-sm text-gray-500 ml-4">
                            {formatTimestamp(event.timestamp)}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-8">
                    No system events recorded yet. Events will appear here when model retraining or other system actions occur.
                  </p>
                )}
              </div>

              {/* System Health Summary */}
              {health && (
                <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
                  <h2 className="text-xl font-semibold text-gray-900 mb-4">System Health</h2>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <p className="text-sm font-medium text-gray-600 mb-1">Flask</p>
                      <div className={`inline-block px-3 py-1 rounded-full text-sm font-semibold ${
                        health.flask === 'ok' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {health.flask === 'ok' ? 'Online' : 'Offline'}
                      </div>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-600 mb-1">Ollama</p>
                      <div className={`inline-block px-3 py-1 rounded-full text-sm font-semibold ${
                        health.ollama === 'ok' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {health.ollama === 'ok' ? 'Online' : 'Offline'}
                      </div>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-600 mb-1">Supabase</p>
                      <div className={`inline-block px-3 py-1 rounded-full text-sm font-semibold ${
                        health.supabase === 'ok' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {health.supabase === 'ok' ? 'Online' : 'Offline'}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Footer Info */}
              <div className="text-sm text-gray-500 text-center">
                <p>Last refreshed: {lastRefresh.toLocaleString()}</p>
                <p className="mt-1">Auto-refreshes every 60 seconds</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </RoleGate>
  )
}
