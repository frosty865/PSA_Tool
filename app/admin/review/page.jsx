'use client'

import { useEffect, useState } from 'react'
import { fetchWithAuth } from '../../lib/fetchWithAuth'
import RoleGate from '@/components/RoleGate'
import '@/styles/cisa.css'

export default function AdminReviewPage() {
  const [submissions, setSubmissions] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [processing, setProcessing] = useState(null)
  
  // System monitoring state
  const [progress, setProgress] = useState(null)
  const [logs, setLogs] = useState([])
  const [logsExpanded, setLogsExpanded] = useState(false)
  const [controlLoading, setControlLoading] = useState(false)

  useEffect(() => {
    loadSubmissions()
    const interval = setInterval(loadSubmissions, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [])

  // Poll progress.json every 10 seconds
  useEffect(() => {
    const fetchProgress = async () => {
      try {
        const res = await fetch('/api/system/progress', { cache: 'no-store' })
        if (res.ok) {
          const data = await res.json()
          setProgress(data)
        }
      } catch (err) {
        console.error('Error fetching progress:', err)
      }
    }

    fetchProgress()
    const timer = setInterval(fetchProgress, 10000)
    return () => clearInterval(timer)
  }, [])

  // Live log stream (Server-Sent Events with polling fallback)
  useEffect(() => {
    let pollInterval = null
    let evtSource = null
    
    // Initial load of recent logs
    const loadInitialLogs = async () => {
      try {
        const res = await fetch('/api/system/logs?tail=20', { cache: 'no-store' })
        if (res.ok) {
          const data = await res.json()
          if (data.lines && data.lines.length > 0) {
            setLogs(data.lines)
          }
        }
      } catch (err) {
        console.error('Error loading initial logs:', err)
      }
    }

    // Setup SSE connection to Flask
    const setupSSE = () => {
      try {
        // Detect Flask URL - use production tunnel URL if not localhost
        const isProduction = typeof window !== 'undefined' && 
                           window.location.hostname !== 'localhost' && 
                           window.location.hostname !== '127.0.0.1'
        const flaskUrl = isProduction 
          ? 'https://flask.frostech.site'
          : 'http://localhost:8080'
        
        const streamUrl = `${flaskUrl}/api/system/logstream`
        
        evtSource = new EventSource(streamUrl)

        evtSource.onmessage = (e) => {
          if (e.data) {
            setLogs((prev) => {
              const newLines = [...prev, e.data]
              // Keep only last 50 lines to prevent memory issues
              return newLines.slice(-50)
            })
          }
        }

        evtSource.onerror = (err) => {
          console.warn('SSE connection error, falling back to polling:', err)
          if (evtSource) {
            evtSource.close()
          }
          setupPolling()
        }
      } catch (error) {
        console.warn('SSE not available, using polling:', error)
        setupPolling()
      }
    }

    // Fallback polling method
    const setupPolling = () => {
      pollInterval = setInterval(async () => {
        try {
          const res = await fetch('/api/system/logs?tail=5', { cache: 'no-store' })
          if (res.ok) {
            const data = await res.json()
            if (data.lines && data.lines.length > 0) {
              setLogs((prev) => {
                const existingLastLine = prev[prev.length - 1]
                const newLines = data.lines.filter((line) => line !== existingLastLine)
                const combined = [...prev, ...newLines]
                return combined.slice(-50)
              })
            }
          }
        } catch (err) {
          console.error('Error polling logs:', err)
        }
      }, 5000)
    }

    loadInitialLogs()
    setupSSE()

    return () => {
      if (evtSource) {
        evtSource.close()
      }
      if (pollInterval) {
        clearInterval(pollInterval)
      }
    }
  }, [])

  // Control action handler
  async function controlAction(action) {
    try {
      setControlLoading(true)
      const res = await fetch('/api/system/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ action })
      })
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ message: 'Control action failed' }))
        throw new Error(errorData.message || `HTTP ${res.status}`)
      }
      
      const data = await res.json()
      
      // Check if response indicates an error
      if (data.status === 'error') {
        throw new Error(data.message || 'Control action failed')
      }
      
      const message = data.message || data.status || 'Action completed'
      alert(`✅ ${message}`)
      
      // Refresh progress after action
      setTimeout(async () => {
        try {
          const progressRes = await fetch('/api/system/progress', { cache: 'no-store' })
          if (progressRes.ok) {
            const progressData = await progressRes.json()
            setProgress(progressData)
          }
        } catch (err) {
          console.error('Error refreshing progress:', err)
        }
      }, 1000)
    } catch (err) {
      console.error('Error in control action:', err)
      alert(`❌ Error: ${err.message}`)
    } finally {
      setControlLoading(false)
    }
  }

  async function loadSubmissions() {
    try {
      setLoading(true)
      setError(null)
      const res = await fetchWithAuth('/api/admin/submissions?status=pending_review', { 
        cache: 'no-store' 
      })
      
      if (!res.ok) {
        throw new Error(`Failed to load submissions: ${res.status}`)
      }
      
      const data = await res.json()
      const subs = data.allSubmissions || data.submissions || []
      
      // Enrich submissions with vulnerability and OFC counts
      const enriched = await Promise.all(subs.map(async (sub) => {
        let vulnCount = 0
        let ofcCount = 0
        let vulnerabilities = []
        let ofcs = []
        
        // Parse submission data
        let parsedData = {}
        try {
          if (sub.data) {
            parsedData = typeof sub.data === 'string' ? JSON.parse(sub.data) : sub.data
          }
        } catch (e) {
          console.warn('Error parsing submission data:', e)
        }
        
        // Extract vulnerabilities
        if (Array.isArray(parsedData.vulnerabilities)) {
          vulnerabilities = parsedData.vulnerabilities
          vulnCount = vulnerabilities.length
        } else if (parsedData.vulnerability) {
          vulnerabilities = [parsedData.vulnerability]
          vulnCount = 1
        }
        
        // Extract OFCs
        if (Array.isArray(parsedData.options_for_consideration)) {
          ofcs = parsedData.options_for_consideration
          ofcCount = ofcs.length
        } else if (Array.isArray(parsedData.ofcs)) {
          ofcs = parsedData.ofcs
          ofcCount = ofcs.length
        } else if (parsedData.options_for_consideration) {
          ofcs = [parsedData.options_for_consideration]
          ofcCount = 1
        }
        
        return {
          ...sub,
          document_name: sub.document_name || sub.source_file || sub.title || `Submission ${sub.id.slice(0, 8)}`,
          created_at: sub.created_at || sub.createdAt || new Date().toISOString(),
          vulnerability_count: vulnCount,
          ofc_count: ofcCount,
          vulnerabilities,
          ofcs,
          summary: parsedData.summary || sub.summary || 'No summary available'
        }
      }))
      
      setSubmissions(enriched)
    } catch (err) {
      console.error('Error loading submissions:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function approveSubmission(id) {
    if (!confirm('Approve this submission and publish to production tables?')) {
      return
    }
    
    try {
      setProcessing(id)
      const res = await fetchWithAuth(`/api/submissions/${id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'approve' })
      })
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ error: 'Failed to approve' }))
        throw new Error(errorData.error || 'Failed to approve submission')
      }
      
      // Remove from list
      setSubmissions(subs => subs.filter(s => s.id !== id))
      setSelected(null)
      alert('✅ Submission approved and published to production tables!')
    } catch (err) {
      console.error('Error approving submission:', err)
      alert('❌ Error approving submission: ' + err.message)
    } finally {
      setProcessing(null)
    }
  }

  async function rejectSubmission(id) {
    const reason = prompt('Reason for rejection (optional):')
    if (reason === null) return // User cancelled
    
    if (!confirm('Reject this submission? This will mark it as rejected and remove it from the review queue.')) {
      return
    }
    
    try {
      setProcessing(id)
      const res = await fetchWithAuth(`/api/submissions/${id}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          comments: reason || 'Rejected by admin',
          action: 'reject'
        })
      })
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ error: 'Failed to reject' }))
        throw new Error(errorData.error || 'Failed to reject submission')
      }
      
      // Remove from list
      setSubmissions(subs => subs.filter(s => s.id !== id))
      setSelected(null)
      alert('✅ Submission rejected and removed from review queue.')
    } catch (err) {
      console.error('Error rejecting submission:', err)
      alert('❌ Error rejecting submission: ' + err.message)
    } finally {
      setProcessing(null)
    }
  }

  return (
    <RoleGate requiredRole="admin">
      {loading && submissions.length === 0 ? (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{
              width: '48px',
              height: '48px',
              border: '4px solid var(--cisa-gray-light)',
              borderTop: '4px solid var(--cisa-blue)',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
              margin: '0 auto'
            }}></div>
            <p style={{ marginTop: 'var(--spacing-md)', color: 'var(--cisa-gray)' }}>Loading submissions...</p>
          </div>
        </div>
      ) : (
      <div style={{ padding: 'var(--spacing-lg)', minHeight: '100vh' }}>
        <div style={{ marginBottom: 'var(--spacing-lg)' }}>
          <h1 style={{ fontSize: 'var(--font-size-xxl)', fontWeight: 700, color: 'var(--cisa-black)', marginBottom: 'var(--spacing-sm)' }}>
            Pending Submissions Review
          </h1>
          <p style={{ color: 'var(--cisa-gray)', fontSize: 'var(--font-size-base)' }}>
            Review and approve/reject user-submitted entries and document-parsed entries. 
            Approved submissions are moved to production tables and feed the learning system.
          </p>
        </div>

        {error && (
          <div style={{
            backgroundColor: 'var(--cisa-red-light)',
            border: '1px solid var(--cisa-red)',
            color: 'var(--cisa-red-dark)',
            padding: 'var(--spacing-md)',
            borderRadius: 'var(--border-radius)',
            marginBottom: 'var(--spacing-md)'
          }}>
            <strong>Error:</strong> {error}
            <button 
              onClick={loadSubmissions}
              style={{ marginLeft: 'var(--spacing-md)', color: 'var(--cisa-red-dark)', textDecoration: 'underline', background: 'none', border: 'none', cursor: 'pointer' }}
            >
              Retry
            </button>
          </div>
        )}

        {/* System Status Banner */}
        <div className="card" style={{ padding: 'var(--spacing-lg)', marginBottom: 'var(--spacing-lg)' }}>
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            marginBottom: 'var(--spacing-md)'
          }}>
            <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 600, color: 'var(--cisa-blue)', margin: 0 }}>
              System Status
            </h2>
            <div style={{ display: 'flex', gap: 'var(--spacing-sm)' }}>
              <button
                onClick={() => controlAction('sync_review')}
                disabled={controlLoading}
                className="btn btn-sm btn-info"
                style={{ opacity: controlLoading ? 0.6 : 1 }}
              >
                🔄 Sync
              </button>
              <button
                onClick={() => controlAction('start_watcher')}
                disabled={controlLoading}
                className="btn btn-sm btn-success"
                style={{ opacity: controlLoading ? 0.6 : 1 }}
              >
                ▶️ Start
              </button>
              <button
                onClick={() => controlAction('stop_watcher')}
                disabled={controlLoading}
                className="btn btn-sm btn-warning"
                style={{ opacity: controlLoading ? 0.6 : 1 }}
              >
                ⏹️ Stop
              </button>
              <button
                onClick={() => {
                  if (confirm('Clear all files from the errors folder?')) {
                    controlAction('clear_errors')
                  }
                }}
                disabled={controlLoading}
                className="btn btn-sm btn-danger"
                style={{ opacity: controlLoading ? 0.6 : 1 }}
              >
                🗑️ Clear Errors
              </button>
            </div>
          </div>
          
          {progress ? (
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
              gap: 'var(--spacing-md)',
              textAlign: 'center'
            }}>
              {Object.entries(progress)
                .filter(([key]) => key !== 'timestamp' && key !== 'status')
                .map(([key, val]) => (
                  <div
                    key={key}
                    style={{
                      textAlign: 'center',
                      padding: 'var(--spacing-sm)',
                      borderRadius: 'var(--border-radius-lg)',
                      backgroundColor: 'var(--cisa-gray-lighter)',
                      border: '1px solid var(--cisa-gray-light)'
                    }}
                  >
                    <p style={{ 
                      fontWeight: 600,
                      textTransform: 'capitalize',
                      marginBottom: 'var(--spacing-sm)',
                      color: 'var(--cisa-gray)',
                      fontSize: 'var(--font-size-sm)'
                    }}>
                      {key.replace('_', ' ')}
                    </p>
                    <div
                      style={{
                        display: 'inline-block',
                        padding: 'var(--spacing-xs) var(--spacing-sm)',
                        borderRadius: '999px',
                        fontWeight: 700,
                        backgroundColor: 'var(--cisa-blue)',
                        color: 'white',
                        fontSize: 'var(--font-size-lg)'
                      }}
                    >
                      {val}
                    </div>
                  </div>
                ))}
            </div>
          ) : (
            <p style={{ color: 'var(--cisa-gray)', textAlign: 'center' }}>Loading system status...</p>
          )}
          
          {progress?.timestamp && (
            <div style={{ marginTop: 'var(--spacing-sm)', fontSize: 'var(--font-size-sm)', color: 'var(--cisa-gray)', textAlign: 'center' }}>
              Last updated: {new Date(progress.timestamp).toLocaleString()}
            </div>
          )}
        </div>

        {/* System Logs (Collapsible) */}
        <div className="card" style={{ padding: 'var(--spacing-lg)', marginBottom: 'var(--spacing-lg)' }}>
          <div 
            style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              cursor: 'pointer'
            }}
            onClick={() => setLogsExpanded(!logsExpanded)}
          >
            <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 600, color: 'var(--cisa-blue)', margin: 0 }}>
              Live Processor Logs
            </h2>
            <button
              onClick={(e) => {
                e.stopPropagation()
                setLogs([])
              }}
              className="btn btn-sm btn-secondary"
            >
              Clear
            </button>
          </div>
          
          {logsExpanded && (
            <div
              style={{
                fontFamily: 'monospace',
                fontSize: 'var(--font-size-sm)',
                overflowY: 'auto',
                padding: 'var(--spacing-sm)',
                borderRadius: 'var(--border-radius)',
                marginTop: 'var(--spacing-sm)',
                backgroundColor: '#1a1a1a',
                color: '#00ff00',
                height: '240px',
                lineHeight: '1.5'
              }}
            >
              {logs.length === 0 ? (
                <div style={{ color: '#888' }}>Waiting for log entries...</div>
              ) : (
                logs.map((line, i) => (
                  <div key={i} style={{ marginBottom: '2px' }}>
                    {line}
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {submissions.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: 'var(--spacing-xxl)' }}>
            <p style={{ color: 'var(--cisa-gray)', fontSize: 'var(--font-size-lg)' }}>🎉 No pending submissions to review</p>
            <p style={{ color: 'var(--cisa-gray-light)', fontSize: 'var(--font-size-sm)', marginTop: 'var(--spacing-sm)' }}>All submissions have been processed</p>
          </div>
        ) : (
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
            gap: 'var(--spacing-md)'
          }}>
            {submissions.map(sub => (
              <div
                key={sub.id}
                className="card"
                onClick={() => setSelected(sub)}
                style={{
                  cursor: 'pointer',
                  transition: 'box-shadow 0.3s ease',
                  border: '1px solid var(--cisa-gray-light)',
                  borderRadius: 'var(--border-radius)',
                  padding: 'var(--spacing-lg)',
                  backgroundColor: 'white'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.boxShadow = 'var(--shadow-md)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--spacing-sm)' }}>
                  <h3 style={{ 
                    fontSize: 'var(--font-size-lg)',
                    fontWeight: 600,
                    color: 'var(--cisa-blue)',
                    margin: 0
                  }}>
                    {sub.document_name}
                  </h3>
                  <span style={{
                    fontSize: 'var(--font-size-xs)',
                    backgroundColor: '#fff3cd',
                    color: '#856404',
                    padding: 'var(--spacing-xs) var(--spacing-sm)',
                    borderRadius: 'var(--border-radius)'
                  }}>
                    Pending
                  </span>
                </div>
                
                <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--cisa-gray)', marginBottom: 'var(--spacing-sm)' }}>
                  {new Date(sub.created_at).toLocaleDateString()} at {new Date(sub.created_at).toLocaleTimeString()}
                </p>
                
                <div style={{ display: 'flex', gap: 'var(--spacing-md)', fontSize: 'var(--font-size-sm)' }}>
                  <div>
                    <span style={{ fontWeight: 600, color: 'var(--cisa-gray)' }}>{sub.vulnerability_count || 0}</span>
                    <span style={{ color: 'var(--cisa-gray-light)', marginLeft: 'var(--spacing-xs)' }}>vulnerabilities</span>
                  </div>
                  <div>
                    <span style={{ fontWeight: 600, color: 'var(--cisa-gray)' }}>{sub.ofc_count || 0}</span>
                    <span style={{ color: 'var(--cisa-gray-light)', marginLeft: 'var(--spacing-xs)' }}>OFCs</span>
                  </div>
                </div>
                
                {sub.source && (
                  <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray-light)', marginTop: 'var(--spacing-sm)' }}>
                    Source: {sub.source}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Submission Detail Dialog */}
        {selected && (
          <div 
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000
            }}
            onClick={() => setSelected(null)}
          >
            <div 
              className="card"
              onClick={(e) => e.stopPropagation()}
              style={{ 
                maxWidth: '56rem',
                width: '100%',
                margin: 'var(--spacing-md)',
                maxHeight: '90vh',
                overflowY: 'auto',
                padding: 'var(--spacing-xl)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-lg)' }}>
                <h2 style={{ fontSize: 'var(--font-size-xxl)', fontWeight: 700, color: 'var(--cisa-black)' }}>{selected.document_name}</h2>
                <button
                  onClick={() => setSelected(null)}
                  style={{ 
                    color: 'var(--cisa-gray)',
                    fontSize: 'var(--font-size-xxl)',
                    fontWeight: 700,
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    lineHeight: 1,
                    padding: 'var(--spacing-xs)'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.color = 'var(--cisa-black)'}
                  onMouseLeave={(e) => e.currentTarget.style.color = 'var(--cisa-gray)'}
                >
                  ×
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
                <div>
                  <strong style={{ color: 'var(--cisa-gray)' }}>Submitted:</strong>{' '}
                  <span style={{ color: 'var(--cisa-gray-light)' }}>
                    {new Date(selected.created_at).toLocaleString()}
                  </span>
                </div>

                {selected.summary && (
                  <div>
                    <strong style={{ color: 'var(--cisa-gray)' }}>Summary:</strong>
                    <p style={{ color: 'var(--cisa-gray-light)', marginTop: 'var(--spacing-xs)' }}>{selected.summary}</p>
                  </div>
                )}

                {selected.source && (
                  <div>
                    <strong style={{ color: 'var(--cisa-gray)' }}>Source:</strong>{' '}
                    <span style={{ color: 'var(--cisa-gray-light)' }}>{selected.source}</span>
                  </div>
                )}

                <div>
                  <strong style={{ color: 'var(--cisa-gray)' }}>Vulnerabilities ({selected.vulnerabilities?.length || 0}):</strong>
                  {selected.vulnerabilities && selected.vulnerabilities.length > 0 ? (
                    <ul style={{ listStyleType: 'disc', paddingLeft: 'var(--spacing-lg)', marginTop: 'var(--spacing-sm)' }}>
                      {selected.vulnerabilities.map((v, i) => (
                        <li key={i} style={{ color: 'var(--cisa-gray)', marginBottom: 'var(--spacing-xs)' }}>
                          {v.vulnerability || v.title || v.description || JSON.stringify(v)}
                          {v.discipline && (
                            <span style={{
                              marginLeft: 'var(--spacing-sm)',
                              fontSize: 'var(--font-size-xs)',
                              backgroundColor: '#cfe2ff',
                              color: '#084298',
                              padding: 'var(--spacing-xs) var(--spacing-sm)',
                              borderRadius: 'var(--border-radius)'
                            }}>
                              {v.discipline}
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p style={{ color: 'var(--cisa-gray-light)', marginTop: 'var(--spacing-xs)' }}>No vulnerabilities found</p>
                  )}
                </div>

                <div>
                  <strong style={{ color: 'var(--cisa-gray)' }}>Options for Consideration ({selected.ofcs?.length || 0}):</strong>
                  {selected.ofcs && selected.ofcs.length > 0 ? (
                    <ul style={{ listStyleType: 'disc', paddingLeft: 'var(--spacing-lg)', marginTop: 'var(--spacing-sm)' }}>
                      {selected.ofcs.map((ofc, i) => (
                        <li key={i} style={{ color: 'var(--cisa-gray)', marginBottom: 'var(--spacing-xs)' }}>
                          {ofc.option_text || ofc.text || ofc.description || JSON.stringify(ofc)}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p style={{ color: 'var(--cisa-gray-light)', marginTop: 'var(--spacing-xs)' }}>No OFCs found</p>
                  )}
                </div>

                <div style={{ display: 'flex', gap: 'var(--spacing-md)', paddingTop: 'var(--spacing-md)', borderTop: '1px solid var(--cisa-gray-light)' }}>
                  <button
                    onClick={() => approveSubmission(selected.id)}
                    disabled={processing === selected.id}
                    className="btn btn-primary"
                    style={{
                      backgroundColor: 'var(--cisa-success)',
                      color: 'white',
                      padding: 'var(--spacing-sm) var(--spacing-lg)',
                      borderRadius: 'var(--border-radius)',
                      border: 'none',
                      cursor: processing === selected.id ? 'not-allowed' : 'pointer',
                      opacity: processing === selected.id ? 0.6 : 1
                    }}
                  >
                    {processing === selected.id ? 'Processing...' : '✅ Approve & Publish'}
                  </button>
                  <button
                    onClick={() => rejectSubmission(selected.id)}
                    disabled={processing === selected.id}
                    className="btn"
                    style={{
                      backgroundColor: '#dc3545',
                      color: 'white',
                      padding: 'var(--spacing-sm) var(--spacing-lg)',
                      borderRadius: 'var(--border-radius)',
                      border: 'none',
                      cursor: processing === selected.id ? 'not-allowed' : 'pointer',
                      opacity: processing === selected.id ? 0.6 : 1
                    }}
                  >
                    {processing === selected.id ? 'Processing...' : '❌ Reject'}
                  </button>
                  <button
                    onClick={() => setSelected(null)}
                    className="btn btn-secondary"
                    style={{
                      padding: 'var(--spacing-sm) var(--spacing-lg)',
                      borderRadius: 'var(--border-radius)'
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
      )}
    </RoleGate>
  )
}
