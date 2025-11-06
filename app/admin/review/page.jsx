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
      
      const data = await res.json()
      if (res.ok) {
        alert(`✅ ${data.message || 'Action completed'}`)
        // Refresh progress after action
        const progressRes = await fetch('/api/system/progress', { cache: 'no-store' })
        if (progressRes.ok) {
          const progressData = await progressRes.json()
          setProgress(progressData)
        }
      } else {
        alert(`❌ Error: ${data.message || 'Action failed'}`)
      }
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

  if (loading && submissions.length === 0) {
    return (
      <RoleGate requiredRole="admin">
        <div className="flex justify-center items-center h-full min-h-screen">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading submissions...</p>
          </div>
        </div>
      </RoleGate>
    )
  }

  return (
    <RoleGate requiredRole="admin">
      <div className="p-6 space-y-4" style={{ minHeight: '100vh' }}>
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Pending Submissions Review</h1>
          <p className="text-gray-600">
            Review and approve/reject user-submitted entries and document-parsed entries. 
            Approved submissions are moved to production tables and feed the learning system.
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            <strong>Error:</strong> {error}
            <button 
              onClick={loadSubmissions}
              className="ml-4 text-red-800 underline"
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
            <h2 className="text-xl font-semibold text-gray-900" style={{ color: 'var(--cisa-blue)', margin: 0 }}>
              System Status
            </h2>
            <div style={{ display: 'flex', gap: 'var(--spacing-sm)' }}>
              <button
                onClick={() => controlAction('sync_review')}
                disabled={controlLoading}
                className="btn btn-sm"
                style={{
                  padding: 'var(--spacing-xs) var(--spacing-sm)',
                  fontSize: 'var(--font-size-sm)',
                  opacity: controlLoading ? 0.6 : 1
                }}
              >
                🔄 Sync
              </button>
              <button
                onClick={() => controlAction('start_watcher')}
                disabled={controlLoading}
                className="btn btn-sm"
                style={{
                  padding: 'var(--spacing-xs) var(--spacing-sm)',
                  fontSize: 'var(--font-size-sm)',
                  opacity: controlLoading ? 0.6 : 1
                }}
              >
                ▶️ Start
              </button>
              <button
                onClick={() => controlAction('stop_watcher')}
                disabled={controlLoading}
                className="btn btn-sm"
                style={{
                  padding: 'var(--spacing-xs) var(--spacing-sm)',
                  fontSize: 'var(--font-size-sm)',
                  opacity: controlLoading ? 0.6 : 1
                }}
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
                className="btn btn-sm"
                style={{
                  padding: 'var(--spacing-xs) var(--spacing-sm)',
                  fontSize: 'var(--font-size-sm)',
                  backgroundColor: '#dc3545',
                  color: 'white',
                  border: 'none',
                  opacity: controlLoading ? 0.6 : 1
                }}
              >
                🗑️ Clear Errors
              </button>
            </div>
          </div>
          
          {progress ? (
            <div className="grid md:grid-cols-5 gap-4 text-center">
              {Object.entries(progress)
                .filter(([key]) => key !== 'timestamp' && key !== 'status')
                .map(([key, val]) => (
                  <div
                    key={key}
                    className="text-center p-3 rounded-lg"
                    style={{
                      backgroundColor: 'var(--cisa-gray-lighter)',
                      border: '1px solid var(--cisa-gray-light)'
                    }}
                  >
                    <p className="font-semibold capitalize mb-2" style={{ 
                      color: 'var(--cisa-gray)',
                      fontSize: 'var(--font-size-sm)'
                    }}>
                      {key.replace('_', ' ')}
                    </p>
                    <div
                      className="inline-block px-3 py-1 rounded-full font-bold"
                      style={{
                        backgroundColor: 'var(--cisa-blue)',
                        color: 'white',
                        fontSize: 'var(--font-size-lg)'
                      }}
                    >
                      {val as number}
                    </div>
                  </div>
                ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center">Loading system status...</p>
          )}
          
          {progress?.timestamp && (
            <div className="mt-3 text-sm text-gray-500 text-center">
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
            <h2 className="text-xl font-semibold text-gray-900" style={{ color: 'var(--cisa-blue)', margin: 0 }}>
              Live Processor Logs
            </h2>
            <button
              onClick={(e) => {
                e.stopPropagation()
                setLogs([])
              }}
              className="btn btn-sm"
              style={{
                padding: 'var(--spacing-xs) var(--spacing-sm)',
                fontSize: 'var(--font-size-sm)'
              }}
            >
              Clear
            </button>
          </div>
          
          {logsExpanded && (
            <div
              className="font-mono text-sm overflow-y-auto p-3 rounded mt-3"
              style={{
                backgroundColor: '#1a1a1a',
                color: '#00ff00',
                height: '240px',
                fontFamily: 'monospace',
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
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <p className="text-gray-500 text-lg">🎉 No pending submissions to review</p>
            <p className="text-gray-400 text-sm mt-2">All submissions have been processed</p>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {submissions.map(sub => (
              <div
                key={sub.id}
                className="card cursor-pointer hover:shadow-lg transition-shadow"
                onClick={() => setSelected(sub)}
                style={{
                  border: '1px solid var(--cisa-gray-light)',
                  borderRadius: 'var(--border-radius)',
                  padding: 'var(--spacing-lg)',
                  backgroundColor: 'white'
                }}
              >
                <div className="flex justify-between items-start mb-3">
                  <h3 className="text-lg font-semibold text-gray-900" style={{ 
                    color: 'var(--cisa-blue)',
                    margin: 0
                  }}>
                    {sub.document_name}
                  </h3>
                  <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
                    Pending
                  </span>
                </div>
                
                <p className="text-sm text-gray-500 mb-3">
                  {new Date(sub.created_at).toLocaleDateString()} at {new Date(sub.created_at).toLocaleTimeString()}
                </p>
                
                <div className="flex gap-4 text-sm">
                  <div>
                    <span className="font-semibold text-gray-700">{sub.vulnerability_count || 0}</span>
                    <span className="text-gray-500 ml-1">vulnerabilities</span>
                  </div>
                  <div>
                    <span className="font-semibold text-gray-700">{sub.ofc_count || 0}</span>
                    <span className="text-gray-500 ml-1">OFCs</span>
                  </div>
                </div>
                
                {sub.source && (
                  <p className="text-xs text-gray-400 mt-2">
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
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
            onClick={() => setSelected(null)}
          >
            <div 
              className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
              style={{ padding: 'var(--spacing-xl)' }}
            >
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-gray-900">{selected.document_name}</h2>
                <button
                  onClick={() => setSelected(null)}
                  className="text-gray-500 hover:text-gray-700 text-3xl font-bold"
                  style={{ lineHeight: 1 }}
                >
                  ×
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <strong className="text-gray-700">Submitted:</strong>{' '}
                  <span className="text-gray-600">
                    {new Date(selected.created_at).toLocaleString()}
                  </span>
                </div>

                {selected.summary && (
                  <div>
                    <strong className="text-gray-700">Summary:</strong>
                    <p className="text-gray-600 mt-1">{selected.summary}</p>
                  </div>
                )}

                {selected.source && (
                  <div>
                    <strong className="text-gray-700">Source:</strong>{' '}
                    <span className="text-gray-600">{selected.source}</span>
                  </div>
                )}

                <div>
                  <strong className="text-gray-700">Vulnerabilities ({selected.vulnerabilities?.length || 0}):</strong>
                  {selected.vulnerabilities && selected.vulnerabilities.length > 0 ? (
                    <ul className="list-disc pl-5 mt-2 space-y-2">
                      {selected.vulnerabilities.map((v, i) => (
                        <li key={i} className="text-gray-700">
                          {v.vulnerability || v.title || v.description || JSON.stringify(v)}
                          {v.discipline && (
                            <span className="ml-2 text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                              {v.discipline}
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-gray-500 mt-1">No vulnerabilities found</p>
                  )}
                </div>

                <div>
                  <strong className="text-gray-700">Options for Consideration ({selected.ofcs?.length || 0}):</strong>
                  {selected.ofcs && selected.ofcs.length > 0 ? (
                    <ul className="list-disc pl-5 mt-2 space-y-2">
                      {selected.ofcs.map((ofc, i) => (
                        <li key={i} className="text-gray-700">
                          {ofc.option_text || ofc.text || ofc.description || JSON.stringify(ofc)}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-gray-500 mt-1">No OFCs found</p>
                  )}
                </div>

                <div className="flex gap-4 pt-4 border-t">
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
    </RoleGate>
  )
}
