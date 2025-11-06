'use client'

import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Loader2, TrendingUp, Activity, Target, RefreshCw } from 'lucide-react'
import RoleGate from '@/components/RoleGate'
import '@/styles/cisa.css'

export default function LearningDashboard() {
  const [stats, setStats] = useState([])
  const [heuristics, setHeuristics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastRefresh, setLastRefresh] = useState(new Date())

  const fetchLearningStats = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Fetch learning statistics
      const statsRes = await fetch('/api/learning/stats?limit=50', { cache: 'no-store' })
      if (statsRes.ok) {
        const statsData = await statsRes.json()
        // Handle both array and object responses
        const statsArray = Array.isArray(statsData) ? statsData : (statsData.stats || [])
        setStats(statsArray)
      } else {
        console.warn('Failed to fetch learning stats:', statsRes.status)
        setStats([])
      }
      
      // Fetch heuristics (confidence thresholds)
      try {
        const heuristicsRes = await fetch('/api/learning/heuristics', { cache: 'no-store' })
        if (heuristicsRes.ok) {
          const heuristicsData = await heuristicsRes.json()
          setHeuristics(heuristicsData.heuristics || null)
        }
      } catch (heuristicsErr) {
        console.warn('Failed to fetch heuristics:', heuristicsErr)
        // Non-critical, continue without heuristics
      }
      
      setLastRefresh(new Date())
    } catch (err) {
      console.error('Error fetching learning metrics:', err)
      setError(err.message)
      setStats([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLearningStats()
    // Auto-refresh every 60 seconds
    const interval = setInterval(fetchLearningStats, 60000)
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

  // Calculate summary metrics
  const totalEvents = stats.reduce((sum, s) => sum + (s.total_events || 0), 0)
  const totalAccepted = stats.reduce((sum, s) => sum + (s.accepted || 0), 0)
  const totalRejected = stats.reduce((sum, s) => sum + (s.rejected || 0), 0)
  const totalEdited = stats.reduce((sum, s) => sum + (s.edited || 0), 0)
  const avgAcceptRate = stats.length > 0 
    ? (stats.reduce((sum, s) => sum + (s.accept_rate || 0), 0) / stats.length * 100).toFixed(1)
    : 0

  // Prepare chart data (reverse to show chronological order)
  const chartData = [...stats].reverse().map(s => ({
    timestamp: formatTimestamp(s.timestamp),
    fullTimestamp: s.timestamp,
    accept_rate: s.accept_rate ? (s.accept_rate * 100).toFixed(1) : 0,
    accepted: s.accepted || 0,
    rejected: s.rejected || 0,
    edited: s.edited || 0,
    total_events: s.total_events || 0,
    average_confidence_score: s.average_confidence_score ? (s.average_confidence_score * 100).toFixed(1) : null
  }))

  return (
    <RoleGate requiredRole="admin">
      <div className="page-container">
        <div className="content-wrapper">
          {/* Header */}
          <div className="mb-6 flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Learning Metrics Dashboard</h1>
              <p className="text-gray-600 mt-2">
                Real-time insights about model performance, analyst feedback, and system learning trends
              </p>
            </div>
            <button
              onClick={fetchLearningStats}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>

          {error && (
            <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              <p className="font-medium">Error loading metrics:</p>
              <p className="text-sm">{error}</p>
            </div>
          )}

          {loading && stats.length === 0 ? (
            <div className="flex items-center justify-center h-96">
              <div className="text-center">
                <Loader2 className="animate-spin w-8 h-8 mx-auto mb-4 text-blue-600" />
                <p className="text-gray-600">Loading learning metrics...</p>
              </div>
            </div>
          ) : (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
                <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-medium text-gray-600">Total Feedback Events</h3>
                    <Activity className="w-5 h-5 text-blue-600" />
                  </div>
                  <p className="text-3xl font-bold text-gray-900">{totalEvents}</p>
                  <p className="text-xs text-gray-500 mt-1">All time</p>
                </div>

                <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-medium text-gray-600">Average Accept Rate</h3>
                    <TrendingUp className="w-5 h-5 text-green-600" />
                  </div>
                  <p className="text-3xl font-bold text-gray-900">{avgAcceptRate}%</p>
                  <p className="text-xs text-gray-500 mt-1">Rolling window</p>
                </div>

                <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-medium text-gray-600">Accepted</h3>
                    <Target className="w-5 h-5 text-green-600" />
                  </div>
                  <p className="text-3xl font-bold text-green-600">{totalAccepted}</p>
                  <p className="text-xs text-gray-500 mt-1">Total approved</p>
                </div>

                <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-medium text-gray-600">Rejected</h3>
                    <Target className="w-5 h-5 text-red-600" />
                  </div>
                  <p className="text-3xl font-bold text-red-600">{totalRejected}</p>
                  <p className="text-xs text-gray-500 mt-1">Total rejected</p>
                </div>
              </div>

              {/* Heuristics Card */}
              {heuristics && (
                <div className="mb-6 bg-white rounded-lg shadow-md p-6 border border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Current Heuristic Thresholds</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <p className="text-sm text-gray-600 mb-1">Confidence Threshold</p>
                      <p className="text-2xl font-bold text-blue-600">
                        {heuristics.confidence_threshold ? (heuristics.confidence_threshold * 100).toFixed(1) : 'N/A'}%
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 mb-1">High Confidence Threshold</p>
                      <p className="text-2xl font-bold text-purple-600">
                        {heuristics.high_confidence_threshold ? (heuristics.high_confidence_threshold * 100).toFixed(1) : 'N/A'}%
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 mb-1">Last Updated</p>
                      <p className="text-sm text-gray-900">
                        {heuristics.last_updated ? formatTimestamp(heuristics.last_updated) : 'Never'}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Charts */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                {/* Accept/Reject/Edit Trend */}
                <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Accept / Reject / Edit Trend</h3>
                  {chartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={300}>
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
                          dataKey="rejected" 
                          stroke="#E53935" 
                          name="Rejected"
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
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-300 flex items-center justify-center text-gray-500">
                      <p>No data available yet. Learning statistics will appear here once feedback events are processed.</p>
                    </div>
                  )}
                </div>

                {/* Event Counts Over Time */}
                <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Event Counts Over Time</h3>
                  {chartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={300}>
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
                        <Tooltip />
                        <Legend />
                        <Line 
                          type="monotone" 
                          dataKey="accepted" 
                          stroke="#4CAF50" 
                          name="Accepted"
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
                          dataKey="total_events" 
                          stroke="#2196F3" 
                          name="Total Events"
                          strokeWidth={2}
                          dot={{ r: 4 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-300 flex items-center justify-center text-gray-500">
                      <p>No data available yet.</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Confidence Score Trend (if available) */}
              {chartData.some(d => d.average_confidence_score !== null) && (
                <div className="mb-6 bg-white rounded-lg shadow-md p-6 border border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Average Confidence Score Trend</h3>
                  <ResponsiveContainer width="100%" height={300}>
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
                        formatter={(value) => [`${value}%`, 'Avg Confidence']}
                      />
                      <Legend />
                      <Line 
                        type="monotone" 
                        dataKey="average_confidence_score" 
                        stroke="#9C27B0" 
                        name="Avg Confidence (%)"
                        strokeWidth={2}
                        dot={{ r: 4 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Recent Activity Summary */}
              {stats.length > 0 && (
                <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Learning Activity</h3>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Timestamp</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Window</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total Events</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Accepted</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Rejected</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Edited</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Accept Rate</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {stats.slice(0, 10).map((stat, idx) => (
                          <tr key={idx} className="hover:bg-gray-50">
                            <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                              {formatTimestamp(stat.timestamp)}
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                              {stat.window_minutes || 60} min
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                              {stat.total_events || 0}
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap text-sm text-green-600 font-medium">
                              {stat.accepted || 0}
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap text-sm text-red-600 font-medium">
                              {stat.rejected || 0}
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap text-sm text-yellow-600 font-medium">
                              {stat.edited || 0}
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 font-medium">
                              {stat.accept_rate ? (stat.accept_rate * 100).toFixed(1) : '0.0'}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Footer Info */}
              <div className="mt-6 text-sm text-gray-500 text-center">
                <p>Last refreshed: {lastRefresh.toLocaleString()}</p>
                <p className="mt-1">Auto-refreshes every 60 seconds</p>
              </div>
            </>
          )}
        </div>
      </div>
    </RoleGate>
  )
}

