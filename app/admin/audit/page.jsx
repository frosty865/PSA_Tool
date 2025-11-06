'use client'

import { useEffect, useState } from 'react'
import { fetchWithAuth } from '../../lib/fetchWithAuth'
import RoleGate from '@/components/RoleGate'
import '@/styles/cisa.css'

export default function AuditLogPage() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all') // 'all', 'approved', 'rejected', 'edited'

  useEffect(() => {
    loadAuditLogs()
    const interval = setInterval(loadAuditLogs, 60000) // Refresh every minute
    return () => clearInterval(interval)
  }, [filter])

  async function loadAuditLogs() {
    try {
      setLoading(true)
      setError(null)
      
      const url = filter !== 'all' 
        ? `/api/admin/audit?action=${filter}&limit=200`
        : '/api/admin/audit?limit=200'
      
      const res = await fetchWithAuth(url, { cache: 'no-store' })
      
      if (!res.ok) {
        throw new Error(`Failed to load audit logs: ${res.status}`)
      }
      
      const data = await res.json()
      setLogs(data.logs || [])
      
      if (data.warning) {
        console.warn('[Audit Log]', data.warning)
      }
    } catch (err) {
      console.error('Error loading audit logs:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const getActionBadgeColor = (action) => {
    switch (action) {
      case 'approved':
        return { bg: '#e6f6ea', border: '#00a651', text: '#007a3d' }
      case 'rejected':
        return { bg: '#fdecea', border: '#c00', text: '#a00' }
      case 'edited':
        return { bg: '#fff9e6', border: '#ffc107', text: '#856404' }
      default:
        return { bg: '#f5f5f5', border: '#ccc', text: '#666' }
    }
  }

  const getActionLabel = (action) => {
    switch (action) {
      case 'approved':
        return '✅ Approved'
      case 'rejected':
        return '❌ Rejected'
      case 'edited':
        return '✏️ Edited'
      default:
        return action
    }
  }

  if (loading && logs.length === 0) {
    return (
      <RoleGate requiredRole="admin">
        <div className="flex justify-center items-center h-full min-h-screen">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading audit log...</p>
          </div>
        </div>
      </RoleGate>
    )
  }

  return (
    <RoleGate requiredRole="admin">
      <div className="p-6 space-y-4" style={{ minHeight: '100vh' }}>
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Review Audit Trail</h1>
          <p className="text-gray-600">
            Track all admin review actions including approvals, rejections, and edits.
            Each entry links to the affected submission and production records.
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            <strong>Error:</strong> {error}
            <button 
              onClick={loadAuditLogs}
              className="ml-4 text-red-800 underline"
            >
              Retry
            </button>
          </div>
        )}

        {/* Filter Buttons */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setFilter('all')}
            className={`px-4 py-2 rounded ${filter === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            All Actions
          </button>
          <button
            onClick={() => setFilter('approved')}
            className={`px-4 py-2 rounded ${filter === 'approved' ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            Approved
          </button>
          <button
            onClick={() => setFilter('rejected')}
            className={`px-4 py-2 rounded ${filter === 'rejected' ? 'bg-red-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            Rejected
          </button>
          <button
            onClick={() => setFilter('edited')}
            className={`px-4 py-2 rounded ${filter === 'edited' ? 'bg-yellow-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            Edited
          </button>
        </div>

        {logs.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <p className="text-gray-500 text-lg">
              {error ? 'Unable to load audit logs' : 'No audit log entries found'}
            </p>
            {error && (
              <p className="text-gray-400 text-sm mt-2">
                The audit_log table may not exist. Please create it in Supabase.
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {logs.map(log => {
              const colors = getActionBadgeColor(log.action)
              return (
                <div
                  key={log.id}
                  className="card"
                  style={{
                    border: `1px solid ${colors.border}`,
                    borderRadius: 'var(--border-radius)',
                    padding: 'var(--spacing-lg)',
                    backgroundColor: colors.bg
                  }}
                >
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center gap-3">
                      <span
                        className="px-3 py-1 rounded text-sm font-semibold"
                        style={{
                          backgroundColor: colors.border,
                          color: 'white'
                        }}
                      >
                        {getActionLabel(log.action)}
                      </span>
                      <span className="text-sm text-gray-500">
                        {new Date(log.timestamp).toLocaleString()}
                      </span>
                    </div>
                  </div>

                  <div className="space-y-2 text-sm">
                    <div>
                      <strong className="text-gray-700">Reviewer:</strong>{' '}
                      <span className="text-gray-600 font-mono text-xs">
                        {log.reviewer_id || 'System'}
                      </span>
                    </div>
                    
                    <div>
                      <strong className="text-gray-700">Submission:</strong>{' '}
                      <span className="text-gray-600 font-mono text-xs">
                        {log.submission_id}
                      </span>
                    </div>

                    {log.notes && (
                      <div>
                        <strong className="text-gray-700">Notes:</strong>
                        <p className="text-gray-600 mt-1">{log.notes}</p>
                      </div>
                    )}

                    {log.affected_vuln_ids && log.affected_vuln_ids.length > 0 && (
                      <div>
                        <strong className="text-gray-700">Vulnerabilities ({log.affected_vuln_ids.length}):</strong>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {log.affected_vuln_ids.map((vulnId, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-mono"
                            >
                              {vulnId}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {log.affected_ofc_ids && log.affected_ofc_ids.length > 0 && (
                      <div>
                        <strong className="text-gray-700">OFCs ({log.affected_ofc_ids.length}):</strong>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {log.affected_ofc_ids.map((ofcId, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs font-mono"
                            >
                              {ofcId}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {logs.length > 0 && (
          <div className="text-center text-sm text-gray-500 mt-6">
            Showing {logs.length} audit log entries
          </div>
        )}
      </div>
    </RoleGate>
  )
}

