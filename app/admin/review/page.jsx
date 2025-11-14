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
  
  // Editing state
  const [editingVuln, setEditingVuln] = useState(null)
  const [editingOfc, setEditingOfc] = useState(null)
  const [editValues, setEditValues] = useState({})
  
  // System monitoring state
  const [progress, setProgress] = useState(null)
  const [logs, setLogs] = useState([])
  const [logsExpanded, setLogsExpanded] = useState(false)
  const [controlLoading, setControlLoading] = useState(false)

  useEffect(() => {
    // RoleGate ensures user is authenticated before rendering
    // So we can directly load submissions
    let isMounted = true
    let pollInterval = null
    
    const loadSubmissionsSafe = async () => {
      if (!isMounted) return
      await loadSubmissions()
    }
    
    loadSubmissionsSafe()
    
    // Note: Auto-sync removed - now handled by VOFC-Processor service
    
    // Set up polling - RoleGate ensures user is authenticated
    pollInterval = setInterval(() => {
      if (isMounted) {
        loadSubmissionsSafe()
      }
    }, 60000) // Refresh every 60s (reduced from 30s to reduce network load)
    
    return () => {
      isMounted = false
      if (pollInterval) clearInterval(pollInterval)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      
      // Note: Sync actions removed - now handled by VOFC-Processor service
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

  async function updateVulnerability(vulnId, updates) {
    try {
      const res = await fetchWithAuth(`/api/submissions/${selected.id}/vulnerabilities/${vulnId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      })
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ error: 'Failed to update' }))
        throw new Error(errorData.error || 'Failed to update vulnerability')
      }
      
      // Reload submission to get updated data
      await loadSubmissions()
      // Re-select the submission to show updated data
      const updated = submissions.find(s => s.id === selected.id)
      if (updated) {
        // Reload the selected submission with fresh data
        const res = await fetchWithAuth(`/api/admin/submissions?status=pending_review`, { 
          cache: 'no-store' 
        })
        if (res.ok) {
          const data = await res.json()
          const subs = data.allSubmissions || data.submissions || []
          const freshSub = subs.find(s => s.id === selected.id)
          if (freshSub) setSelected(freshSub)
        }
      }
      
      setEditingVuln(null)
      setEditValues({})
      alert('✅ Vulnerability updated successfully')
    } catch (err) {
      console.error('Error updating vulnerability:', err)
      alert('❌ Error updating vulnerability: ' + err.message)
    }
  }

  async function updateOFC(ofcId, updates) {
    try {
      const res = await fetchWithAuth(`/api/submissions/${selected.id}/ofcs/${ofcId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      })
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ error: 'Failed to update' }))
        throw new Error(errorData.error || 'Failed to update OFC')
      }
      
      // Reload submission to get updated data
      await loadSubmissions()
      // Re-select the submission to show updated data
      const res2 = await fetchWithAuth(`/api/admin/submissions?status=pending_review`, { 
        cache: 'no-store' 
      })
      if (res2.ok) {
        const data = await res2.json()
        const subs = data.allSubmissions || data.submissions || []
        const freshSub = subs.find(s => s.id === selected.id)
        if (freshSub) setSelected(freshSub)
      }
      
      setEditingOfc(null)
      setEditValues({})
      alert('✅ OFC updated successfully')
    } catch (err) {
      console.error('Error updating OFC:', err)
      alert('❌ Error updating OFC: ' + err.message)
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
                  {new Date(sub.created_at).toLocaleDateString('en-US', { timeZone: 'America/New_York' })} at {new Date(sub.created_at).toLocaleTimeString('en-US', { timeZone: 'America/New_York', timeZoneName: 'short' })}
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
                    {new Date(selected.created_at).toLocaleString('en-US', { timeZone: 'America/New_York', timeZoneName: 'short' })}
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
                          border: '1px solid var(--cisa-gray-light)',
                          position: 'relative'
                        }}>
                          {editingVuln === v.id ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' }}>
                              <div>
                                <label style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', display: 'block', marginBottom: 'var(--spacing-xs)' }}>
                                  Vulnerability Name:
                                </label>
                                <textarea
                                  value={editValues.vulnerability_name || v.vulnerability_name || v.vulnerability || ''}
                                  onChange={(e) => setEditValues({...editValues, vulnerability_name: e.target.value})}
                                  style={{
                                    width: '100%',
                                    padding: 'var(--spacing-xs)',
                                    border: '1px solid var(--cisa-gray-light)',
                                    borderRadius: 'var(--border-radius)',
                                    fontSize: 'var(--font-size-sm)',
                                    minHeight: '60px',
                                    fontFamily: 'inherit'
                                  }}
                                />
                              </div>
                              {v.description !== undefined && (
                                <div>
                                  <label style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', display: 'block', marginBottom: 'var(--spacing-xs)' }}>
                                    Description:
                                  </label>
                                  <textarea
                                    value={editValues.description !== undefined ? editValues.description : (v.description || '')}
                                    onChange={(e) => setEditValues({...editValues, description: e.target.value})}
                                    style={{
                                      width: '100%',
                                      padding: 'var(--spacing-xs)',
                                      border: '1px solid var(--cisa-gray-light)',
                                      borderRadius: 'var(--border-radius)',
                                      fontSize: 'var(--font-size-sm)',
                                      minHeight: '80px',
                                      fontFamily: 'inherit'
                                    }}
                                  />
                                </div>
                              )}
                              <div style={{ display: 'flex', gap: 'var(--spacing-sm)' }}>
                                <input
                                  type="text"
                                  placeholder="Discipline"
                                  value={editValues.discipline !== undefined ? editValues.discipline : (v.discipline || '')}
                                  onChange={(e) => setEditValues({...editValues, discipline: e.target.value})}
                                  style={{
                                    flex: 1,
                                    padding: 'var(--spacing-xs)',
                                    border: '1px solid var(--cisa-gray-light)',
                                    borderRadius: 'var(--border-radius)',
                                    fontSize: 'var(--font-size-sm)'
                                  }}
                                />
                                <input
                                  type="text"
                                  placeholder="Sector"
                                  value={editValues.sector !== undefined ? editValues.sector : (v.sector || '')}
                                  onChange={(e) => setEditValues({...editValues, sector: e.target.value})}
                                  style={{
                                    flex: 1,
                                    padding: 'var(--spacing-xs)',
                                    border: '1px solid var(--cisa-gray-light)',
                                    borderRadius: 'var(--border-radius)',
                                    fontSize: 'var(--font-size-sm)'
                                  }}
                                />
                              </div>
                              <div style={{ display: 'flex', gap: 'var(--spacing-sm)', justifyContent: 'flex-end' }}>
                                <button
                                  onClick={() => {
                                    setEditingVuln(null)
                                    setEditValues({})
                                  }}
                                  style={{
                                    padding: 'var(--spacing-xs) var(--spacing-sm)',
                                    border: '1px solid var(--cisa-gray-light)',
                                    borderRadius: 'var(--border-radius)',
                                    background: 'white',
                                    cursor: 'pointer',
                                    fontSize: 'var(--font-size-sm)'
                                  }}
                                >
                                  Cancel
                                </button>
                                <button
                                  onClick={() => updateVulnerability(v.id, editValues)}
                                  style={{
                                    padding: 'var(--spacing-xs) var(--spacing-sm)',
                                    border: 'none',
                                    borderRadius: 'var(--border-radius)',
                                    background: 'var(--cisa-blue)',
                                    color: 'white',
                                    cursor: 'pointer',
                                    fontSize: 'var(--font-size-sm)'
                                  }}
                                >
                                  Save
                                </button>
                              </div>
                            </div>
                          ) : (
                            <>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--spacing-xs)' }}>
                                <p style={{ color: 'var(--cisa-gray)', margin: 0, flex: 1 }}>
                                  {v.vulnerability_name || v.vulnerability}
                                </p>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    setEditingVuln(v.id)
                                    setEditValues({
                                      vulnerability_name: v.vulnerability_name || v.vulnerability || '',
                                      description: v.description || '',
                                      discipline: v.discipline || '',
                                      sector: v.sector || '',
                                      subsector: v.subsector || '',
                                      severity_level: v.severity_level || ''
                                    })
                                  }}
                                  style={{
                                    padding: 'var(--spacing-xs) var(--spacing-sm)',
                                    border: '1px solid var(--cisa-gray-light)',
                                    borderRadius: 'var(--border-radius)',
                                    background: 'white',
                                    cursor: 'pointer',
                                    fontSize: 'var(--font-size-xs)',
                                    marginLeft: 'var(--spacing-sm)'
                                  }}
                                  title="Edit vulnerability"
                                >
                                  ✏️ Edit
                                </button>
                              </div>
                              {v.description && (
                                <p style={{ color: 'var(--cisa-gray-light)', fontSize: 'var(--font-size-sm)', marginTop: 'var(--spacing-xs)', marginBottom: 'var(--spacing-xs)' }}>
                                  {v.description}
                                </p>
                              )}
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
                                {v.severity_level && (
                                  <span style={{
                                    fontSize: 'var(--font-size-xs)',
                                    backgroundColor: '#f8d7da',
                                    color: '#721c24',
                                    padding: 'var(--spacing-xs) var(--spacing-sm)',
                                    borderRadius: 'var(--border-radius)'
                                  }}>
                                    {v.severity_level}
                                  </span>
                                )}
                              </div>
                            </>
                          )}
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
                          border: '1px solid var(--cisa-gray-light)',
                          position: 'relative'
                        }}>
                          {editingOfc === ofc.id ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' }}>
                              <div>
                                <label style={{ fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)', display: 'block', marginBottom: 'var(--spacing-xs)' }}>
                                  Option Text:
                                </label>
                                <textarea
                                  value={editValues.option_text !== undefined ? editValues.option_text : (ofc.option_text || '')}
                                  onChange={(e) => setEditValues({...editValues, option_text: e.target.value})}
                                  style={{
                                    width: '100%',
                                    padding: 'var(--spacing-xs)',
                                    border: '1px solid var(--cisa-gray-light)',
                                    borderRadius: 'var(--border-radius)',
                                    fontSize: 'var(--font-size-sm)',
                                    minHeight: '80px',
                                    fontFamily: 'inherit'
                                  }}
                                />
                              </div>
                              <div style={{ display: 'flex', gap: 'var(--spacing-sm)' }}>
                                <input
                                  type="text"
                                  placeholder="Discipline"
                                  value={editValues.discipline !== undefined ? editValues.discipline : (ofc.discipline || '')}
                                  onChange={(e) => setEditValues({...editValues, discipline: e.target.value})}
                                  style={{
                                    flex: 1,
                                    padding: 'var(--spacing-xs)',
                                    border: '1px solid var(--cisa-gray-light)',
                                    borderRadius: 'var(--border-radius)',
                                    fontSize: 'var(--font-size-sm)'
                                  }}
                                />
                                <input
                                  type="text"
                                  placeholder="Sector"
                                  value={editValues.sector !== undefined ? editValues.sector : (ofc.sector || '')}
                                  onChange={(e) => setEditValues({...editValues, sector: e.target.value})}
                                  style={{
                                    flex: 1,
                                    padding: 'var(--spacing-xs)',
                                    border: '1px solid var(--cisa-gray-light)',
                                    borderRadius: 'var(--border-radius)',
                                    fontSize: 'var(--font-size-sm)'
                                  }}
                                />
                              </div>
                              <div style={{ display: 'flex', gap: 'var(--spacing-sm)', justifyContent: 'flex-end' }}>
                                <button
                                  onClick={() => {
                                    setEditingOfc(null)
                                    setEditValues({})
                                  }}
                                  style={{
                                    padding: 'var(--spacing-xs) var(--spacing-sm)',
                                    border: '1px solid var(--cisa-gray-light)',
                                    borderRadius: 'var(--border-radius)',
                                    background: 'white',
                                    cursor: 'pointer',
                                    fontSize: 'var(--font-size-sm)'
                                  }}
                                >
                                  Cancel
                                </button>
                                <button
                                  onClick={() => updateOFC(ofc.id, editValues)}
                                  style={{
                                    padding: 'var(--spacing-xs) var(--spacing-sm)',
                                    border: 'none',
                                    borderRadius: 'var(--border-radius)',
                                    background: 'var(--cisa-blue)',
                                    color: 'white',
                                    cursor: 'pointer',
                                    fontSize: 'var(--font-size-sm)'
                                  }}
                                >
                                  Save
                                </button>
                              </div>
                            </div>
                          ) : (
                            <>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--spacing-xs)' }}>
                                <p style={{ color: 'var(--cisa-gray)', margin: 0, flex: 1 }}>
                                  {ofc.option_text}
                                </p>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    setEditingOfc(ofc.id)
                                    setEditValues({
                                      option_text: ofc.option_text || '',
                                      discipline: ofc.discipline || '',
                                      sector: ofc.sector || '',
                                      subsector: ofc.subsector || '',
                                      confidence_score: ofc.confidence_score || 0
                                    })
                                  }}
                                  style={{
                                    padding: 'var(--spacing-xs) var(--spacing-sm)',
                                    border: '1px solid var(--cisa-gray-light)',
                                    borderRadius: 'var(--border-radius)',
                                    background: 'white',
                                    cursor: 'pointer',
                                    fontSize: 'var(--font-size-xs)',
                                    marginLeft: 'var(--spacing-sm)'
                                  }}
                                  title="Edit OFC"
                                >
                                  ✏️ Edit
                                </button>
                              </div>
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
                            </>
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
