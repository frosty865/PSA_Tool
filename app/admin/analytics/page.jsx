'use client'

import { useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { motion } from 'framer-motion'
import RoleGate from '@/components/RoleGate'
import '@/styles/cisa.css'

export default function AnalyticsDashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  async function fetchAnalytics() {
    try {
      setLoading(true)
      const res = await fetch('/api/analytics/summary', { cache: 'no-store' })
      
      if (!res.ok) {
        if (res.status === 202) {
          // Analytics not ready yet
          setError('Analytics are being collected. Please check back in a few minutes.')
          setLoading(false)
          return
        }
        throw new Error('Failed to load analytics')
      }
      
      const data = await res.json()
      setStats(data)
      setError(null)
    } catch (err) {
      console.error('Analytics fetch error:', err)
      setError(err.message || 'Failed to load analytics')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAnalytics()
    const interval = setInterval(fetchAnalytics, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [])

  return (
    <RoleGate requiredRole="admin">
      <div style={{ padding: 'var(--spacing-lg)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-lg)' }}>
          <h1 style={{ fontSize: 'var(--font-size-xxl)', fontWeight: 700, color: 'var(--cisa-blue)', margin: 0 }}>
            Analytics Dashboard
          </h1>
          <button
            onClick={fetchAnalytics}
            disabled={loading}
            className="btn btn-primary btn-sm"
            style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-xs)' }}
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>

        {error && (
          <div className="alert alert-warning" style={{ marginBottom: 'var(--spacing-lg)' }}>
            {error}
          </div>
        )}

        {loading && !stats ? (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{
                width: '48px',
                height: '48px',
                border: '3px solid var(--cisa-gray-light)',
                borderTopColor: 'var(--cisa-blue)',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
                margin: '0 auto var(--spacing-md)'
              }}></div>
              <p style={{ color: 'var(--cisa-gray)' }}>Loading analytics...</p>
            </div>
          </div>
        ) : stats ? (
          <div style={{ display: 'grid', gap: 'var(--spacing-lg)' }}>
            {/* Summary Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 'var(--spacing-lg)' }}>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="card"
                style={{
                  background: 'linear-gradient(135deg, var(--cisa-blue-lightest) 0%, rgba(0, 113, 188, 0.05) 100%)',
                  border: '1px solid var(--cisa-blue-lighter)'
                }}
              >
                <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--cisa-gray)', marginBottom: 'var(--spacing-xs)' }}>
                  Total Submissions
                </div>
                <div style={{ fontSize: 'var(--font-size-xxl)', fontWeight: 700, color: 'var(--cisa-blue)' }}>
                  {stats.total_submissions || 0}
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="card"
                style={{
                  background: 'linear-gradient(135deg, var(--cisa-green-lightest) 0%, rgba(40, 167, 69, 0.05) 100%)',
                  border: '1px solid rgba(40, 167, 69, 0.3)'
                }}
              >
                <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--cisa-gray)', marginBottom: 'var(--spacing-xs)' }}>
                  Approved
                </div>
                <div style={{ fontSize: 'var(--font-size-xxl)', fontWeight: 700, color: 'var(--cisa-success)' }}>
                  {stats.approved || 0}
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="card"
                style={{
                  background: 'linear-gradient(135deg, var(--cisa-red-lightest) 0%, rgba(220, 53, 69, 0.05) 100%)',
                  border: '1px solid rgba(220, 53, 69, 0.3)'
                }}
              >
                <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--cisa-gray)', marginBottom: 'var(--spacing-xs)' }}>
                  Rejected
                </div>
                <div style={{ fontSize: 'var(--font-size-xxl)', fontWeight: 700, color: 'var(--cisa-danger)' }}>
                  {stats.rejected || 0}
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="card"
                style={{
                  background: 'linear-gradient(135deg, var(--cisa-purple-lightest) 0%, rgba(138, 43, 226, 0.05) 100%)',
                  border: '1px solid rgba(138, 43, 226, 0.3)'
                }}
              >
                <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--cisa-gray)', marginBottom: 'var(--spacing-xs)' }}>
                  Approval Rate
                </div>
                <div style={{ fontSize: 'var(--font-size-xxl)', fontWeight: 700, color: 'var(--cisa-purple)' }}>
                  {stats.total_submissions > 0 
                    ? ((stats.approved / stats.total_submissions) * 100).toFixed(1) 
                    : 0}%
                </div>
              </motion.div>
            </div>

            {/* Detailed Stats Table */}
            {stats.by_model && stats.by_model.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="card"
              >
                <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 600, color: 'var(--cisa-blue)', marginBottom: 'var(--spacing-md)' }}>
                  Statistics by Model
                </h2>
                <div style={{ overflowX: 'auto' }}>
                  <table className="table" style={{ width: '100%' }}>
                    <thead>
                      <tr>
                        <th>Model Version</th>
                        <th>Total</th>
                        <th>Approved</th>
                        <th>Rejected</th>
                        <th>Approval Rate</th>
                        <th>Avg Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.by_model.map((model, idx) => (
                        <tr key={idx}>
                          <td><strong>{model.model_version || 'Unknown'}</strong></td>
                          <td>{model.total || 0}</td>
                          <td style={{ color: 'var(--cisa-success)' }}>{model.approved || 0}</td>
                          <td style={{ color: 'var(--cisa-danger)' }}>{model.rejected || 0}</td>
                          <td>
                            {model.total > 0 
                              ? ((model.approved / model.total) * 100).toFixed(1) 
                              : 0}%
                          </td>
                          <td>
                            {model.avg_confidence 
                              ? (model.avg_confidence * 100).toFixed(1) 
                              : 'N/A'}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </motion.div>
            )}
          </div>
        ) : (
          <div className="card" style={{ padding: 'var(--spacing-xl)', textAlign: 'center' }}>
            <p style={{ color: 'var(--cisa-gray)' }}>No analytics data available yet.</p>
          </div>
        )}
      </div>
    </RoleGate>
  )
}

