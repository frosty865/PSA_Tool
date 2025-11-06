'use client'

import { useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { motion } from 'framer-motion'
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
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchAnalytics() }, [])

  if (loading) {
    return (
      <div className="page-container">
        <div className="content-wrapper">
          <div className="text-center py-8">
            <div className="loading"></div>
            <p className="text-secondary mt-3">Loading analytics…</p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="content-wrapper">
          <div className="card">
            <div className="card-header">
              <h1 className="card-title">Analytics Dashboard</h1>
            </div>
            <div className="card-body">
              <div className="error-message">
                <p>Error: {error}</p>
                <button onClick={fetchAnalytics} className="btn btn-primary mt-4">
                  <RefreshCw className="h-4 w-4 inline mr-2" />
                  Retry
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="page-container">
        <div className="content-wrapper">
          <div className="card">
            <div className="card-body">
              <p className="text-secondary">No analytics data available</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="page-container">
      <div className="content-wrapper">
        <motion.div 
          className="space-y-6"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          {/* Page Header */}
          <div className="card-header">
            <div className="flex justify-between items-center">
              <div>
                <h1 className="card-title">PSA Analytics Dashboard</h1>
                <p className="card-subtitle">
                  Learning events metrics and model performance
                </p>
              </div>
              <button 
                onClick={fetchAnalytics} 
                className="btn btn-secondary"
                title="Refresh analytics"
              >
                <RefreshCw className="h-4 w-4 inline mr-2" />
                Refresh
              </button>
            </div>
          </div>

          {/* Metrics Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Total Events */}
            <motion.div
              className="card"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3, delay: 0.1 }}
            >
              <div className="card-header">
                <h2 className="card-title text-lg">Total Events</h2>
              </div>
              <div className="card-body">
                <div className="text-4xl font-bold text-blue-600">
                  {stats.total_events || 0}
                </div>
              </div>
            </motion.div>

            {/* Approved Events */}
            <motion.div
              className="card"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3, delay: 0.2 }}
            >
              <div className="card-header">
                <h2 className="card-title text-lg">Approved Events</h2>
              </div>
              <div className="card-body">
                <div className="text-4xl font-bold text-green-600">
                  {stats.approved_events || 0}
                </div>
              </div>
            </motion.div>

            {/* Approval Rate */}
            <motion.div
              className="card"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3, delay: 0.3 }}
            >
              <div className="card-header">
                <h2 className="card-title text-lg">Approval Rate</h2>
              </div>
              <div className="card-body">
                <div className="text-4xl font-bold text-purple-600">
                  {stats.approval_rate ? (stats.approval_rate * 100).toFixed(1) : '0.0'}%
                </div>
              </div>
            </motion.div>

            {/* Average Confidence */}
            <motion.div
              className="card"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3, delay: 0.4 }}
            >
              <div className="card-header">
                <h2 className="card-title text-lg">Avg Confidence</h2>
              </div>
              <div className="card-body">
                <div className="text-4xl font-bold text-indigo-600">
                  {stats.avg_confidence ? (stats.avg_confidence * 100).toFixed(1) + '%' : '—'}
                </div>
              </div>
            </motion.div>
          </div>

          {/* Additional Info */}
          <div className="card">
            <div className="card-body">
              <div className="flex justify-between items-center flex-wrap gap-4">
                <div>
                  <p className="text-sm text-secondary mb-1">
                    <strong>Latest Model:</strong> {stats.latest_model || '—'}
                  </p>
                  <p className="text-sm text-secondary">
                    <strong>Last Updated:</strong> {stats.timestamp ? new Date(stats.timestamp).toLocaleString() : '—'}
                  </p>
                  {stats.retrieved_at && (
                    <p className="text-sm text-secondary mt-1">
                      <strong>Retrieved:</strong> {new Date(stats.retrieved_at).toLocaleString()}
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

