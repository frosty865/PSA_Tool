'use client'

import { useEffect, useState } from 'react'
import { fetchWithAuth } from '../../lib/fetchWithAuth'
import '@/styles/cisa.css'

function SystemStatusPage() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdate, setLastUpdate] = useState(null)
  const [simpleHealth, setSimpleHealth] = useState({
    flask: 'unknown',
    ollama: 'unknown',
    supabase: 'unknown'
  })

  const loadStatus = async (showRefreshing = false) => {
    if (showRefreshing) setRefreshing(true)
    try {
      const res = await fetchWithAuth('/api/dashboard/system', { cache: 'no-store' })
      
      if (!res.ok) {
        const errorText = await res.text()
        console.error('[SYSTEM DASHBOARD] Response not OK:', res.status, errorText)
        throw new Error(`HTTP ${res.status}: ${errorText.substring(0, 200)}`)
      }
      
      const data = await res.json()
      
      setStatus(data)
      setError(null)
      setLastUpdate(new Date())
    } catch (e) {
      console.error('[SYSTEM DASHBOARD] Error loading system status:', e)
      console.error('[SYSTEM DASHBOARD] Error stack:', e.stack)
      setError(e.message)
    } finally {
      setLoading(false)
      if (showRefreshing) setRefreshing(false)
    }
  }

  // Live health check using Next.js API proxy (same as admin dashboard)
  useEffect(() => {
    async function fetchSystemHealth() {
      try {
        const res = await fetch('/api/system/health', { cache: 'no-store' })
        if (res.ok) {
          const data = await res.json()
          setSimpleHealth({
            flask: data.components?.flask || 'unknown',
            ollama: data.components?.ollama || 'unknown',
            supabase: data.components?.supabase || 'unknown'
          })
        } else {
          throw new Error(`Health check failed: ${res.status}`)
        }
      } catch (err) {
        console.error('System health check failed:', err)
        setSimpleHealth({
          flask: 'offline',
          ollama: 'offline',
          supabase: 'offline'
        })
      }
    }

    fetchSystemHealth()
    const interval = setInterval(fetchSystemHealth, 10000) // refresh every 10s
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    loadStatus()
    // Refresh every 10 seconds for real-time updates (balance between freshness and server load)
    const id = setInterval(() => {
      loadStatus(true)
    }, 10000)
    return () => {
      clearInterval(id)
    }
  }, [])

  const getStatusColor = (serviceStatus) => {
    switch (serviceStatus) {
      case 'online':
      case 'active':
      case 'running': return 'var(--cisa-success)'
      case 'warning': return 'var(--cisa-warning)'
      case 'error':
      case 'offline': return 'var(--cisa-red)'
      case 'unavailable': return 'var(--cisa-gray)'
      default: return 'var(--cisa-gray)'
    }
  }

  const getStatusBadgeStyle = (serviceStatus) => {
    switch (serviceStatus) {
      case 'online':
      case 'active':
      case 'running': 
        return { backgroundColor: 'rgba(40, 167, 69, 0.1)', color: '#155724' }
      case 'warning': 
        return { backgroundColor: 'rgba(255, 193, 7, 0.1)', color: '#856404' }
      case 'error':
      case 'offline': 
        return { backgroundColor: 'var(--cisa-red-light)', color: 'var(--cisa-red-dark)' }
      case 'unavailable': 
        return { backgroundColor: 'var(--cisa-gray-lighter)', color: 'var(--cisa-gray)' }
      default: 
        return { backgroundColor: 'var(--cisa-gray-lighter)', color: 'var(--cisa-gray)' }
    }
  }

  if (loading && !status) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '256px' }}>
        <div style={{
          width: '48px',
          height: '48px',
          border: '3px solid var(--cisa-gray-light)',
          borderTopColor: 'var(--cisa-blue)',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }}></div>
        <p style={{ marginLeft: 'var(--spacing-md)', color: 'var(--cisa-gray)' }}>Loading system status...</p>
      </div>
    )
  }

  if (error && !status) {
    return (
      <div className="alert alert-danger">
        <p style={{ fontWeight: 600, margin: 0, marginBottom: 'var(--spacing-sm)' }}>Error loading system status: {error}</p>
        <button 
          onClick={() => loadStatus(true)}
          className="btn btn-danger btn-sm"
          style={{ marginTop: 'var(--spacing-sm)' }}
        >
          Retry
        </button>
      </div>
    )
  }

  if (!status) {
    return <div style={{ padding: 'var(--spacing-lg)', color: 'var(--cisa-gray)' }}>No system status data available</div>
  }

  return (
    <div style={{ padding: 'var(--spacing-lg)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-lg)' }}>
        <h1 style={{ fontSize: 'var(--font-size-xxl)', fontWeight: 700, color: 'var(--cisa-blue)', margin: 0 }}>
          System Health Dashboard
        </h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)' }}>
          {lastUpdate && (
            <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--cisa-gray)' }}>
              Last updated: {lastUpdate.toLocaleTimeString()}
            </span>
          )}
          {refreshing && (
            <div style={{
              width: '16px',
              height: '16px',
              border: '2px solid var(--cisa-gray-light)',
              borderTopColor: 'var(--cisa-blue)',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite'
            }}></div>
          )}
          <button
            onClick={() => loadStatus(true)}
            className="btn btn-primary btn-sm"
            disabled={refreshing}
            style={{ opacity: refreshing ? 0.6 : 1 }}
          >
            {refreshing ? 'Refreshing...' : '🔄 Refresh'}
          </button>
        </div>
      </div>
      
      {error && status && (
        <div className="alert alert-warning" style={{ marginBottom: 'var(--spacing-lg)' }}>
          <p style={{ margin: 0 }}>⚠️ Warning: {error} (showing last known status)</p>
        </div>
      )}

    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-xl)' }}>

      {/* Live Health Status - Single source of truth */}
      <div className="card" style={{ marginBottom: 'var(--spacing-xl)' }}>
        <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, color: 'var(--cisa-blue)', marginBottom: 'var(--spacing-md)' }}>
          System Health Status
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--spacing-md)' }}>
          {['flask', 'ollama', 'supabase'].map(key => (
            <div 
              key={key} 
              style={{
                padding: 'var(--spacing-md)',
                borderRadius: 'var(--border-radius-lg)',
                backgroundColor: simpleHealth[key] === 'online' ? 'rgba(40, 167, 69, 0.1)' : 'rgba(220, 53, 69, 0.1)',
                border: `1px solid ${simpleHealth[key] === 'online' ? 'rgba(40, 167, 69, 0.3)' : 'rgba(220, 53, 69, 0.3)'}`
              }}
            >
              <h4 style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600, color: 'var(--cisa-gray)', marginBottom: 'var(--spacing-xs)' }}>
                {key.charAt(0).toUpperCase() + key.slice(1)} Server
              </h4>
              <p style={{ 
                fontSize: 'var(--font-size-xs)', 
                color: simpleHealth[key] === 'online' ? '#155724' : 'var(--cisa-red-dark)',
                fontWeight: 600
              }}>
                {simpleHealth[key]}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* File Processing Status - Only show if we have valid data */}
      {status.files && (status.files.incoming > 0 || status.files.library > 0 || status.files.extracted_text > 0 || status.files.errors > 0 || status.processing?.active_jobs > 0) && (
        <div className="card">
          <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, color: 'var(--cisa-blue)', marginBottom: 'var(--spacing-lg)' }}>File Processing Pipeline</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--spacing-lg)' }}>
            <div style={{
              textAlign: 'center',
              padding: 'var(--spacing-lg)',
              backgroundColor: 'rgba(255, 193, 7, 0.1)',
              borderRadius: 'var(--border-radius-lg)',
              border: '1px solid rgba(255, 193, 7, 0.3)'
            }}>
              <p style={{ fontSize: 'var(--font-size-xxl)', fontWeight: 700, color: '#856404', margin: 0 }}>{status.files.incoming || 0}</p>
              <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--cisa-gray)', marginTop: 'var(--spacing-xs)' }}>Incoming Files</p>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', opacity: 0.7 }}>Awaiting processing</p>
            </div>
            <div style={{
              textAlign: 'center',
              padding: 'var(--spacing-lg)',
              backgroundColor: 'var(--cisa-blue-lightest)',
              borderRadius: 'var(--border-radius-lg)',
              border: '1px solid var(--cisa-blue-lighter)'
            }}>
              <p style={{ fontSize: 'var(--font-size-xxl)', fontWeight: 700, color: 'var(--cisa-blue)', margin: 0 }}>{status.files.library || 0}</p>
              <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--cisa-gray)', marginTop: 'var(--spacing-xs)' }}>Processed Files</p>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', opacity: 0.7 }}>In library</p>
            </div>
            <div style={{
              textAlign: 'center',
              padding: 'var(--spacing-lg)',
              backgroundColor: 'rgba(40, 167, 69, 0.1)',
              borderRadius: 'var(--border-radius-lg)',
              border: '1px solid rgba(40, 167, 69, 0.3)'
            }}>
              <p style={{ fontSize: 'var(--font-size-xxl)', fontWeight: 700, color: '#155724', margin: 0 }}>{status.files.extracted_text || 0}</p>
              <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--cisa-gray)', marginTop: 'var(--spacing-xs)' }}>Extracted Text</p>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', opacity: 0.7 }}>Ready for analysis</p>
            </div>
            <div style={{
              textAlign: 'center',
              padding: 'var(--spacing-lg)',
              backgroundColor: 'var(--cisa-red-light)',
              borderRadius: 'var(--border-radius-lg)',
              border: '1px solid var(--cisa-red)'
            }}>
              <p style={{ fontSize: 'var(--font-size-xxl)', fontWeight: 700, color: 'var(--cisa-red-dark)', margin: 0 }}>{status.files.errors || 0}</p>
              <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--cisa-gray)', marginTop: 'var(--spacing-xs)' }}>Errors</p>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', opacity: 0.7 }}>Failed processing</p>
            </div>
          </div>
          
          {/* Processing Status */}
          <div style={{
            marginTop: 'var(--spacing-lg)',
            padding: 'var(--spacing-lg)',
            backgroundColor: 'var(--cisa-gray-lighter)',
            borderRadius: 'var(--border-radius-lg)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <p style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600, color: 'var(--cisa-gray)', margin: 0 }}>Processing Status</p>
                <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', opacity: 0.7, marginTop: 'var(--spacing-xs)' }}>
                  Active Jobs: {status.processing?.active_jobs || 0} | 
                  Ready: {status.processing?.ready ? 'Yes' : 'No'}
                </p>
              </div>
              <span style={{
                padding: 'var(--spacing-xs) var(--spacing-md)',
                borderRadius: '999px',
                fontSize: 'var(--font-size-xs)',
                fontWeight: 600,
                ...(status.processing?.ready ? 
                  { backgroundColor: 'rgba(40, 167, 69, 0.1)', color: '#155724' } : 
                  { backgroundColor: 'var(--cisa-gray-light)', color: 'var(--cisa-gray)' }
                )
              }}>
                {status.processing?.ready ? 'Ready' : 'Idle'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Parsing & Processing Statistics */}
      {status.parsing && (
        <div className="card">
          <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, color: 'var(--cisa-blue)', marginBottom: 'var(--spacing-lg)' }}>Parsing & Processing Statistics</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 'var(--spacing-lg)' }}>
            <div style={{ textAlign: 'center', padding: 'var(--spacing-lg)', backgroundColor: 'var(--cisa-blue-lightest)', borderRadius: 'var(--border-radius-lg)' }}>
              <p style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: 'var(--cisa-blue)', margin: 0 }}>{status.parsing.total_submissions || 0}</p>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', marginTop: 'var(--spacing-xs)' }}>Total Submissions</p>
            </div>
            <div style={{ textAlign: 'center', padding: 'var(--spacing-lg)', backgroundColor: 'rgba(255, 193, 7, 0.1)', borderRadius: 'var(--border-radius-lg)' }}>
              <p style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: '#856404', margin: 0 }}>{status.parsing.pending_review || 0}</p>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', marginTop: 'var(--spacing-xs)' }}>Pending Review</p>
            </div>
            <div style={{ textAlign: 'center', padding: 'var(--spacing-lg)', backgroundColor: 'rgba(40, 167, 69, 0.1)', borderRadius: 'var(--border-radius-lg)' }}>
              <p style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: '#155724', margin: 0 }}>{status.parsing.approved || 0}</p>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', marginTop: 'var(--spacing-xs)' }}>Approved</p>
            </div>
            <div style={{ textAlign: 'center', padding: 'var(--spacing-lg)', backgroundColor: 'var(--cisa-red-light)', borderRadius: 'var(--border-radius-lg)' }}>
              <p style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: 'var(--cisa-red-dark)', margin: 0 }}>{status.parsing.rejected || 0}</p>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', marginTop: 'var(--spacing-xs)' }}>Rejected</p>
            </div>
            <div style={{ textAlign: 'center', padding: 'var(--spacing-lg)', backgroundColor: 'rgba(138, 43, 226, 0.1)', borderRadius: 'var(--border-radius-lg)' }}>
              <p style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: '#6f42c1', margin: 0 }}>{status.parsing.total_vulnerabilities || 0}</p>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', marginTop: 'var(--spacing-xs)' }}>Vulnerabilities</p>
            </div>
            <div style={{ textAlign: 'center', padding: 'var(--spacing-lg)', backgroundColor: 'rgba(75, 0, 130, 0.1)', borderRadius: 'var(--border-radius-lg)' }}>
              <p style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: '#4b0082', margin: 0 }}>{status.parsing.total_ofcs || 0}</p>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', marginTop: 'var(--spacing-xs)' }}>Options for Consideration</p>
            </div>
          </div>

          {/* Recent Processing Activity */}
          {status.parsing.recent_submissions && status.parsing.recent_submissions.length > 0 && (
            <div style={{ marginTop: 'var(--spacing-xl)' }}>
              <h4 style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600, color: 'var(--cisa-gray)', marginBottom: 'var(--spacing-md)' }}>Recent Processing Activity</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)', maxHeight: '256px', overflowY: 'auto' }}>
                {status.parsing.recent_submissions.map((sub) => (
                  <div key={sub.id} style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: 'var(--spacing-sm)',
                    backgroundColor: 'var(--cisa-gray-lighter)',
                    borderRadius: 'var(--border-radius)',
                    fontSize: 'var(--font-size-sm)'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)' }}>
                      <span style={{
                        width: '8px',
                        height: '8px',
                        borderRadius: '50%',
                        backgroundColor: sub.status === 'approved' ? 'var(--cisa-success)' :
                                        sub.status === 'rejected' ? 'var(--cisa-red)' :
                                        sub.status === 'pending_review' ? 'var(--cisa-warning)' :
                                        'var(--cisa-gray)'
                      }}></span>
                      <span style={{ fontFamily: 'monospace', fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)' }}>{sub.id.slice(0, 8)}...</span>
                      <span style={{
                        padding: 'var(--spacing-xs) var(--spacing-sm)',
                        borderRadius: 'var(--border-radius)',
                        fontSize: 'var(--font-size-xs)',
                        fontWeight: 600,
                        ...(sub.status === 'approved' ? { backgroundColor: 'rgba(40, 167, 69, 0.1)', color: '#155724' } :
                            sub.status === 'rejected' ? { backgroundColor: 'var(--cisa-red-light)', color: 'var(--cisa-red-dark)' } :
                            sub.status === 'pending_review' ? { backgroundColor: 'rgba(255, 193, 7, 0.1)', color: '#856404' } :
                            { backgroundColor: 'var(--cisa-gray-lighter)', color: 'var(--cisa-gray)' })
                      }}>
                        {sub.status}
                      </span>
                    </div>
                    <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', opacity: 0.7 }}>
                      {new Date(sub.created_at).toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Learning Statistics */}
      {status.learning && (
        <div className="card">
          <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, color: 'var(--cisa-blue)', marginBottom: 'var(--spacing-lg)' }}>Learning System</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--spacing-lg)' }}>
            <div style={{ textAlign: 'center', padding: 'var(--spacing-lg)', backgroundColor: 'rgba(138, 43, 226, 0.1)', borderRadius: 'var(--border-radius-lg)' }}>
              <p style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: '#6f42c1', margin: 0 }}>{status.learning.total_events || 0}</p>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', marginTop: 'var(--spacing-xs)' }}>Total Learning Events</p>
            </div>
            <div style={{ textAlign: 'center', padding: 'var(--spacing-lg)', backgroundColor: 'rgba(40, 167, 69, 0.1)', borderRadius: 'var(--border-radius-lg)' }}>
              <p style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: '#155724', margin: 0 }}>{status.learning.approved_events || 0}</p>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', marginTop: 'var(--spacing-xs)' }}>Approved Events</p>
            </div>
          </div>
        </div>
      )}

      {/* Python & Flask Service Information */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 'var(--spacing-lg)' }}>
        {/* Python Runtime Info */}
        {status.python && (
          <div className="card">
            <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, color: 'var(--cisa-blue)', marginBottom: 'var(--spacing-md)' }}>🐍 Python Runtime</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)', fontSize: 'var(--font-size-sm)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--cisa-gray)' }}>Status:</span>
                <span style={{ 
                  fontWeight: 600,
                  color: (status.python.runtime_status === 'running' || status.python.status === 'running') ? 'var(--cisa-success)' : 'var(--cisa-red)'
                }}>
                  {(status.python.runtime_status === 'running' || status.python.status === 'running') ? '✅ Running' : '❌ Stopped'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--cisa-gray)' }}>Version:</span>
                <span style={{ fontWeight: 600, fontFamily: 'monospace' }}>{status.python.version || 'N/A'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--cisa-gray)' }}>Model:</span>
                <span style={{ fontWeight: 600 }}>{status.python.model || 'N/A'}</span>
              </div>
              {status.python.executable && status.python.executable !== 'unknown' && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: 'var(--cisa-gray)' }}>Executable:</span>
                  <span style={{ fontFamily: 'monospace', fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {status.python.executable}
                  </span>
                </div>
              )}
              {status.python.platform && Object.keys(status.python.platform).length > 0 && (
                <div style={{ paddingTop: 'var(--spacing-sm)', borderTop: '1px solid var(--cisa-gray-light)', fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)' }}>
                  <div>Platform: {status.python.platform.system} {status.python.platform.release}</div>
                  {status.python.platform.machine && <div>Architecture: {status.python.platform.machine}</div>}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Flask Service Info */}
        {status.flask && (
          <div className="card">
            <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, color: 'var(--cisa-blue)', marginBottom: 'var(--spacing-md)' }}>🔧 Flask Server</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)', fontSize: 'var(--font-size-sm)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--cisa-gray)' }}>Version:</span>
                <span style={{ fontWeight: 600, fontFamily: 'monospace' }}>{status.flask.version || 'N/A'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--cisa-gray)' }}>Environment:</span>
                <span style={{
                  padding: 'var(--spacing-xs) var(--spacing-sm)',
                  borderRadius: 'var(--border-radius)',
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: 600,
                  ...(status.flask.environment === 'production' ? 
                    { backgroundColor: 'rgba(0, 113, 188, 0.1)', color: 'var(--cisa-blue)' } : 
                    { backgroundColor: 'rgba(255, 193, 7, 0.1)', color: '#856404' })
                }}>
                  {status.flask.environment || 'N/A'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--cisa-gray)' }}>Debug Mode:</span>
                <span style={{
                  padding: 'var(--spacing-xs) var(--spacing-sm)',
                  borderRadius: 'var(--border-radius)',
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: 600,
                  ...(status.flask.debug ? 
                    { backgroundColor: 'var(--cisa-red-light)', color: 'var(--cisa-red-dark)' } : 
                    { backgroundColor: 'rgba(40, 167, 69, 0.1)', color: '#155724' })
                }}>
                  {status.flask.debug ? '⚠️ Enabled' : '✅ Disabled'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* GPU Utilization */}
      {status.gpu && (
        <div className="card">
          <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, color: 'var(--cisa-blue)', marginBottom: 'var(--spacing-lg)' }}>🎮 GPU Utilization</h3>
          {status.gpu.available ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--spacing-lg)' }}>
              <div style={{ textAlign: 'center', padding: 'var(--spacing-lg)', backgroundColor: 'var(--cisa-blue-lightest)', borderRadius: 'var(--border-radius-lg)' }}>
                <p style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: 'var(--cisa-blue)', margin: 0 }}>{status.gpu.utilization || 0}%</p>
                <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', marginTop: 'var(--spacing-xs)' }}>GPU Utilization</p>
              </div>
              <div style={{ textAlign: 'center', padding: 'var(--spacing-lg)', backgroundColor: 'rgba(138, 43, 226, 0.1)', borderRadius: 'var(--border-radius-lg)' }}>
                <p style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: '#6f42c1', margin: 0 }}>
                  {status.gpu.memory_used ? `${status.gpu.memory_used.toFixed(2)} GB` : 'N/A'}
                </p>
                <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', marginTop: 'var(--spacing-xs)' }}>Memory Used</p>
                {status.gpu.memory_total && (
                  <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', opacity: 0.7, marginTop: 'var(--spacing-xs)' }}>
                    of {status.gpu.memory_total.toFixed(2)} GB
                  </p>
                )}
              </div>
              {status.gpu.devices && status.gpu.devices.length > 0 && (
                <div style={{ textAlign: 'center', padding: 'var(--spacing-lg)', backgroundColor: 'var(--cisa-gray-lighter)', borderRadius: 'var(--border-radius-lg)' }}>
                  <p style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: 'var(--cisa-gray)', margin: 0 }}>{status.gpu.devices.length}</p>
                  <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', marginTop: 'var(--spacing-xs)' }}>GPU Devices</p>
                </div>
              )}
            </div>
          ) : (
            <div style={{ padding: 'var(--spacing-lg)', backgroundColor: 'var(--cisa-gray-lighter)', borderRadius: 'var(--border-radius-lg)', textAlign: 'center' }}>
              <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--cisa-gray)', margin: 0, marginBottom: 'var(--spacing-xs)' }}>
                GPU not detected
              </p>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', opacity: 0.7, margin: 0 }}>
                {typeof status.gpu !== 'undefined' 
                  ? 'CPU processing mode is active. Install nvidia-ml-py to detect GPU if available.'
                  : 'GPU information not available'}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Backend Statistics */}
      {status.backend && (
        <div className="card">
          <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, color: 'var(--cisa-blue)', marginBottom: 'var(--spacing-lg)' }}>⚙️ Backend Statistics</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--spacing-lg)' }}>
            <div style={{ textAlign: 'center', padding: 'var(--spacing-lg)', backgroundColor: 'var(--cisa-blue-lightest)', borderRadius: 'var(--border-radius-lg)' }}>
              <p style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: 'var(--cisa-blue)', margin: 0 }}>{status.backend.active_connections || 0}</p>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', marginTop: 'var(--spacing-xs)' }}>Active Connections</p>
            </div>
            <div style={{ textAlign: 'center', padding: 'var(--spacing-lg)', backgroundColor: 'rgba(40, 167, 69, 0.1)', borderRadius: 'var(--border-radius-lg)' }}>
              <p style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: '#155724', margin: 0 }}>{status.backend.requests_per_minute || 0}</p>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', marginTop: 'var(--spacing-xs)' }}>Requests/Min</p>
            </div>
            <div style={{ textAlign: 'center', padding: 'var(--spacing-lg)', backgroundColor: 'rgba(255, 193, 7, 0.1)', borderRadius: 'var(--border-radius-lg)' }}>
              <p style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: '#856404', margin: 0 }}>
                {status.backend.avg_response_time ? `${status.backend.avg_response_time}ms` : 'N/A'}
              </p>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', marginTop: 'var(--spacing-xs)' }}>Avg Response Time</p>
            </div>
            <div style={{ textAlign: 'center', padding: 'var(--spacing-lg)', backgroundColor: 'var(--cisa-gray-lighter)', borderRadius: 'var(--border-radius-lg)' }}>
              <p style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: 'var(--cisa-gray)', margin: 0 }}>{status.backend.queue_size || 0}</p>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', marginTop: 'var(--spacing-xs)' }}>Queue Size</p>
            </div>
          </div>
        </div>
      )}

      {/* Ollama Models */}
      {status.services?.ollama_models && status.services.ollama_models.length > 0 && (
        <div className="card">
          <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, color: 'var(--cisa-blue)', marginBottom: 'var(--spacing-md)' }}>🤖 Available Ollama Models</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 'var(--spacing-md)' }}>
            {status.services.ollama_models.map((model, idx) => (
              <div key={idx} style={{
                backgroundColor: 'var(--cisa-gray-lighter)',
                borderRadius: 'var(--border-radius-lg)',
                padding: 'var(--spacing-md)',
                border: '1px solid var(--cisa-gray-light)'
              }}>
                <div style={{ fontFamily: 'monospace', fontSize: 'var(--font-size-sm)', fontWeight: 600, color: 'var(--cisa-blue)', marginBottom: 'var(--spacing-xs)' }}>{model}</div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)' }}>Model {idx + 1}</div>
              </div>
            ))}
          </div>
          {status.services.ollama_base_url && (
            <div style={{ marginTop: 'var(--spacing-md)', fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)' }}>
              Ollama Base URL: <span style={{ fontFamily: 'monospace' }}>{status.services.ollama_base_url}</span>
            </div>
          )}
        </div>
      )}
    </div>
    </div>
  )
}

export default SystemStatusPage
