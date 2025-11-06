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

  useEffect(() => {
    loadSubmissions()
    const interval = setInterval(loadSubmissions, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [])

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
