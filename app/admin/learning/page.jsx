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
  const [lastRefresh, setLastRefresh] = useState(null)

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
    // Initialize lastRefresh on client side only
    if (!lastRefresh) {
      setLastRefresh(new Date())
    }
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
      <div style={{ padding: 'var(--spacing-lg)', maxWidth: '1600px', margin: '0 auto' }}>
        {/* Header */}
        <div style={{ 
          marginBottom: 'var(--spacing-xl)', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 'var(--spacing-md)'
        }}>
          <div>
            <h1 style={{ 
              fontSize: 'var(--font-size-xxl)', 
              fontWeight: 700, 
              color: 'var(--cisa-blue)', 
              margin: 0,
              marginBottom: 'var(--spacing-xs)'
            }}>
              Learning Metrics Dashboard
            </h1>
            <p style={{ 
              fontSize: 'var(--font-size-md)', 
              color: 'var(--cisa-gray)',
              margin: 0
            }}>
              Real-time insights about model performance, analyst feedback, and system learning trends
            </p>
          </div>
          <button
            onClick={fetchLearningStats}
            disabled={loading}
            className="btn btn-primary"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--spacing-sm)',
              opacity: loading ? 0.6 : 1,
              cursor: loading ? 'not-allowed' : 'pointer'
            }}
          >
            <RefreshCw style={{ 
              width: '16px', 
              height: '16px',
              animation: loading ? 'spin 1s linear infinite' : 'none'
            }} />
            Refresh
          </button>
        </div>

        {error && (
          <div className="alert alert-warning" style={{ 
            marginBottom: 'var(--spacing-lg)',
            padding: 'var(--spacing-md)',
            backgroundColor: '#fff3cd',
            border: '1px solid var(--cisa-warning)',
            borderRadius: 'var(--border-radius)'
          }}>
            <p style={{ fontWeight: 600, margin: 0, marginBottom: 'var(--spacing-xs)' }}>Error loading metrics:</p>
            <p style={{ fontSize: 'var(--font-size-sm)', margin: 0 }}>{error}</p>
          </div>
        )}

        {loading && stats.length === 0 ? (
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            minHeight: '400px'
          }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{
                width: '32px',
                height: '32px',
                border: '3px solid var(--cisa-gray-light)',
                borderTop: '3px solid var(--cisa-blue)',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
                margin: '0 auto',
                marginBottom: 'var(--spacing-md)'
              }}></div>
              <p style={{ color: 'var(--cisa-gray)', fontSize: 'var(--font-size-md)' }}>Loading learning metrics...</p>
            </div>
          </div>
        ) : (
            <>
              {/* Summary Cards */}
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', 
                gap: 'var(--spacing-lg)', 
                marginBottom: 'var(--spacing-xl)'
              }}>
                <div className="card" style={{
                  background: 'linear-gradient(135deg, var(--cisa-blue-lightest) 0%, rgba(0, 113, 188, 0.05) 100%)',
                  border: '1px solid var(--cisa-blue-lighter)'
                }}>
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'space-between', 
                    marginBottom: 'var(--spacing-sm)'
                  }}>
                    <h3 style={{ 
                      fontSize: 'var(--font-size-sm)', 
                      fontWeight: 500, 
                      color: 'var(--cisa-gray)',
                      margin: 0
                    }}>
                      Total Feedback Events
                    </h3>
                    <Activity style={{ width: '20px', height: '20px', color: 'var(--cisa-blue)' }} />
                  </div>
                  <p style={{ 
                    fontSize: 'var(--font-size-xxl)', 
                    fontWeight: 700, 
                    color: 'var(--cisa-blue)',
                    margin: 0,
                    marginBottom: 'var(--spacing-xs)'
                  }}>
                    {totalEvents}
                  </p>
                  <p style={{ 
                    fontSize: 'var(--font-size-xs)', 
                    color: 'var(--cisa-gray)',
                    margin: 0
                  }}>
                    All time
                  </p>
                </div>

                <div className="card" style={{
                  background: 'linear-gradient(135deg, rgba(40, 167, 69, 0.1) 0%, rgba(40, 167, 69, 0.05) 100%)',
                  border: '1px solid rgba(40, 167, 69, 0.3)'
                }}>
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'space-between', 
                    marginBottom: 'var(--spacing-sm)'
                  }}>
                    <h3 style={{ 
                      fontSize: 'var(--font-size-sm)', 
                      fontWeight: 500, 
                      color: 'var(--cisa-gray)',
                      margin: 0
                    }}>
                      Average Accept Rate
                    </h3>
                    <TrendingUp style={{ width: '20px', height: '20px', color: 'var(--cisa-success)' }} />
                  </div>
                  <p style={{ 
                    fontSize: 'var(--font-size-xxl)', 
                    fontWeight: 700, 
                    color: 'var(--cisa-success)',
                    margin: 0,
                    marginBottom: 'var(--spacing-xs)'
                  }}>
                    {avgAcceptRate}%
                  </p>
                  <p style={{ 
                    fontSize: 'var(--font-size-xs)', 
                    color: 'var(--cisa-gray)',
                    margin: 0
                  }}>
                    Rolling window
                  </p>
                </div>

                <div className="card" style={{
                  background: 'linear-gradient(135deg, rgba(40, 167, 69, 0.1) 0%, rgba(40, 167, 69, 0.05) 100%)',
                  border: '1px solid rgba(40, 167, 69, 0.3)'
                }}>
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'space-between', 
                    marginBottom: 'var(--spacing-sm)'
                  }}>
                    <h3 style={{ 
                      fontSize: 'var(--font-size-sm)', 
                      fontWeight: 500, 
                      color: 'var(--cisa-gray)',
                      margin: 0
                    }}>
                      Accepted
                    </h3>
                    <Target style={{ width: '20px', height: '20px', color: 'var(--cisa-success)' }} />
                  </div>
                  <p style={{ 
                    fontSize: 'var(--font-size-xxl)', 
                    fontWeight: 700, 
                    color: 'var(--cisa-success)',
                    margin: 0,
                    marginBottom: 'var(--spacing-xs)'
                  }}>
                    {totalAccepted}
                  </p>
                  <p style={{ 
                    fontSize: 'var(--font-size-xs)', 
                    color: 'var(--cisa-gray)',
                    margin: 0
                  }}>
                    Total approved
                  </p>
                </div>

                <div className="card" style={{
                  background: 'linear-gradient(135deg, rgba(216, 57, 51, 0.1) 0%, rgba(216, 57, 51, 0.05) 100%)',
                  border: '1px solid rgba(216, 57, 51, 0.3)'
                }}>
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'space-between', 
                    marginBottom: 'var(--spacing-sm)'
                  }}>
                    <h3 style={{ 
                      fontSize: 'var(--font-size-sm)', 
                      fontWeight: 500, 
                      color: 'var(--cisa-gray)',
                      margin: 0
                    }}>
                      Rejected
                    </h3>
                    <Target style={{ width: '20px', height: '20px', color: 'var(--cisa-red)' }} />
                  </div>
                  <p style={{ 
                    fontSize: 'var(--font-size-xxl)', 
                    fontWeight: 700, 
                    color: 'var(--cisa-red)',
                    margin: 0,
                    marginBottom: 'var(--spacing-xs)'
                  }}>
                    {totalRejected}
                  </p>
                  <p style={{ 
                    fontSize: 'var(--font-size-xs)', 
                    color: 'var(--cisa-gray)',
                    margin: 0
                  }}>
                    Total rejected
                  </p>
                </div>
              </div>

              {/* Heuristics Card */}
              {heuristics && (
                <div className="card" style={{ marginBottom: 'var(--spacing-xl)' }}>
                  <h3 style={{ 
                    fontSize: 'var(--font-size-lg)', 
                    fontWeight: 600, 
                    color: 'var(--cisa-black)', 
                    marginBottom: 'var(--spacing-lg)',
                    margin: 0,
                    marginBottom: 'var(--spacing-md)'
                  }}>
                    Current Heuristic Thresholds
                  </h3>
                  <div style={{ 
                    display: 'grid', 
                    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
                    gap: 'var(--spacing-lg)'
                  }}>
                    <div>
                      <p style={{ 
                        fontSize: 'var(--font-size-sm)', 
                        color: 'var(--cisa-gray)', 
                        marginBottom: 'var(--spacing-xs)',
                        margin: 0
                      }}>
                        Confidence Threshold
                      </p>
                      <p style={{ 
                        fontSize: 'var(--font-size-xl)', 
                        fontWeight: 700, 
                        color: 'var(--cisa-blue)',
                        margin: 0
                      }}>
                        {heuristics.confidence_threshold ? (heuristics.confidence_threshold * 100).toFixed(1) : 'N/A'}%
                      </p>
                    </div>
                    <div>
                      <p style={{ 
                        fontSize: 'var(--font-size-sm)', 
                        color: 'var(--cisa-gray)', 
                        marginBottom: 'var(--spacing-xs)',
                        margin: 0
                      }}>
                        High Confidence Threshold
                      </p>
                      <p style={{ 
                        fontSize: 'var(--font-size-xl)', 
                        fontWeight: 700, 
                        color: '#6f42c1',
                        margin: 0
                      }}>
                        {heuristics.high_confidence_threshold ? (heuristics.high_confidence_threshold * 100).toFixed(1) : 'N/A'}%
                      </p>
                    </div>
                    <div>
                      <p style={{ 
                        fontSize: 'var(--font-size-sm)', 
                        color: 'var(--cisa-gray)', 
                        marginBottom: 'var(--spacing-xs)',
                        margin: 0
                      }}>
                        Last Updated
                      </p>
                      <p style={{ 
                        fontSize: 'var(--font-size-sm)', 
                        color: 'var(--cisa-black)',
                        margin: 0
                      }}>
                        {heuristics.last_updated ? formatTimestamp(heuristics.last_updated) : 'Never'}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Charts */}
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', 
                gap: 'var(--spacing-xl)', 
                marginBottom: 'var(--spacing-xl)'
              }}>
                {/* Accept/Reject/Edit Trend */}
                <div className="card">
                  <h3 style={{ 
                    fontSize: 'var(--font-size-lg)', 
                    fontWeight: 600, 
                    color: 'var(--cisa-black)', 
                    marginBottom: 'var(--spacing-lg)',
                    margin: 0,
                    marginBottom: 'var(--spacing-md)'
                  }}>
                    Accept / Reject / Edit Trend
                  </h3>
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
                    <div style={{ 
                      minHeight: '300px', 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center',
                      color: 'var(--cisa-gray)'
                    }}>
                      <p style={{ margin: 0 }}>No data available yet. Learning statistics will appear here once feedback events are processed.</p>
                    </div>
                  )}
                </div>

                {/* Event Counts Over Time */}
                <div className="card">
                  <h3 style={{ 
                    fontSize: 'var(--font-size-lg)', 
                    fontWeight: 600, 
                    color: 'var(--cisa-black)', 
                    marginBottom: 'var(--spacing-lg)',
                    margin: 0,
                    marginBottom: 'var(--spacing-md)'
                  }}>
                    Event Counts Over Time
                  </h3>
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
                    <div style={{ 
                      minHeight: '300px', 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center',
                      color: 'var(--cisa-gray)'
                    }}>
                      <p style={{ margin: 0 }}>No data available yet.</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Confidence Score Trend (if available) */}
              {chartData.some(d => d.average_confidence_score !== null) && (
                <div className="card" style={{ marginBottom: 'var(--spacing-xl)' }}>
                  <h3 style={{ 
                    fontSize: 'var(--font-size-lg)', 
                    fontWeight: 600, 
                    color: 'var(--cisa-black)', 
                    marginBottom: 'var(--spacing-lg)',
                    margin: 0,
                    marginBottom: 'var(--spacing-md)'
                  }}>
                    Average Confidence Score Trend
                  </h3>
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
                <div className="card" style={{ marginBottom: 'var(--spacing-xl)' }}>
                  <h3 style={{ 
                    fontSize: 'var(--font-size-lg)', 
                    fontWeight: 600, 
                    color: 'var(--cisa-black)', 
                    marginBottom: 'var(--spacing-lg)',
                    margin: 0,
                    marginBottom: 'var(--spacing-md)'
                  }}>
                    Recent Learning Activity
                  </h3>
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ 
                      width: '100%', 
                      borderCollapse: 'collapse'
                    }}>
                      <thead style={{ backgroundColor: 'var(--cisa-gray-lighter)' }}>
                        <tr>
                          <th style={{ 
                            padding: 'var(--spacing-sm) var(--spacing-md)', 
                            textAlign: 'left', 
                            fontSize: 'var(--font-size-xs)', 
                            fontWeight: 600, 
                            color: 'var(--cisa-gray)',
                            textTransform: 'uppercase',
                            borderBottom: '2px solid var(--cisa-gray-light)'
                          }}>
                            Timestamp
                          </th>
                          <th style={{ 
                            padding: 'var(--spacing-sm) var(--spacing-md)', 
                            textAlign: 'left', 
                            fontSize: 'var(--font-size-xs)', 
                            fontWeight: 600, 
                            color: 'var(--cisa-gray)',
                            textTransform: 'uppercase',
                            borderBottom: '2px solid var(--cisa-gray-light)'
                          }}>
                            Window
                          </th>
                          <th style={{ 
                            padding: 'var(--spacing-sm) var(--spacing-md)', 
                            textAlign: 'left', 
                            fontSize: 'var(--font-size-xs)', 
                            fontWeight: 600, 
                            color: 'var(--cisa-gray)',
                            textTransform: 'uppercase',
                            borderBottom: '2px solid var(--cisa-gray-light)'
                          }}>
                            Total Events
                          </th>
                          <th style={{ 
                            padding: 'var(--spacing-sm) var(--spacing-md)', 
                            textAlign: 'left', 
                            fontSize: 'var(--font-size-xs)', 
                            fontWeight: 600, 
                            color: 'var(--cisa-gray)',
                            textTransform: 'uppercase',
                            borderBottom: '2px solid var(--cisa-gray-light)'
                          }}>
                            Accepted
                          </th>
                          <th style={{ 
                            padding: 'var(--spacing-sm) var(--spacing-md)', 
                            textAlign: 'left', 
                            fontSize: 'var(--font-size-xs)', 
                            fontWeight: 600, 
                            color: 'var(--cisa-gray)',
                            textTransform: 'uppercase',
                            borderBottom: '2px solid var(--cisa-gray-light)'
                          }}>
                            Rejected
                          </th>
                          <th style={{ 
                            padding: 'var(--spacing-sm) var(--spacing-md)', 
                            textAlign: 'left', 
                            fontSize: 'var(--font-size-xs)', 
                            fontWeight: 600, 
                            color: 'var(--cisa-gray)',
                            textTransform: 'uppercase',
                            borderBottom: '2px solid var(--cisa-gray-light)'
                          }}>
                            Edited
                          </th>
                          <th style={{ 
                            padding: 'var(--spacing-sm) var(--spacing-md)', 
                            textAlign: 'left', 
                            fontSize: 'var(--font-size-xs)', 
                            fontWeight: 600, 
                            color: 'var(--cisa-gray)',
                            textTransform: 'uppercase',
                            borderBottom: '2px solid var(--cisa-gray-light)'
                          }}>
                            Accept Rate
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {stats.slice(0, 10).map((stat, idx) => (
                          <tr key={idx} style={{ 
                            borderBottom: '1px solid var(--cisa-gray-light)',
                            transition: 'background-color 0.2s'
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--cisa-gray-lighter)'}
                          onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                          >
                            <td style={{ 
                              padding: 'var(--spacing-sm) var(--spacing-md)', 
                              whiteSpace: 'nowrap', 
                              fontSize: 'var(--font-size-sm)', 
                              color: 'var(--cisa-black)'
                            }}>
                              {formatTimestamp(stat.timestamp)}
                            </td>
                            <td style={{ 
                              padding: 'var(--spacing-sm) var(--spacing-md)', 
                              whiteSpace: 'nowrap', 
                              fontSize: 'var(--font-size-sm)', 
                              color: 'var(--cisa-gray)'
                            }}>
                              {stat.window_minutes || 60} min
                            </td>
                            <td style={{ 
                              padding: 'var(--spacing-sm) var(--spacing-md)', 
                              whiteSpace: 'nowrap', 
                              fontSize: 'var(--font-size-sm)', 
                              color: 'var(--cisa-black)'
                            }}>
                              {stat.total_events || 0}
                            </td>
                            <td style={{ 
                              padding: 'var(--spacing-sm) var(--spacing-md)', 
                              whiteSpace: 'nowrap', 
                              fontSize: 'var(--font-size-sm)', 
                              color: 'var(--cisa-success)', 
                              fontWeight: 600
                            }}>
                              {stat.accepted || 0}
                            </td>
                            <td style={{ 
                              padding: 'var(--spacing-sm) var(--spacing-md)', 
                              whiteSpace: 'nowrap', 
                              fontSize: 'var(--font-size-sm)', 
                              color: 'var(--cisa-red)', 
                              fontWeight: 600
                            }}>
                              {stat.rejected || 0}
                            </td>
                            <td style={{ 
                              padding: 'var(--spacing-sm) var(--spacing-md)', 
                              whiteSpace: 'nowrap', 
                              fontSize: 'var(--font-size-sm)', 
                              color: 'var(--cisa-warning)', 
                              fontWeight: 600
                            }}>
                              {stat.edited || 0}
                            </td>
                            <td style={{ 
                              padding: 'var(--spacing-sm) var(--spacing-md)', 
                              whiteSpace: 'nowrap', 
                              fontSize: 'var(--font-size-sm)', 
                              color: 'var(--cisa-black)', 
                              fontWeight: 600
                            }}>
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
              <div style={{ 
                marginTop: 'var(--spacing-xl)', 
                fontSize: 'var(--font-size-sm)', 
                color: 'var(--cisa-gray)', 
                textAlign: 'center'
              }}>
                <p style={{ margin: 0 }}>Last refreshed: {lastRefresh ? lastRefresh.toLocaleString() : 'Never'}</p>
                <p style={{ margin: 'var(--spacing-xs) 0 0 0' }}>Auto-refreshes every 60 seconds</p>
              </div>
            </>
          )}
      </div>
    </RoleGate>
  )
}

