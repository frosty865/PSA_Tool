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
    // RoleGate ensures user is authenticated before rendering
    // So we can directly load submissions
    loadSubmissions()
    
    // Auto-sync review files to submissions if there are files but no submissions
    const autoSync = async () => {
      try {
        const progressRes = await fetch('/api/system/progress', { cache: 'no-store' })
        if (progressRes.ok) {
          const progressData = await progressRes.json()
          // If there are review files, check if we need to sync
          if (progressData.review > 0) {
            // Try to sync after a short delay to let submissions load first
            setTimeout(async () => {
              const subsRes = await fetchWithAuth('/api/admin/submissions?status=pending_review', { 
                cache: 'no-store' 
              })
              if (subsRes.ok) {
                const subsData = await subsRes.json()
                const subs = subsData.allSubmissions || subsData.submissions || []
                // If there are review files but no submissions, auto-sync
                if (subs.length === 0 && progressData.review > 0) {
                  console.log('Auto-syncing review files to submissions...')
                  try {
                    const syncRes = await fetch('/api/system/control', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      credentials: 'include',
                      body: JSON.stringify({ action: 'sync_review_to_submissions' })
                    })
                    if (syncRes.ok) {
                      console.log('Auto-sync completed')
                      // Reload submissions after sync
                      setTimeout(loadSubmissions, 2000)
                    }
                  } catch (syncErr) {
                    console.error('Auto-sync error:', syncErr)
                  }
                }
              }
            }, 2000)
          }
        }
      } catch (err) {
        console.error('Error in auto-sync check:', err)
      }
    }
    
    autoSync()
    
    // Set up polling - RoleGate ensures user is authenticated
    const pollInterval = setInterval(() => {
      loadSubmissions()
    }, 30000) // Refresh every 30s
    
    return () => {
      if (pollInterval) clearInterval(pollInterval)
    }
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
      
      // Reload submissions if syncing
      if (action === 'sync_review_to_submissions') {
        setTimeout(loadSubmissions, 1000)
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
        // If 401, don't throw - let fetchWithAuth handle redirect
        if (res.status === 401 || res.status === 403) {
          console.warn('Authentication failed, redirecting to login...')
          return // fetchWithAuth will handle redirect
        }
        throw new Error(`Failed to load submissions: ${res.status}`)
      }
      
      const data = await res.json()
      const subs = data.allSubmissions || data.submissions || []
      
      setSubmissions(subs)
    } catch (err) {
      console.error('Error loading submissions:', err)
      // Don't set error for auth failures - redirect is handled
      if (!err.message.includes('401') && !err.message.includes('403')) {
        setError(err.message)
      }
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

  // Extract summary from data JSONB
  function getSummary(submission) {
    try {
      const data = typeof submission.data === 'string' ? JSON.parse(submission.data) : submission.data
      return data?.summary || data?.description || null
    } catch (e) {
      return null
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
            Review and approve/reject document-parsed entries. Approved submissions are moved to production tables.
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
                onClick={() => controlAction('sync_review_to_submissions')}
                disabled={controlLoading}
                className="btn btn-sm btn-primary"
                style={{ opacity: controlLoading ? 0.6 : 1 }}
                title="Sync review files to submissions table"
              >
                📤 Sync to Submissions
              </button>
              <button
                onClick={() => controlAction('sync_review')}
                disabled={controlLoading}
                className="btn btn-sm btn-info"
                style={{ opacity: controlLoading ? 0.6 : 1 }}
                title="Sync approved files to production"
              >
                🔄 Sync Approved
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
                    {sub.document_name || sub.source_file || `Submission ${sub.id.slice(0, 8)}`}
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
                <h2 style={{ fontSize: 'var(--font-size-xxl)', fontWeight: 700, color: 'var(--cisa-black)' }}>
                  {selected.document_name || selected.source_file || `Submission ${selected.id.slice(0, 8)}`}
                </h2>
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

                {getSummary(selected) && (
                  <div>
                    <strong style={{ color: 'var(--cisa-gray)' }}>Summary:</strong>
                    <p style={{ color: 'var(--cisa-gray-light)', marginTop: 'var(--spacing-xs)' }}>{getSummary(selected)}</p>
                  </div>
                )}

                {selected.source && (
                  <div>
                    <strong style={{ color: 'var(--cisa-gray)' }}>Source:</strong>{' '}
                    <span style={{ color: 'var(--cisa-gray-light)' }}>{selected.source}</span>
                  </div>
                )}

                <div>
                  <strong style={{ color: 'var(--cisa-gray)' }}>Vulnerabilities ({selected.vulnerability_count || selected.submission_vulnerabilities?.length || 0}):</strong>
                  {selected.submission_vulnerabilities && selected.submission_vulnerabilities.length > 0 ? (
                    <div style={{ marginTop: 'var(--spacing-sm)' }}>
                      {selected.submission_vulnerabilities.map((v, i) => (
                        <div key={v.id || i} style={{ 
                          padding: 'var(--spacing-sm)',
                          marginBottom: 'var(--spacing-sm)',
                          backgroundColor: 'var(--cisa-gray-lighter)',
                          borderRadius: 'var(--border-radius)',
                          border: '1px solid var(--cisa-gray-light)'
                        }}>
                          <p style={{ color: 'var(--cisa-gray)', marginBottom: 'var(--spacing-xs)' }}>
                            {v.vulnerability}
                          </p>
                          <div style={{ display: 'flex', gap: 'var(--spacing-sm)', flexWrap: 'wrap' }}>
                            {v.discipline && (
                              <span style={{
                                fontSize: 'var(--font-size-xs)',
                                backgroundColor: '#cfe2ff',
                                color: '#084298',
                                padding: 'var(--spacing-xs) var(--spacing-sm)',
                                borderRadius: 'var(--border-radius)'
                              }}>
                                {v.discipline}
                              </span>
                            )}
                            {v.sector && (
                              <span style={{
                                fontSize: 'var(--font-size-xs)',
                                backgroundColor: '#d1e7dd',
                                color: '#0f5132',
                                padding: 'var(--spacing-xs) var(--spacing-sm)',
                                borderRadius: 'var(--border-radius)'
                              }}>
                                {v.sector}
                              </span>
                            )}
                            {v.subsector && (
                              <span style={{
                                fontSize: 'var(--font-size-xs)',
                                backgroundColor: '#fff3cd',
                                color: '#856404',
                                padding: 'var(--spacing-xs) var(--spacing-sm)',
                                borderRadius: 'var(--border-radius)'
                              }}>
                                {v.subsector}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{ color: 'var(--cisa-gray-light)', marginTop: 'var(--spacing-xs)' }}>No vulnerabilities found</p>
                  )}
                </div>

                <div>
                  <strong style={{ color: 'var(--cisa-gray)' }}>Options for Consideration ({selected.ofc_count || selected.submission_options_for_consideration?.length || 0}):</strong>
                  {selected.submission_options_for_consideration && selected.submission_options_for_consideration.length > 0 ? (
                    <div style={{ marginTop: 'var(--spacing-sm)' }}>
                      {selected.submission_options_for_consideration.map((ofc, i) => (
                        <div key={ofc.id || i} style={{ 
                          padding: 'var(--spacing-sm)',
                          marginBottom: 'var(--spacing-sm)',
                          backgroundColor: 'var(--cisa-gray-lighter)',
                          borderRadius: 'var(--border-radius)',
                          border: '1px solid var(--cisa-gray-light)'
                        }}>
                          <p style={{ color: 'var(--cisa-gray)', marginBottom: 'var(--spacing-xs)' }}>
                            {ofc.option_text}
                          </p>
                          <div style={{ display: 'flex', gap: 'var(--spacing-sm)', flexWrap: 'wrap', alignItems: 'center' }}>
                            {ofc.discipline && (
                              <span style={{
                                fontSize: 'var(--font-size-xs)',
                                backgroundColor: '#cfe2ff',
                                color: '#084298',
                                padding: 'var(--spacing-xs) var(--spacing-sm)',
                                borderRadius: 'var(--border-radius)'
                              }}>
                                {ofc.discipline}
                              </span>
                            )}
                            {ofc.confidence_score && (
                              <span style={{
                                fontSize: 'var(--font-size-xs)',
                                backgroundColor: '#f8d7da',
                                color: '#721c24',
                                padding: 'var(--spacing-xs) var(--spacing-sm)',
                                borderRadius: 'var(--border-radius)'
                              }}>
                                Confidence: {(ofc.confidence_score * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>
                          {ofc.sources && Array.isArray(ofc.sources) && ofc.sources.length > 0 && (
                            <div style={{ marginTop: 'var(--spacing-xs)' }}>
                              <strong style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)' }}>Sources:</strong>
                              <div style={{ marginTop: 'var(--spacing-xs)' }}>
                                {ofc.sources.map((source, idx) => (
                                  <div key={idx} style={{
                                    fontSize: 'var(--font-size-xs)',
                                    color: 'var(--cisa-gray-light)',
                                    marginBottom: 'var(--spacing-xs)'
                                  }}>
                                    {source.source_title || source.source_text || 'Source'}
                                    {source.source_url && (
                                      <a 
                                        href={source.source_url} 
                                        target="_blank" 
                                        rel="noopener noreferrer"
                                        style={{ marginLeft: 'var(--spacing-xs)', color: 'var(--cisa-blue)' }}
                                      >
                                        (link)
                                      </a>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
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
