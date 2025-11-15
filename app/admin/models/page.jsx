'use client'

import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Loader2, RefreshCw } from 'lucide-react'
import RoleGate from '@/components/RoleGate'
import { useStatus } from '@/components/StatusProvider'
import '@/styles/cisa.css'

// Add spin animation for refresh button
const spinKeyframes = `
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
`
if (typeof document !== 'undefined') {
  const style = document.createElement('style')
  style.textContent = spinKeyframes
  document.head.appendChild(style)
}

export default function ModelAnalytics() {
  // Use preloaded status from context
  const {
    health,
    progress,
    monitoring,
    events,
    learningStats: stats,
    modelInfo,
    healthLoading,
    progressLoading,
    monitoringLoading,
    eventsLoading,
    learningStatsLoading,
    modelInfoLoading,
    lastRefresh,
    refreshAll
  } = useStatus()
  
  const [error, setError] = useState(null)
  
  // Determine if any data is still loading
  const loading = healthLoading || progressLoading || monitoringLoading || eventsLoading || learningStatsLoading || modelInfoLoading

  const fetchData = async () => {
    // Use the refresh function from context
    refreshAll()
  }

  // Data is preloaded by StatusProvider - no need to fetch on mount
  // StatusProvider automatically refreshes every 30 seconds

  // Format timestamp for display (EST/EDT)
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return ''
    try {
      const date = new Date(timestamp)
      return date.toLocaleString('en-US', { 
        month: 'short', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit',
        timeZone: 'America/New_York',
        timeZoneName: 'short'
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
      <div style={{ padding: 'var(--spacing-lg)', minHeight: '100vh' }}>
        <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
          {/* Header */}
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            marginBottom: 'var(--spacing-lg)' 
          }}>
            <div>
              <h1 style={{ 
                fontSize: 'var(--font-size-xxl)', 
                fontWeight: 700, 
                color: 'var(--cisa-black)', 
                marginBottom: 'var(--spacing-sm)' 
              }}>
                Model Analytics & Performance
              </h1>
              <p style={{ 
                color: 'var(--cisa-gray)', 
                fontSize: 'var(--font-size-base)' 
              }}>
                Live model performance, retraining events, and system health metrics
              </p>
            </div>
            <button
              onClick={async () => {
                // Manual refresh triggered
                await fetchData()
              }}
              disabled={loading}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--spacing-sm)',
                padding: 'var(--spacing-sm) var(--spacing-md)',
                backgroundColor: loading ? 'var(--cisa-gray)' : 'var(--cisa-blue)',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--border-radius)',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontWeight: 600,
                fontSize: 'var(--font-size-base)',
                transition: 'background-color 0.2s'
              }}
              onMouseEnter={(e) => {
                if (!loading) e.target.style.backgroundColor = 'var(--cisa-blue-dark)'
              }}
              onMouseLeave={(e) => {
                if (!loading) e.target.style.backgroundColor = 'var(--cisa-blue)'
              }}
            >
              <RefreshCw 
                style={{ 
                  width: '16px', 
                  height: '16px',
                  animation: loading ? 'spin 1s linear infinite' : 'none'
                }} 
              />
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>

          {error && (
            <div style={{
              marginBottom: 'var(--spacing-lg)',
              backgroundColor: '#FEF2F2',
              border: '1px solid #FECACA',
              color: '#991B1B',
              padding: 'var(--spacing-md)',
              borderRadius: 'var(--border-radius)'
            }}>
              <p style={{ fontWeight: 600, marginBottom: 'var(--spacing-xs)' }}>Error loading analytics:</p>
              <p style={{ fontSize: 'var(--font-size-sm)' }}>{error}</p>
            </div>
          )}

          {loading && !stats.length && !modelInfo ? (
            <div style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              height: '400px'
            }}>
              <div style={{ textAlign: 'center' }}>
                <Loader2 style={{
                  animation: 'spin 1s linear infinite',
                  width: '32px',
                  height: '32px',
                  margin: '0 auto var(--spacing-md)',
                  color: 'var(--cisa-blue)'
                }} />
                <p style={{ color: 'var(--cisa-gray)' }}>Loading model analytics...</p>
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)' }}>
              {/* Current Model Summary */}
              <div className="card" style={{ padding: 'var(--spacing-lg)' }}>
                <h2 style={{ 
                  fontSize: 'var(--font-size-xl)', 
                  fontWeight: 600, 
                  color: 'var(--cisa-blue)', 
                  marginBottom: 'var(--spacing-md)' 
                }}>
                  Current Model Status
                </h2>
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: 'var(--spacing-md)',
                  textAlign: 'center'
                }}>
                  <div>
                    <p style={{ 
                      fontSize: 'var(--font-size-sm)', 
                      fontWeight: 600, 
                      color: 'var(--cisa-gray)', 
                      marginBottom: 'var(--spacing-sm)' 
                    }}>
                      Model
                    </p>
                    <div style={{
                      display: 'inline-block',
                      padding: 'var(--spacing-xs) var(--spacing-md)',
                      backgroundColor: '#DBEAFE',
                      color: '#1E40AF',
                      borderRadius: '999px',
                      fontSize: 'var(--font-size-sm)',
                      fontWeight: 600
                    }}>
                      {modelInfo?.name || 'Unknown'}
                    </div>
                  </div>
                  <div>
                    <p style={{ 
                      fontSize: 'var(--font-size-sm)', 
                      fontWeight: 600, 
                      color: 'var(--cisa-gray)', 
                      marginBottom: 'var(--spacing-sm)' 
                    }}>
                      Version
                    </p>
                    <div style={{
                      display: 'inline-block',
                      padding: 'var(--spacing-xs) var(--spacing-md)',
                      backgroundColor: 'var(--cisa-gray-lighter)',
                      color: 'var(--cisa-gray-dark)',
                      borderRadius: '999px',
                      fontSize: 'var(--font-size-sm)',
                      fontWeight: 600
                    }}>
                      {modelInfo?.version || 'N/A'}
                    </div>
                  </div>
                  <div>
                    <p style={{ 
                      fontSize: 'var(--font-size-sm)', 
                      fontWeight: 600, 
                      color: 'var(--cisa-gray)', 
                      marginBottom: 'var(--spacing-sm)' 
                    }}>
                      Size
                    </p>
                    <div style={{
                      display: 'inline-block',
                      padding: 'var(--spacing-xs) var(--spacing-md)',
                      backgroundColor: 'var(--cisa-gray-lighter)',
                      color: 'var(--cisa-gray-dark)',
                      borderRadius: '999px',
                      fontSize: 'var(--font-size-sm)',
                      fontWeight: 600
                    }}>
                      {modelInfo?.size_gb ? `${modelInfo.size_gb} GB` : '—'}
                    </div>
                  </div>
                  <div>
                    <p style={{ 
                      fontSize: 'var(--font-size-sm)', 
                      fontWeight: 600, 
                      color: 'var(--cisa-gray)', 
                      marginBottom: 'var(--spacing-sm)' 
                    }}>
                      Status
                    </p>
                    <div style={{
                      display: 'inline-block',
                      padding: 'var(--spacing-xs) var(--spacing-md)',
                      backgroundColor: health?.ollama === 'ok' ? '#D1FAE5' : '#FEE2E2',
                      color: health?.ollama === 'ok' ? '#065F46' : '#991B1B',
                      borderRadius: '999px',
                      fontSize: 'var(--font-size-sm)',
                      fontWeight: 600
                    }}>
                      {health?.ollama === 'ok' ? 'Online' : 'Offline'}
                    </div>
                  </div>
                  {modelInfo?.status && (
                    <div>
                      <p style={{ 
                        fontSize: 'var(--font-size-sm)', 
                        fontWeight: 600, 
                        color: 'var(--cisa-gray)', 
                        marginBottom: 'var(--spacing-sm)' 
                      }}>
                        Availability
                      </p>
                      <div style={{
                        display: 'inline-block',
                        padding: 'var(--spacing-xs) var(--spacing-md)',
                        backgroundColor: modelInfo.status === 'available' ? '#D1FAE5' : '#FEE2E2',
                        color: modelInfo.status === 'available' ? '#065F46' : '#991B1B',
                        borderRadius: '999px',
                        fontSize: 'var(--font-size-sm)',
                        fontWeight: 600
                      }}>
                        {modelInfo.status === 'available' ? 'Available' : modelInfo.status === 'error' ? 'Error' : 'Unknown'}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Model Usage Statistics */}
              {(progress || monitoring) && (
                <div className="card" style={{ padding: 'var(--spacing-lg)' }}>
                  <h2 style={{ 
                    fontSize: 'var(--font-size-xl)', 
                    fontWeight: 600, 
                    color: 'var(--cisa-blue)', 
                    marginBottom: 'var(--spacing-md)' 
                  }}>
                    Model Usage Statistics
                  </h2>
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                    gap: 'var(--spacing-md)'
                  }}>
                    <div style={{
                      padding: 'var(--spacing-md)',
                      backgroundColor: '#F0F9FF',
                      borderRadius: 'var(--border-radius)',
                      border: '1px solid #BAE6FD'
                    }}>
                      <p style={{ 
                        fontSize: 'var(--font-size-sm)', 
                        color: 'var(--cisa-gray)', 
                        marginBottom: 'var(--spacing-xs)' 
                      }}>
                        Documents Processed
                      </p>
                      <p style={{ 
                        fontSize: 'var(--font-size-xxl)', 
                        fontWeight: 700, 
                        color: 'var(--cisa-blue)' 
                      }}>
                        {progress?.processed || monitoring?.file_processing?.completed?.count || 0}
                      </p>
                    </div>
                    <div style={{
                      padding: 'var(--spacing-md)',
                      backgroundColor: '#FEF3C7',
                      borderRadius: 'var(--border-radius)',
                      border: '1px solid #FDE68A'
                    }}>
                      <p style={{ 
                        fontSize: 'var(--font-size-sm)', 
                        color: 'var(--cisa-gray)', 
                        marginBottom: 'var(--spacing-xs)' 
                      }}>
                        Pending Processing
                      </p>
                      <p style={{ 
                        fontSize: 'var(--font-size-xxl)', 
                        fontWeight: 700, 
                        color: '#D97706' 
                      }}>
                        {progress?.incoming || monitoring?.file_processing?.docs?.count || 0}
                      </p>
                    </div>
                    <div style={{
                      padding: 'var(--spacing-md)',
                      backgroundColor: '#FEE2E2',
                      borderRadius: 'var(--border-radius)',
                      border: '1px solid #FECACA'
                    }}>
                      <p style={{ 
                        fontSize: 'var(--font-size-sm)', 
                        color: 'var(--cisa-gray)', 
                        marginBottom: 'var(--spacing-xs)' 
                      }}>
                        Processing Errors
                      </p>
                      <p style={{ 
                        fontSize: 'var(--font-size-xxl)', 
                        fontWeight: 700, 
                        color: '#DC2626' 
                      }}>
                        {progress?.errors || monitoring?.file_processing?.failed?.count || 0}
                      </p>
                    </div>
                    <div style={{
                      padding: 'var(--spacing-md)',
                      backgroundColor: '#D1FAE5',
                      borderRadius: 'var(--border-radius)',
                      border: '1px solid #A7F3D0'
                    }}>
                      <p style={{ 
                        fontSize: 'var(--font-size-sm)', 
                        color: 'var(--cisa-gray)', 
                        marginBottom: 'var(--spacing-xs)' 
                      }}>
                        Success Rate
                      </p>
                      <p style={{ 
                        fontSize: 'var(--font-size-xxl)', 
                        fontWeight: 700, 
                        color: '#059669' 
                      }}>
                        {(() => {
                          const processed = progress?.processed || monitoring?.file_processing?.completed?.count || 0
                          const errors = progress?.errors || monitoring?.file_processing?.failed?.count || 0
                          const total = processed + errors
                          if (total === 0) return '0%'
                          return `${Math.round((processed / total) * 100)}%`
                        })()}
                      </p>
                    </div>
                    {monitoring?.submissions?.analysis && (
                      <>
                        <div style={{
                          padding: 'var(--spacing-md)',
                          backgroundColor: '#E0E7FF',
                          borderRadius: 'var(--border-radius)',
                          border: '1px solid #C7D2FE'
                        }}>
                          <p style={{ 
                            fontSize: 'var(--font-size-sm)', 
                            color: 'var(--cisa-gray)', 
                            marginBottom: 'var(--spacing-xs)' 
                          }}>
                            Total Submissions
                          </p>
                          <p style={{ 
                            fontSize: 'var(--font-size-xxl)', 
                            fontWeight: 700, 
                            color: '#4F46E5' 
                          }}>
                            {monitoring.submissions.analysis.total || 0}
                          </p>
                        </div>
                        <div style={{
                          padding: 'var(--spacing-md)',
                          backgroundColor: '#F3E8FF',
                          borderRadius: 'var(--border-radius)',
                          border: '1px solid #E9D5FF'
                        }}>
                          <p style={{ 
                            fontSize: 'var(--font-size-sm)', 
                            color: 'var(--cisa-gray)', 
                            marginBottom: 'var(--spacing-xs)' 
                          }}>
                            With Model Results
                          </p>
                          <p style={{ 
                            fontSize: 'var(--font-size-xxl)', 
                            fontWeight: 700, 
                            color: '#9333EA' 
                          }}>
                            {monitoring.submissions.analysis.with_ollama_results || 0}
                          </p>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              )}

              {/* Processing Status */}
              {progress && (
                <div className="card" style={{ padding: 'var(--spacing-lg)' }}>
                  <h2 style={{ 
                    fontSize: 'var(--font-size-xl)', 
                    fontWeight: 600, 
                    color: 'var(--cisa-blue)', 
                    marginBottom: 'var(--spacing-md)' 
                  }}>
                    Processing Status
                  </h2>
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                    gap: 'var(--spacing-md)'
                  }}>
                    <div>
                      <p style={{ 
                        fontSize: 'var(--font-size-sm)', 
                        fontWeight: 600, 
                        color: 'var(--cisa-gray)', 
                        marginBottom: 'var(--spacing-xs)' 
                      }}>
                        Watcher Status
                      </p>
                      <div style={{
                        display: 'inline-block',
                        padding: 'var(--spacing-xs) var(--spacing-md)',
                        backgroundColor: progress.watcher_status === 'running' ? '#D1FAE5' : '#FEE2E2',
                        color: progress.watcher_status === 'running' ? '#065F46' : '#991B1B',
                        borderRadius: '999px',
                        fontSize: 'var(--font-size-sm)',
                        fontWeight: 600
                      }}>
                        {progress.watcher_status === 'running' ? 'Running' : progress.watcher_status === 'stopped' ? 'Stopped' : 'Unknown'}
                      </div>
                    </div>
                    <div>
                      <p style={{ 
                        fontSize: 'var(--font-size-sm)', 
                        fontWeight: 600, 
                        color: 'var(--cisa-gray)', 
                        marginBottom: 'var(--spacing-xs)' 
                      }}>
                        Library Files
                      </p>
                      <p style={{ 
                        fontSize: 'var(--font-size-lg)', 
                        fontWeight: 700, 
                        color: 'var(--cisa-blue)' 
                      }}>
                        {progress.library || 0}
                      </p>
                    </div>
                    <div>
                      <p style={{ 
                        fontSize: 'var(--font-size-sm)', 
                        fontWeight: 600, 
                        color: 'var(--cisa-gray)', 
                        marginBottom: 'var(--spacing-xs)' 
                      }}>
                        Review Files
                      </p>
                      <p style={{ 
                        fontSize: 'var(--font-size-lg)', 
                        fontWeight: 700, 
                        color: '#9333EA' 
                      }}>
                        {progress.review || 0}
                      </p>
                    </div>
                    {progress.timestamp && (
                      <div>
                        <p style={{ 
                          fontSize: 'var(--font-size-sm)', 
                          fontWeight: 600, 
                          color: 'var(--cisa-gray)', 
                          marginBottom: 'var(--spacing-xs)' 
                        }}>
                          Last Update
                        </p>
                        <p style={{ 
                          fontSize: 'var(--font-size-sm)', 
                          color: 'var(--cisa-gray-dark)' 
                        }}>
                          {formatTimestamp(progress.timestamp)}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

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
                <div className="card" style={{ padding: 'var(--spacing-lg)' }}>
                  <h2 style={{ 
                    fontSize: 'var(--font-size-xl)', 
                    fontWeight: 600, 
                    color: 'var(--cisa-blue)', 
                    marginBottom: 'var(--spacing-md)' 
                  }}>
                    System Health
                  </h2>
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                    gap: 'var(--spacing-md)'
                  }}>
                    <div>
                      <p style={{ 
                        fontSize: 'var(--font-size-sm)', 
                        fontWeight: 600, 
                        color: 'var(--cisa-gray)', 
                        marginBottom: 'var(--spacing-xs)' 
                      }}>
                        Flask
                      </p>
                      <div style={{
                        display: 'inline-block',
                        padding: 'var(--spacing-xs) var(--spacing-md)',
                        backgroundColor: health.flask === 'ok' ? '#D1FAE5' : '#FEE2E2',
                        color: health.flask === 'ok' ? '#065F46' : '#991B1B',
                        borderRadius: '999px',
                        fontSize: 'var(--font-size-sm)',
                        fontWeight: 600
                      }}>
                        {health.flask === 'ok' ? 'Online' : 'Offline'}
                      </div>
                    </div>
                    <div>
                      <p style={{ 
                        fontSize: 'var(--font-size-sm)', 
                        fontWeight: 600, 
                        color: 'var(--cisa-gray)', 
                        marginBottom: 'var(--spacing-xs)' 
                      }}>
                        Ollama
                      </p>
                      <div style={{
                        display: 'inline-block',
                        padding: 'var(--spacing-xs) var(--spacing-md)',
                        backgroundColor: health.ollama === 'ok' ? '#D1FAE5' : '#FEE2E2',
                        color: health.ollama === 'ok' ? '#065F46' : '#991B1B',
                        borderRadius: '999px',
                        fontSize: 'var(--font-size-sm)',
                        fontWeight: 600
                      }}>
                        {health.ollama === 'ok' ? 'Online' : 'Offline'}
                      </div>
                    </div>
                    <div>
                      <p style={{ 
                        fontSize: 'var(--font-size-sm)', 
                        fontWeight: 600, 
                        color: 'var(--cisa-gray)', 
                        marginBottom: 'var(--spacing-xs)' 
                      }}>
                        Supabase
                      </p>
                      <div style={{
                        display: 'inline-block',
                        padding: 'var(--spacing-xs) var(--spacing-md)',
                        backgroundColor: health.supabase === 'ok' ? '#D1FAE5' : '#FEE2E2',
                        color: health.supabase === 'ok' ? '#065F46' : '#991B1B',
                        borderRadius: '999px',
                        fontSize: 'var(--font-size-sm)',
                        fontWeight: 600
                      }}>
                        {health.supabase === 'ok' ? 'Online' : 'Offline'}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Footer Info */}
              <div style={{
                fontSize: 'var(--font-size-sm)',
                color: 'var(--cisa-gray)',
                textAlign: 'center',
                marginTop: 'var(--spacing-md)'
              }}>
                <p>Last refreshed: {lastRefresh ? lastRefresh.toLocaleString() : 'Never'}</p>
                <p style={{ marginTop: 'var(--spacing-xs)' }}>Auto-refreshes every 60 seconds</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </RoleGate>
  )
}
