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
  const [clearing, setClearing] = useState(false)

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

  async function clearAuditTrail() {
    if (!confirm('Are you sure you want to clear the entire audit trail? This action cannot be undone.')) {
      return
    }

    try {
      setClearing(true)
      setError(null)
      
      const res = await fetchWithAuth('/api/admin/audit', {
        method: 'DELETE',
        cache: 'no-store'
      })
      
      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(errorData.error || `Failed to clear audit trail: ${res.status}`)
      }
      
      const data = await res.json()
      alert(`Audit trail cleared successfully. ${data.deleted || 0} entries deleted.`)
      
      // Reload the audit logs (will be empty now)
      await loadAuditLogs()
    } catch (err) {
      console.error('Error clearing audit trail:', err)
      setError(err.message)
      alert(`Error clearing audit trail: ${err.message}`)
    } finally {
      setClearing(false)
    }
  }

  return (
    <RoleGate requiredRole="admin">
      {loading && logs.length === 0 ? (
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          minHeight: '100vh' 
        }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{
              width: '48px',
              height: '48px',
              border: '3px solid var(--cisa-gray-light)',
              borderTop: '3px solid var(--cisa-blue)',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
              margin: '0 auto'
            }}></div>
            <p style={{ 
              marginTop: 'var(--spacing-md)', 
              color: 'var(--cisa-gray)',
              fontSize: 'var(--font-size-md)'
            }}>
              Loading audit log...
            </p>
          </div>
        </div>
      ) : (
      <div style={{ 
        padding: 'var(--spacing-lg)', 
        maxWidth: '1600px', 
        margin: '0 auto',
        minHeight: '100vh' 
      }}>
        <div style={{ marginBottom: 'var(--spacing-xl)' }}>
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'flex-start',
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
                Review Audit Trail
              </h1>
              <p style={{ 
                fontSize: 'var(--font-size-md)', 
                color: 'var(--cisa-gray)',
                margin: 0
              }}>
                Track all admin review actions including approvals, rejections, and edits.
                Each entry links to the affected submission and production records.
              </p>
            </div>
            {logs.length > 0 && (
              <button
                onClick={clearAuditTrail}
                disabled={clearing}
                className="btn"
                style={{ 
                  minWidth: '120px',
                  backgroundColor: clearing ? 'var(--cisa-gray-light)' : 'var(--cisa-red)',
                  color: 'var(--cisa-white)',
                  cursor: clearing ? 'not-allowed' : 'pointer',
                  opacity: clearing ? 0.6 : 1
                }}
              >
                {clearing ? 'Clearing...' : '🗑️ Clear All'}
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="alert alert-warning" style={{ 
            padding: 'var(--spacing-md)', 
            marginBottom: 'var(--spacing-lg)',
            backgroundColor: '#fff3cd',
            border: '1px solid var(--cisa-warning)',
            borderRadius: 'var(--border-radius)'
          }}>
            <strong>Error:</strong> {error}
            <button 
              onClick={loadAuditLogs}
              className="btn btn-primary"
              style={{ 
                marginLeft: 'var(--spacing-md)',
                padding: 'var(--spacing-xs) var(--spacing-sm)',
                fontSize: 'var(--font-size-sm)'
              }}
            >
              Retry
            </button>
          </div>
        )}

        {/* Filter Buttons */}
        <div style={{ 
          display: 'flex', 
          gap: 'var(--spacing-sm)', 
          marginBottom: 'var(--spacing-lg)',
          flexWrap: 'wrap'
        }}>
          <button
            onClick={() => setFilter('all')}
            className="btn"
            style={{
              backgroundColor: filter === 'all' ? 'var(--cisa-blue)' : 'var(--cisa-gray-light)',
              color: filter === 'all' ? 'var(--cisa-white)' : 'var(--cisa-black)',
              padding: 'var(--spacing-sm) var(--spacing-md)'
            }}
          >
            All Actions
          </button>
          <button
            onClick={() => setFilter('approved')}
            className="btn"
            style={{
              backgroundColor: filter === 'approved' ? 'var(--cisa-success)' : 'var(--cisa-gray-light)',
              color: filter === 'approved' ? 'var(--cisa-white)' : 'var(--cisa-black)',
              padding: 'var(--spacing-sm) var(--spacing-md)'
            }}
          >
            Approved
          </button>
          <button
            onClick={() => setFilter('rejected')}
            className="btn"
            style={{
              backgroundColor: filter === 'rejected' ? 'var(--cisa-red)' : 'var(--cisa-gray-light)',
              color: filter === 'rejected' ? 'var(--cisa-white)' : 'var(--cisa-black)',
              padding: 'var(--spacing-sm) var(--spacing-md)'
            }}
          >
            Rejected
          </button>
          <button
            onClick={() => setFilter('edited')}
            className="btn"
            style={{
              backgroundColor: filter === 'edited' ? 'var(--cisa-warning)' : 'var(--cisa-gray-light)',
              color: filter === 'edited' ? 'var(--cisa-black)' : 'var(--cisa-black)',
              padding: 'var(--spacing-sm) var(--spacing-md)'
            }}
          >
            Edited
          </button>
        </div>

        {logs.length === 0 ? (
          <div className="card" style={{
            padding: 'var(--spacing-xxl)',
            textAlign: 'center',
            backgroundColor: 'var(--cisa-white)'
          }}>
            <p style={{ 
              color: 'var(--cisa-gray)', 
              fontSize: 'var(--font-size-lg)',
              margin: 0
            }}>
              {error ? 'Unable to load audit logs' : 'No audit log entries found'}
            </p>
            {error && (
              <p style={{ 
                color: 'var(--cisa-gray-light)', 
                fontSize: 'var(--font-size-sm)', 
                marginTop: 'var(--spacing-sm)',
                margin: 0
              }}>
                The audit_log table may not exist. Please create it in Supabase.
              </p>
            )}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)' }}>
            {logs.map(log => {
              const colors = getActionBadgeColor(log.action)
              return (
                <div
                  key={log.id}
                  className="card"
                  style={{
                    border: `2px solid ${colors.border}`,
                    borderRadius: 'var(--border-radius)',
                    padding: 'var(--spacing-lg)',
                    backgroundColor: colors.bg,
                    transition: 'all 0.3s ease'
                  }}
                >
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'flex-start',
                    marginBottom: 'var(--spacing-md)'
                  }}>
                    <div style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: 'var(--spacing-md)',
                      flexWrap: 'wrap'
                    }}>
                      <span
                        style={{
                          padding: 'var(--spacing-xs) var(--spacing-sm)',
                          borderRadius: 'var(--border-radius)',
                          fontSize: 'var(--font-size-sm)',
                          fontWeight: 600,
                          backgroundColor: colors.border,
                          color: 'var(--cisa-white)'
                        }}
                      >
                        {getActionLabel(log.action)}
                      </span>
                      <span style={{ 
                        fontSize: 'var(--font-size-sm)', 
                        color: 'var(--cisa-gray)'
                      }}>
                        {new Date(log.timestamp).toLocaleString()}
                      </span>
                    </div>
                  </div>

                  <div style={{ 
                    display: 'flex', 
                    flexDirection: 'column', 
                    gap: 'var(--spacing-sm)',
                    fontSize: 'var(--font-size-sm)'
                  }}>
                    <div>
                      <strong style={{ color: 'var(--cisa-black)' }}>Reviewer:</strong>{' '}
                      <span style={{ 
                        color: 'var(--cisa-gray)', 
                        fontFamily: 'monospace',
                        fontSize: 'var(--font-size-xs)'
                      }}>
                        {log.reviewer_id || 'System'}
                      </span>
                    </div>
                    
                    <div>
                      <strong style={{ color: 'var(--cisa-black)' }}>Submission:</strong>{' '}
                      <span style={{ 
                        color: 'var(--cisa-gray)', 
                        fontFamily: 'monospace',
                        fontSize: 'var(--font-size-xs)'
                      }}>
                        {log.submission_id}
                      </span>
                    </div>

                    {log.notes && (
                      <div>
                        <strong style={{ color: 'var(--cisa-black)' }}>Notes:</strong>
                        <p style={{ 
                          color: 'var(--cisa-gray)', 
                          marginTop: 'var(--spacing-xs)',
                          margin: 0
                        }}>
                          {log.notes}
                        </p>
                      </div>
                    )}

                    {log.affected_vuln_ids && log.affected_vuln_ids.length > 0 && (
                      <div>
                        <strong style={{ color: 'var(--cisa-black)' }}>
                          Vulnerabilities ({log.affected_vuln_ids.length}):
                        </strong>
                        <div style={{ 
                          marginTop: 'var(--spacing-xs)', 
                          display: 'flex', 
                          flexWrap: 'wrap', 
                          gap: 'var(--spacing-xs)'
                        }}>
                          {log.affected_vuln_ids.map((vulnId, idx) => (
                            <span
                              key={idx}
                              style={{
                                padding: 'var(--spacing-xs) var(--spacing-sm)',
                                backgroundColor: 'var(--cisa-blue-lightest)',
                                color: 'var(--cisa-blue)',
                                borderRadius: 'var(--border-radius)',
                                fontSize: 'var(--font-size-xs)',
                                fontFamily: 'monospace'
                              }}
                            >
                              {vulnId}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {log.affected_ofc_ids && log.affected_ofc_ids.length > 0 && (
                      <div>
                        <strong style={{ color: 'var(--cisa-black)' }}>
                          OFCs ({log.affected_ofc_ids.length}):
                        </strong>
                        <div style={{ 
                          marginTop: 'var(--spacing-xs)', 
                          display: 'flex', 
                          flexWrap: 'wrap', 
                          gap: 'var(--spacing-xs)'
                        }}>
                          {log.affected_ofc_ids.map((ofcId, idx) => (
                            <span
                              key={idx}
                              style={{
                                padding: 'var(--spacing-xs) var(--spacing-sm)',
                                backgroundColor: '#e6e6fa',
                                color: '#6a0dad',
                                borderRadius: 'var(--border-radius)',
                                fontSize: 'var(--font-size-xs)',
                                fontFamily: 'monospace'
                              }}
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
          <div style={{ 
            textAlign: 'center', 
            fontSize: 'var(--font-size-sm)', 
            color: 'var(--cisa-gray)', 
            marginTop: 'var(--spacing-xl)'
          }}>
            Showing {logs.length} audit log entries
          </div>
        )}
      </div>
      )}
    </RoleGate>
  )
}

