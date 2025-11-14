'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { fetchWithAuth } from '../lib/fetchWithAuth'
import '@/styles/cisa.css'
import Link from 'next/link'

export default function AdminOverviewPage() {
  const router = useRouter()
  const [stats, setStats] = useState([])
  const [soft, setSoft] = useState([])
  const [system, setSystem] = useState({ flask: 'checking', ollama: 'checking', supabase: 'checking', tunnel: 'checking', model_manager: 'checking', watcher: 'checking' })
  const [modelManagerInfo, setModelManagerInfo] = useState(null)
  const [countdown, setCountdown] = useState(null)
  const [pendingReviewCount, setPendingReviewCount] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastRefresh, setLastRefresh] = useState(null)
  const [progress, setProgress] = useState(null)

  // System health checker - uses Next.js API route proxy to avoid CORS issues
  // Manual refresh function (for button clicks)
  const fetchSystemHealth = useCallback(async () => {
    try {
      const res = await fetch('/api/system/health', { 
        cache: 'no-store',
        headers: { 'Accept': 'application/json' }
      })
      
      if (!res.ok) {
        throw new Error(`Health check API returned ${res.status}`)
      }
      
      const json = await res.json()
      
      if (json.components) {
        setSystem(json.components)
        // Update Model Manager info if available
        if (json.model_manager_info) {
          setModelManagerInfo(json.model_manager_info)
        }
      } else {
        setSystem({ flask: 'unknown', ollama: 'unknown', supabase: 'unknown', tunnel: 'unknown', model_manager: 'unknown', watcher: 'unknown' })
      }
    } catch (err) {
      console.error('[System Health] Manual refresh failed:', err)
      // On manual refresh, show error but don't change state if we have a previous good state
      setSystem(prev => prev.flask === 'checking' || prev.flask === 'unknown'
        ? { flask: 'offline', ollama: 'unknown', supabase: 'unknown', tunnel: 'unknown', model_manager: 'unknown', watcher: 'unknown' }
        : prev
      )
    }
  }, [])

  // Global error handler to suppress browser extension errors
  useEffect(() => {
    const handleError = (event) => {
      if (event.error && event.error.message && event.error.message.includes('message channel')) {
        event.preventDefault() // Suppress browser extension errors
        return false
      }
    }
    const handleRejection = (event) => {
      if (event.reason && event.reason.message && event.reason.message.includes('message channel')) {
        event.preventDefault() // Suppress browser extension errors
        return false
      }
    }
    window.addEventListener('error', handleError)
    window.addEventListener('unhandledrejection', handleRejection)
    return () => {
      window.removeEventListener('error', handleError)
      window.removeEventListener('unhandledrejection', handleRejection)
    }
  }, [])

  useEffect(() => {
    let isMounted = true
    let hasEverSucceeded = false
    let lastKnownGood = { flask: 'checking', ollama: 'checking', supabase: 'checking', tunnel: 'checking', model_manager: 'checking', watcher: 'checking' }
    
    const healthCheckWithDebounce = async () => {
      if (!isMounted) return
      
      try {
        const res = await fetch('/api/system/health', { 
          cache: 'no-store',
          headers: { 'Accept': 'application/json' }
        })
        
        // Always try to parse JSON, even if status is not OK
        // The route now returns 200 with error status in body for graceful handling
        let json
        try {
          json = await res.json()
        } catch (parseError) {
          // If JSON parsing fails, treat as error
          if (hasEverSucceeded) {
            console.warn(`[System Health] JSON parse error, keeping last known state`)
            setSystem(lastKnownGood)
          } else {
            setSystem({ flask: 'offline', ollama: 'unknown', supabase: 'unknown', tunnel: 'unknown', model_manager: 'unknown' })
          }
          return
        }
        
        // Check if response indicates an error (even if status is 200)
        if (json.status === 'error' || json.status === 'timeout') {
          // Error response but status is 200 - use components from response
          if (json.components) {
            setSystem(json.components)
          } else if (hasEverSucceeded) {
            console.warn(`[System Health] Error status but no components, keeping last known state`)
            setSystem(lastKnownGood)
          } else {
            setSystem({ flask: 'offline', ollama: 'unknown', supabase: 'unknown', tunnel: 'unknown', model_manager: 'unknown' })
          }
          return
        }
        
        // Success response
        if (json.components) {
          hasEverSucceeded = true
          lastKnownGood = json.components
          setSystem(json.components)
          // Update Model Manager info if available
          if (json.model_manager_info) {
            setModelManagerInfo(json.model_manager_info)
          }
        } else {
          // Invalid format but keep last known state if we've succeeded before
          if (hasEverSucceeded) {
            setSystem(lastKnownGood)
          } else {
            setSystem({ flask: 'unknown', ollama: 'unknown', supabase: 'unknown', tunnel: 'unknown', model_manager: 'unknown', watcher: 'unknown' })
          }
        }
      } catch (err) {
        // Network errors are temporary - keep last known good state if we've ever succeeded
        // Ignore browser extension errors (message channel errors)
        if (err.message && err.message.includes('message channel')) {
          return // Silently ignore browser extension errors
        }
        console.warn('[System Health] Temporary network error, keeping last known state:', err.message)
        if (hasEverSucceeded) {
          setSystem(lastKnownGood)
        } else {
          setSystem({ flask: 'offline', ollama: 'unknown', supabase: 'unknown', tunnel: 'unknown', model_manager: 'unknown' })
        }
      }
    }
    
    healthCheckWithDebounce()
    const interval = setInterval(healthCheckWithDebounce, 60000) // 60s interval (reduced from 20s to reduce network load)
    return () => { isMounted = false; clearInterval(interval) }
  }, [])

  // Fetch pending review count directly from database
  useEffect(() => {
    let isMounted = true
    let countInterval = null
    
    const fetchPendingCount = async () => {
      if (!isMounted) return
      try {
        // Use count_only parameter to get accurate count from database
        const res = await fetchWithAuth('/api/admin/submissions?status=pending_review&count_only=true', { cache: 'no-store' })
        if (res.ok && isMounted) {
          const data = await res.json()
          // Get the count directly from the database query
          const count = data.count ?? 0
          setPendingReviewCount(count)
        } else if (isMounted) {
          // If error, try to keep last known value or set to null
          // Fallback: try the old method
          try {
            const fallbackRes = await fetchWithAuth('/api/admin/submissions?status=pending_review', { cache: 'no-store' })
            if (fallbackRes.ok && isMounted) {
              const fallbackData = await fallbackRes.json()
              const count = Array.isArray(fallbackData.submissions) ? fallbackData.submissions.length : 
                           (Array.isArray(fallbackData.allSubmissions) ? fallbackData.allSubmissions.length : 0)
              setPendingReviewCount(count)
            }
          } catch (fallbackErr) {
            // Silently handle fallback errors
          }
        }
      } catch (err) {
        // Don't set to null on error, keep last known value
      }
    }

    fetchPendingCount()
    countInterval = setInterval(() => {
      if (isMounted) {
        fetchPendingCount()
      }
    }, 60000) // Refresh every 60s (reduced from 30s to reduce network load)
    
    return () => {
      isMounted = false
      if (countInterval) clearInterval(countInterval)
    }
  }, [])

  // Countdown timer for Model Manager
  useEffect(() => {
    if (!modelManagerInfo?.next_run) {
      setCountdown(null)
      return
    }

    let isMounted = true
    let countdownInterval = null

    const updateCountdown = () => {
      if (!isMounted) return
      
      const now = new Date()
      const nextRun = new Date(modelManagerInfo.next_run)
      const diff = nextRun - now

      if (diff <= 0) {
        if (isMounted) setCountdown('Due now')
        return
      }

      const hours = Math.floor(diff / (1000 * 60 * 60))
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
      const seconds = Math.floor((diff % (1000 * 60)) / 1000)

      if (!isMounted) return

      if (hours > 0) {
        setCountdown(`${hours}h ${minutes}m`)
      } else if (minutes > 0) {
        setCountdown(`${minutes}m ${seconds}s`)
      } else {
        setCountdown(`${seconds}s`)
      }
    }

    updateCountdown()
    countdownInterval = setInterval(() => {
      if (isMounted) {
        updateCountdown()
      }
    }, 1000)
    
    return () => {
      isMounted = false
      if (countdownInterval) clearInterval(countdownInterval)
    }
  }, [modelManagerInfo])

  // Admin overview data fetcher
  const loadDashboardData = useCallback(async () => {
    try {
      const res = await fetchWithAuth('/api/dashboard/overview', { cache: 'no-store' })
      
      if (!res.ok) {
        const errorText = await res.text()
        console.error(`[Admin Overview] API error: ${res.status}`, errorText.substring(0, 200))
        throw new Error(`HTTP ${res.status}: ${res.status === 401 ? 'Unauthorized' : res.status === 403 ? 'Forbidden' : 'Server Error'}`)
      }
      
      const json = await res.json()
      setStats(json.stats || [])
      setSoft(json.soft || [])
      setError(null)
      setLastRefresh(new Date())
    } catch (e) {
      console.error('[Admin Overview] Load error:', e)
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  // Progress fetcher
  const fetchProgress = useCallback(async () => {
    try {
      const res = await fetch('/api/proxy/flask/progress', { 
        cache: 'no-store',
        headers: { 'Accept': 'application/json' }
      })
      if (res.ok) {
        const data = await res.json()
        setProgress(data)
      }
    } catch (err) {
      console.error('[Progress] Fetch failed:', err)
    }
  }, [])

  useEffect(() => {
    let isMounted = true
    loadDashboardData()
    fetchProgress() // Initial fetch
    const id = setInterval(() => {
      if (isMounted) {
        loadDashboardData()
        fetchProgress()
      }
    }, 3000) // Poll every 3 seconds for progress updates
    return () => { isMounted = false; clearInterval(id) }
  }, [loadDashboardData, fetchProgress])

  // Calculate aggregate statistics
  const aggregateStats = stats.length > 0 ? {
    avgAcceptRate: stats.reduce((sum, s) => sum + (s.accept_rate || 0), 0) / stats.length,
    avgSoftmatchRatio: stats.reduce((sum, s) => sum + (s.softmatch_ratio || 0), 0) / stats.length,
    latestModel: stats[0]?.model_version || 'N/A',
    totalModels: stats.length
  } : null

  const getSystemStatusColor = (status) => {
    switch (status) {
      case 'ok':
      case 'online': // Legacy support
      case 'active': // Legacy support
      case 'running': // Legacy support
        return { bg: '#e6f6ea', border: '#00a651', text: '#007a3d' }
      case 'paused':
        return { bg: '#fff9e6', border: '#ffc107', text: '#856404' }
      case 'failed':
      case 'offline': // Legacy support
      case 'error': // Legacy support
        return { bg: '#fdecea', border: '#c00', text: '#a00' }
      case 'checking':
        return { bg: '#fff3cd', border: '#ffc107', text: '#856404' }
      case 'unknown': // Legacy support - treat as failed
      default:
        return { bg: '#f5f5f5', border: '#9ca3af', text: '#6b7280' }
    }
  }
  
  const getSystemStatusLabel = (status) => {
    switch (status) {
      case 'ok':
      case 'online': // Legacy support
      case 'active': // Legacy support
      case 'running': // Legacy support
        return 'Online'
      case 'paused':
        return 'Paused'
      case 'failed':
        return 'Failed'
      case 'offline': // Legacy support
      case 'error': // Legacy support
        return 'Failed'
      case 'checking':
        return 'Checking...'
      case 'unknown': // Legacy support - treat as failed
        return 'Failed'
      default:
        return 'Failed'
    }
  }
  
  const getSystemIcon = (key) => {
    switch (key) {
      case 'flask':
        return '🔧'
      case 'ollama':
        return '🤖'
      case 'supabase':
        return '🗄️'
      case 'tunnel':
        return '🌐'
      case 'model_manager':
        return '🧠'
      case 'watcher':
        return '👁️'
      default:
        return '⚙️'
    }
  }

  if (error && !stats.length && !soft.length) {
    return (
      <div className="alert alert-danger" style={{ 
        padding: 'var(--spacing-xl)', 
        backgroundColor: '#fee', 
        border: '1px solid #f00',
        borderRadius: 'var(--border-radius)',
        margin: 'var(--spacing-lg)',
        textAlign: 'center'
      }}>
        <h2 style={{ margin: '0 0 var(--spacing-md) 0', color: '#c00' }}>⚠️ Error Loading Admin Dashboard</h2>
        <p style={{ margin: '0 0 var(--spacing-md) 0', color: '#800', fontSize: 'var(--font-size-lg)' }}>{error}</p>
        <p style={{ margin: 'var(--spacing-sm) 0 0 0', fontSize: 'var(--font-size-sm)', color: '#666' }}>
          This may indicate an authentication issue. Check the browser console for details.
        </p>
        <button 
          onClick={() => { setLoading(true); setError(null); loadDashboardData(); }}
          className="btn btn-primary"
          style={{ marginTop: 'var(--spacing-md)' }}
        >
          🔄 Retry
        </button>
      </div>
    )
  }

  return (
    <div style={{ padding: 'var(--spacing-lg)', maxWidth: '1600px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: 'var(--spacing-xl)',
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
            VOFC Admin Dashboard
          </h1>
          {lastRefresh && (
            <p style={{ 
              fontSize: 'var(--font-size-sm)', 
              color: 'var(--cisa-gray)', 
              margin: 0 
            }}>
              Last updated: {lastRefresh.toLocaleTimeString()}
            </p>
          )}
        </div>
        <button 
          onClick={() => { setLoading(true); loadDashboardData(); fetchSystemHealth(); }}
          className="btn btn-primary"
          disabled={loading}
          style={{ opacity: loading ? 0.6 : 1 }}
        >
          {loading ? '⏳ Refreshing...' : '🔄 Refresh'}
        </button>
      </div>

      {error && stats.length > 0 && (
        <div className="alert alert-warning" style={{ 
          padding: 'var(--spacing-md)', 
          marginBottom: 'var(--spacing-lg)',
          backgroundColor: '#fff3cd',
          border: '1px solid #ffc107',
          borderRadius: 'var(--border-radius)'
        }}>
          <strong>⚠️ Warning:</strong> {error} (showing cached data)
        </div>
      )}

      {/* Document Processing Progress */}
      {progress && progress.status === 'processing' && (
        <div className="card" style={{ 
          marginBottom: 'var(--spacing-lg)',
          backgroundColor: 'var(--cisa-blue-lightest)',
          border: '2px solid var(--cisa-blue)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--spacing-md)' }}>
            <h2 style={{ 
              fontSize: 'var(--font-size-lg)', 
              fontWeight: 600, 
              color: 'var(--cisa-blue)', 
              margin: 0 
            }}>
              📄 Processing Document
            </h2>
            <span style={{
              padding: '4px 12px',
              borderRadius: '999px',
              fontSize: 'var(--font-size-xs)',
              fontWeight: 600,
              backgroundColor: 'var(--cisa-blue)',
              color: 'white'
            }}>
              {progress.progress_percent || 0}%
            </span>
          </div>
          <div style={{ marginBottom: 'var(--spacing-md)' }}>
            <p style={{ 
              fontSize: 'var(--font-size-base)', 
              fontWeight: 600, 
              color: 'var(--cisa-black)', 
              margin: '0 0 var(--spacing-xs) 0' 
            }}>
              {progress.current_file || 'Processing...'}
            </p>
            <p style={{ 
              fontSize: 'var(--font-size-sm)', 
              color: 'var(--cisa-gray)', 
              margin: 0 
            }}>
              {progress.message}
            </p>
          </div>
          {progress.total_files > 0 && (
            <div style={{ marginBottom: 'var(--spacing-sm)' }}>
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                fontSize: 'var(--font-size-xs)', 
                color: 'var(--cisa-gray)',
                marginBottom: '4px'
              }}>
                <span>File {progress.current_step || 0} of {progress.total_files}</span>
                <span>{progress.progress_percent || 0}% complete</span>
              </div>
              <div style={{
                width: '100%',
                height: '8px',
                backgroundColor: 'var(--cisa-gray-light)',
                borderRadius: '4px',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${progress.progress_percent || 0}%`,
                  height: '100%',
                  backgroundColor: 'var(--cisa-blue)',
                  transition: 'width 0.3s ease'
                }}></div>
              </div>
            </div>
          )}
          <p style={{ 
            fontSize: 'var(--font-size-xs)', 
            color: 'var(--cisa-gray)', 
            opacity: 0.7,
            margin: 'var(--spacing-xs) 0 0 0'
          }}>
            Started: {new Date(progress.timestamp).toLocaleTimeString('en-US', { timeZone: 'America/New_York', timeZoneName: 'short' })}
          </p>
        </div>
      )}

      {/* System Health Summary */}
      <section style={{ marginBottom: 'var(--spacing-xl)' }}>
        <h2 style={{ 
          fontSize: 'var(--font-size-xl)', 
          fontWeight: 600, 
          color: 'var(--cisa-blue)', 
          margin: 0,
          marginBottom: 'var(--spacing-md)'
        }}>
          System Health
        </h2>
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', 
          gap: 'var(--spacing-lg)'
        }}>
          {['flask', 'ollama', 'supabase', 'tunnel', 'model_manager', 'watcher'].map(key => {
            const status = system[key] || 'checking'
            const colors = getSystemStatusColor(status)
            const statusLabel = getSystemStatusLabel(status)
            const icon = getSystemIcon(key)
            let displayName
            if (key === 'flask') {
              displayName = 'VOFC Flask API Server'
            } else if (key === 'tunnel') {
              displayName = 'Cloudflare Tunnel'
            } else if (key === 'model_manager') {
              displayName = 'Model Manager'
            } else if (key === 'watcher') {
              displayName = 'VOFC Processor (Watcher)'
            } else {
              displayName = `${key.charAt(0).toUpperCase() + key.slice(1)} Server`
            }
            
            return (
              <div 
                key={key} 
                className="card" 
                style={{
                  backgroundColor: colors.bg,
                  border: `2px solid ${colors.border}`,
                  transition: 'all 0.3s ease',
                  position: 'relative',
                  overflow: 'hidden',
                  padding: 'var(--spacing-md)'
                }}
              >
                <div style={{ 
                  position: 'absolute', 
                  top: 0, 
                  right: 0, 
                  width: '4px', 
                  height: '100%',
                  backgroundColor: colors.border
                }}></div>
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: 'var(--spacing-sm)',
                  marginBottom: 'var(--spacing-sm)'
                }}>
                  <span style={{ fontSize: 'var(--font-size-xl)' }}>{icon}</span>
                  <div style={{ 
                    fontWeight: 700, 
                    color: colors.text,
                    fontSize: 'var(--font-size-lg)'
                  }}>
                    {displayName}
                  </div>
                </div>
                <div style={{ 
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 'var(--spacing-xs)',
                  marginTop: 'var(--spacing-xs)'
                }}>
                  <div style={{ 
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--spacing-xs)'
                  }}>
                    <div style={{
                      width: '10px',
                      height: '10px',
                      borderRadius: '50%',
                      backgroundColor: colors.border,
                      boxShadow: `0 0 6px ${colors.border}`,
                      flexShrink: 0
                    }}></div>
                    <div style={{ 
                      fontSize: 'var(--font-size-sm)', 
                      color: colors.text,
                      fontWeight: 600
                    }}>
                      {statusLabel}
                    </div>
                  </div>
                  {key === 'model_manager' && countdown && status === 'ok' && (
                    <div style={{ 
                      fontSize: 'var(--font-size-xs)', 
                      color: 'var(--cisa-gray)',
                      marginLeft: '18px',
                      fontStyle: 'italic'
                    }}>
                      Next run: {countdown}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </section>

      {/* Key Metrics Overview */}
      {aggregateStats && (
        <section style={{ marginBottom: 'var(--spacing-xl)' }}>
          <h2 style={{ 
            fontSize: 'var(--font-size-xl)', 
            fontWeight: 600, 
            color: 'var(--cisa-blue)', 
            marginBottom: 'var(--spacing-md)'
          }}>
            Key Metrics Overview
          </h2>
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', 
            gap: 'var(--spacing-lg)'
          }}>
            <div className="card" style={{
              background: 'linear-gradient(135deg, var(--cisa-blue-lightest) 0%, rgba(0, 113, 188, 0.05) 100%)',
              border: '1px solid var(--cisa-blue-lighter)'
            }}>
              <div style={{ 
                fontSize: 'var(--font-size-sm)', 
                color: 'var(--cisa-gray)', 
                marginBottom: 'var(--spacing-xs)'
              }}>
                Average Accept Rate
              </div>
              <div style={{ 
                fontSize: 'var(--font-size-xxl)', 
                fontWeight: 700, 
                color: 'var(--cisa-blue)',
                marginBottom: 'var(--spacing-xs)'
              }}>
                {(aggregateStats.avgAcceptRate * 100).toFixed(1)}%
              </div>
              <div style={{ 
                fontSize: 'var(--font-size-xs)', 
                color: 'var(--cisa-gray)',
                opacity: 0.7
              }}>
                Across {aggregateStats.totalModels} model{aggregateStats.totalModels !== 1 ? 's' : ''}
              </div>
            </div>

            <div className="card" style={{
              background: 'linear-gradient(135deg, rgba(138, 43, 226, 0.1) 0%, rgba(138, 43, 226, 0.05) 100%)',
              border: '1px solid rgba(138, 43, 226, 0.3)'
            }}>
              <div style={{ 
                fontSize: 'var(--font-size-sm)', 
                color: 'var(--cisa-gray)', 
                marginBottom: 'var(--spacing-xs)'
              }}>
                Average Softmatch Ratio
              </div>
              <div style={{ 
                fontSize: 'var(--font-size-xxl)', 
                fontWeight: 700, 
                color: '#6f42c1',
                marginBottom: 'var(--spacing-xs)'
              }}>
                {(aggregateStats.avgSoftmatchRatio * 100).toFixed(1)}%
              </div>
              <div style={{ 
                fontSize: 'var(--font-size-xs)', 
                color: 'var(--cisa-gray)',
                opacity: 0.7
              }}>
                Near-duplicate detection rate
              </div>
            </div>

            <div className="card" style={{
              background: 'linear-gradient(135deg, rgba(40, 167, 69, 0.1) 0%, rgba(40, 167, 69, 0.05) 100%)',
              border: '1px solid rgba(40, 167, 69, 0.3)'
            }}>
              <div style={{ 
                fontSize: 'var(--font-size-sm)', 
                color: 'var(--cisa-gray)', 
                marginBottom: 'var(--spacing-xs)'
              }}>
                Latest Model Version
              </div>
              <div style={{ 
                fontSize: 'var(--font-size-lg)', 
                fontWeight: 700, 
                color: '#155724',
                marginBottom: 'var(--spacing-xs)',
                fontFamily: 'monospace'
              }}>
                {aggregateStats.latestModel}
              </div>
              <div style={{ 
                fontSize: 'var(--font-size-xs)', 
                color: 'var(--cisa-gray)',
                opacity: 0.7
              }}>
                Currently in use
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Model Performance Summary */}
      <section style={{ marginBottom: 'var(--spacing-xl)' }}>
        <h2 style={{ 
          fontSize: 'var(--font-size-xl)', 
          fontWeight: 600, 
          color: 'var(--cisa-blue)', 
          marginBottom: 'var(--spacing-md)'
        }}>
          Model Performance Summary
        </h2>
        {loading && !stats.length ? (
          <div style={{ 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center', 
            padding: 'var(--spacing-xl)',
            color: 'var(--cisa-gray)'
          }}>
            <div style={{
              width: '32px',
              height: '32px',
              border: '3px solid var(--cisa-gray-light)',
              borderTopColor: 'var(--cisa-blue)',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
              marginRight: 'var(--spacing-md)'
            }}></div>
            Loading model statistics...
          </div>
        ) : stats.length > 0 ? (
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', 
            gap: 'var(--spacing-lg)'
          }}>
            {stats.map((s) => (
              <div key={s.model_version} className="card" style={{
                transition: 'all 0.3s ease',
                border: '1px solid var(--cisa-gray-light)'
              }}>
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  marginBottom: 'var(--spacing-md)'
                }}>
                  <div style={{ 
                    fontWeight: 700, 
                    color: 'var(--cisa-blue)', 
                    fontSize: 'var(--font-size-lg)',
                    fontFamily: 'monospace'
                  }}>
                    {s.model_version}
                  </div>
                  <div style={{
                    padding: 'var(--spacing-xs) var(--spacing-sm)',
                    borderRadius: 'var(--border-radius)',
                    backgroundColor: 'rgba(0, 113, 188, 0.1)',
                    color: 'var(--cisa-blue)',
                    fontSize: 'var(--font-size-xs)',
                    fontWeight: 600
                  }}>
                    Active
                  </div>
                </div>
                <div style={{ 
                  fontSize: 'var(--font-size-xs)', 
                  color: 'var(--cisa-gray)', 
                  marginBottom: 'var(--spacing-md)',
                  paddingBottom: 'var(--spacing-md)',
                  borderBottom: '1px solid var(--cisa-gray-light)'
                }}>
                  Last updated: {new Date(s.updated_at).toLocaleString('en-US', { timeZone: 'America/New_York', timeZoneName: 'short' })}
                </div>
                <div style={{ 
                  display: 'grid', 
                  gridTemplateColumns: '1fr 1fr', 
                  gap: 'var(--spacing-md)'
                }}>
                  <div>
                    <div style={{ 
                      fontSize: 'var(--font-size-xs)', 
                      color: 'var(--cisa-gray)',
                      marginBottom: 'var(--spacing-xs)'
                    }}>
                      Accept Rate
                    </div>
                    <div style={{ 
                      fontSize: 'var(--font-size-xl)', 
                      fontWeight: 700, 
                      color: 'var(--cisa-blue)'
                    }}>
                      {(s.accept_rate * 100).toFixed(1)}%
                    </div>
                    <div style={{ 
                      width: '100%', 
                      height: '6px', 
                      backgroundColor: 'var(--cisa-gray-light)',
                      borderRadius: '3px',
                      marginTop: 'var(--spacing-xs)',
                      overflow: 'hidden'
                    }}>
                      <div style={{ 
                        width: `${(s.accept_rate * 100)}%`, 
                        height: '100%', 
                        backgroundColor: 'var(--cisa-blue)',
                        transition: 'width 0.3s ease'
                      }}></div>
                    </div>
                  </div>
                  <div>
                    <div style={{ 
                      fontSize: 'var(--font-size-xs)', 
                      color: 'var(--cisa-gray)',
                      marginBottom: 'var(--spacing-xs)'
                    }}>
                      Softmatch Ratio
                    </div>
                    <div style={{ 
                      fontSize: 'var(--font-size-xl)', 
                      fontWeight: 700, 
                      color: '#6f42c1'
                    }}>
                      {(s.softmatch_ratio * 100).toFixed(1)}%
                    </div>
                    <div style={{ 
                      width: '100%', 
                      height: '6px', 
                      backgroundColor: 'var(--cisa-gray-light)',
                      borderRadius: '3px',
                      marginTop: 'var(--spacing-xs)',
                      overflow: 'hidden'
                    }}>
                      <div style={{ 
                        width: `${(s.softmatch_ratio * 100)}%`, 
                        height: '100%', 
                        backgroundColor: '#6f42c1',
                        transition: 'width 0.3s ease'
                      }}></div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="card" style={{ 
            padding: 'var(--spacing-xl)', 
            textAlign: 'center',
            color: 'var(--cisa-gray)'
          }}>
            <p style={{ margin: 0, fontSize: 'var(--font-size-lg)' }}>
              No model performance data available yet
            </p>
            <p style={{ margin: 'var(--spacing-sm) 0 0 0', fontSize: 'var(--font-size-sm)' }}>
              Model statistics will appear here once processing begins
            </p>
          </div>
        )}
      </section>

      {/* Admin Actions */}
      <section style={{ marginBottom: 'var(--spacing-xl)' }}>
        <h2 style={{ 
          fontSize: 'var(--font-size-xl)', 
          fontWeight: 600, 
          color: 'var(--cisa-blue)', 
          marginBottom: 'var(--spacing-md)'
        }}>
          Admin Actions
        </h2>
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', 
          gap: 'var(--spacing-md)'
        }}>
          {/* Submission Review - Core Workflow */}
          <div
            className="card" 
            style={{ 
              textDecoration: 'none', 
              transition: 'all 0.3s ease',
              border: '2px solid var(--cisa-blue)',
              background: 'linear-gradient(135deg, rgba(0, 113, 188, 0.05) 0%, rgba(0, 113, 188, 0.02) 100%)',
              position: 'relative',
              overflow: 'hidden',
              display: 'block',
              cursor: 'pointer',
              zIndex: 1
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-4px)'
              e.currentTarget.style.boxShadow = 'var(--shadow-md)'
              e.currentTarget.style.borderColor = 'var(--cisa-blue)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
              e.currentTarget.style.borderColor = 'var(--cisa-blue)'
            }}
            onClick={() => {
              router.push('/admin/review')
            }}
          >
            <div style={{ 
              position: 'absolute',
              top: '8px',
              right: '8px',
              display: 'flex',
              gap: 'var(--spacing-xs)',
              alignItems: 'center',
              zIndex: 2
            }}>
              <div style={{
                fontSize: 'var(--font-size-xs)',
                padding: '2px 8px',
                borderRadius: 'var(--border-radius)',
                backgroundColor: 'var(--cisa-blue)',
                color: 'white',
                fontWeight: 600,
                pointerEvents: 'none'
              }}>CORE</div>
              {pendingReviewCount !== null && pendingReviewCount > 0 && (
                <div style={{
                  fontSize: 'var(--font-size-xs)',
                  padding: '2px 8px',
                  borderRadius: 'var(--border-radius)',
                  backgroundColor: 'var(--cisa-red)',
                  color: 'white',
                  fontWeight: 600,
                  pointerEvents: 'none',
                  minWidth: '24px',
                  textAlign: 'center'
                }}>
                  {pendingReviewCount}
                </div>
              )}
            </div>
            <div style={{ 
              fontSize: 'var(--font-size-xxl)', 
              marginBottom: 'var(--spacing-sm)'
            }}>📋</div>
            <div style={{ 
              fontWeight: 700, 
              color: 'var(--cisa-blue)', 
              marginBottom: 'var(--spacing-xs)',
              fontSize: 'var(--font-size-lg)'
            }}>Submission Review</div>
            <div style={{ 
              fontSize: 'var(--font-size-sm)', 
              color: 'var(--cisa-gray)',
              lineHeight: 1.5
            }}>
              Review user-submitted and document-parsed entries. Approve to move to production tables and feed learning system.
            </div>
          </div>

          {/* Audit Trail */}
          <Link href="/admin/audit" className="card" style={{ 
            textDecoration: 'none', 
            transition: 'all 0.3s ease',
            border: '1px solid var(--cisa-gray-light)',
            background: 'linear-gradient(135deg, rgba(108, 117, 125, 0.05) 0%, rgba(108, 117, 125, 0.02) 100%)'
          }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-4px)'
              e.currentTarget.style.boxShadow = 'var(--shadow-md)'
              e.currentTarget.style.borderColor = '#6c757d'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
              e.currentTarget.style.borderColor = 'var(--cisa-gray-light)'
            }}
          >
            <div style={{ 
              fontSize: 'var(--font-size-xxl)', 
              marginBottom: 'var(--spacing-sm)'
            }}>📋</div>
            <div style={{ 
              fontWeight: 700, 
              color: '#6c757d', 
              marginBottom: 'var(--spacing-xs)',
              fontSize: 'var(--font-size-lg)'
            }}>Audit Trail</div>
            <div style={{ 
              fontSize: 'var(--font-size-sm)', 
              color: 'var(--cisa-gray)',
              lineHeight: 1.5
            }}>
              Track all review actions: approvals, rejections, and edits with full audit history
            </div>
          </Link>

          {/* Processing Monitor */}
          <div
            className="card"
            style={{
              textDecoration: 'none',
              transition: 'all 0.3s ease',
              border: '1px solid var(--cisa-gray-light)',
              background: 'linear-gradient(135deg, rgba(40, 167, 69, 0.05) 0%, rgba(40, 167, 69, 0.02) 100%)',
              position: 'relative',
              overflow: 'hidden',
              display: 'block',
              cursor: 'pointer',
              zIndex: 1
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-4px)'
              e.currentTarget.style.boxShadow = 'var(--shadow-md)'
              e.currentTarget.style.borderColor = 'var(--cisa-success)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
              e.currentTarget.style.borderColor = 'var(--cisa-gray-light)'
            }}
            onClick={() => {
              router.push('/admin/processing')
            }}
          >
            <div style={{
              fontSize: 'var(--font-size-xxl)',
              marginBottom: 'var(--spacing-sm)'
            }}>⚙️</div>
            <div style={{
              fontWeight: 700,
              color: 'var(--cisa-success)',
              marginBottom: 'var(--spacing-xs)',
              fontSize: 'var(--font-size-lg)'
            }}>Processing Monitor</div>
            <div style={{
              fontSize: 'var(--font-size-sm)',
              color: 'var(--cisa-gray)',
              lineHeight: 1.5
            }}>
              Real-time monitoring of document processing pipeline, folder watcher, and live logs
            </div>
          </div>

          {/* Analytics Dashboard */}
          <Link href="/admin/analytics" className="card" style={{ 
            textDecoration: 'none', 
            transition: 'all 0.3s ease',
            border: '1px solid var(--cisa-gray-light)',
            background: 'linear-gradient(135deg, rgba(0, 113, 188, 0.05) 0%, rgba(0, 113, 188, 0.02) 100%)'
          }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-4px)'
              e.currentTarget.style.boxShadow = 'var(--shadow-md)'
              e.currentTarget.style.borderColor = 'var(--cisa-blue)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
              e.currentTarget.style.borderColor = 'var(--cisa-gray-light)'
            }}
          >
            <div style={{ 
              fontSize: 'var(--font-size-xxl)', 
              marginBottom: 'var(--spacing-sm)'
            }}>📈</div>
            <div style={{ 
              fontWeight: 700, 
              color: 'var(--cisa-blue)', 
              marginBottom: 'var(--spacing-xs)',
              fontSize: 'var(--font-size-lg)'
            }}>Analytics Dashboard</div>
            <div style={{ 
              fontSize: 'var(--font-size-sm)', 
              color: 'var(--cisa-gray)',
              lineHeight: 1.5
            }}>
              View learning events metrics, model performance statistics, and approval rates
            </div>
          </Link>

          {/* Learning Metrics Dashboard */}
          <Link href="/admin/learning" className="card" style={{
            textDecoration: 'none', 
            transition: 'all 0.3s ease',
            border: '1px solid var(--cisa-gray-light)',
            background: 'linear-gradient(135deg, rgba(138, 43, 226, 0.05) 0%, rgba(138, 43, 226, 0.02) 100%)'
          }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-4px)'
              e.currentTarget.style.boxShadow = 'var(--shadow-md)'
              e.currentTarget.style.borderColor = '#8a2be2'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
              e.currentTarget.style.borderColor = 'var(--cisa-gray-light)'
            }}
          >
            <div style={{ 
              fontSize: 'var(--font-size-xxl)', 
              marginBottom: 'var(--spacing-sm)'
            }}>🧠</div>
            <div style={{ 
              fontWeight: 700, 
              color: '#8a2be2', 
              marginBottom: 'var(--spacing-xs)',
              fontSize: 'var(--font-size-lg)'
            }}>Learning Metrics</div>
            <div style={{ 
              fontSize: 'var(--font-size-sm)', 
              color: 'var(--cisa-gray)',
              lineHeight: 1.5
            }}>
              Real-time insights: accept/reject rates, confidence thresholds, and learning trends
            </div>
          </Link>

          {/* User Management */}
          <Link href="/admin/users" className="card" style={{ 
            textDecoration: 'none', 
            transition: 'all 0.3s ease',
            border: '1px solid var(--cisa-gray-light)',
            position: 'relative',
            overflow: 'hidden'
          }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-4px)'
              e.currentTarget.style.boxShadow = 'var(--shadow-md)'
              e.currentTarget.style.borderColor = 'var(--cisa-blue)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
              e.currentTarget.style.borderColor = 'var(--cisa-gray-light)'
            }}
          >
            <div style={{ 
              fontSize: 'var(--font-size-xxl)', 
              marginBottom: 'var(--spacing-sm)'
            }}>👥</div>
            <div style={{ 
              fontWeight: 700, 
              color: 'var(--cisa-blue)', 
              marginBottom: 'var(--spacing-xs)',
              fontSize: 'var(--font-size-lg)'
            }}>User Management</div>
            <div style={{ 
              fontSize: 'var(--font-size-sm)', 
              color: 'var(--cisa-gray)'
            }}>Add, activate, and manage user accounts and roles</div>
          </Link>

          {/* Model Analytics */}
          <Link href="/admin/models" className="card" style={{ 
            textDecoration: 'none', 
            transition: 'all 0.3s ease',
            border: '1px solid var(--cisa-gray-light)'
          }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-4px)'
              e.currentTarget.style.boxShadow = 'var(--shadow-md)'
              e.currentTarget.style.borderColor = 'var(--cisa-blue)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
              e.currentTarget.style.borderColor = 'var(--cisa-gray-light)'
            }}
          >
            <div style={{ 
              fontSize: 'var(--font-size-xxl)', 
              marginBottom: 'var(--spacing-sm)'
            }}>📊</div>
            <div style={{ 
              fontWeight: 700, 
              color: 'var(--cisa-blue)', 
              marginBottom: 'var(--spacing-xs)',
              fontSize: 'var(--font-size-lg)'
            }}>Model Analytics</div>
            <div style={{ 
              fontSize: 'var(--font-size-sm)', 
              color: 'var(--cisa-gray)'
            }}>Accept rate, edits, softmatch ratio by model version</div>
          </Link>

          {/* Soft Match Audit */}
          <Link href="/admin/softmatches" className="card" style={{ 
            textDecoration: 'none', 
            transition: 'all 0.3s ease',
            border: '1px solid var(--cisa-gray-light)'
          }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-4px)'
              e.currentTarget.style.boxShadow = 'var(--shadow-md)'
              e.currentTarget.style.borderColor = 'var(--cisa-blue)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
              e.currentTarget.style.borderColor = 'var(--cisa-gray-light)'
            }}
          >
            <div style={{ 
              fontSize: 'var(--font-size-xxl)', 
              marginBottom: 'var(--spacing-sm)'
            }}>🔍</div>
            <div style={{ 
              fontWeight: 700, 
              color: 'var(--cisa-blue)', 
              marginBottom: 'var(--spacing-xs)',
              fontSize: 'var(--font-size-lg)'
            }}>Soft Match Audit</div>
            <div style={{ 
              fontSize: 'var(--font-size-sm)', 
              color: 'var(--cisa-gray)'
            }}>Review and manage near-duplicate detections</div>
          </Link>

        </div>
      </section>

      {/* Recent Soft Matches */}
      <section>
        <h2 style={{ 
          fontSize: 'var(--font-size-xl)', 
          fontWeight: 600, 
          color: 'var(--cisa-blue)', 
          marginBottom: 'var(--spacing-md)'
        }}>
          Recent Activity
        </h2>
        <div className="card" style={{ 
          padding: 0, 
          overflow: 'hidden',
          border: '1px solid var(--cisa-gray-light)'
        }}>
          {loading && !soft.length ? (
            <div style={{ 
              padding: 'var(--spacing-xl)', 
              textAlign: 'center',
              color: 'var(--cisa-gray)'
            }}>
              <div style={{
                display: 'inline-block',
                width: '24px',
                height: '24px',
                border: '3px solid var(--cisa-gray-light)',
                borderTopColor: 'var(--cisa-blue)',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
                marginRight: 'var(--spacing-sm)'
              }}></div>
              Loading recent activity...
            </div>
          ) : soft.length > 0 ? (
            <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
              {soft.map((r, i) => (
                <li 
                  key={i} 
                  style={{
                    padding: 'var(--spacing-md)',
                    borderBottom: i < soft.length - 1 ? '1px solid var(--cisa-gray-light)' : 'none',
                    fontSize: 'var(--font-size-sm)',
                    transition: 'background-color 0.2s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = 'var(--cisa-gray-lighter)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent'
                  }}
                >
                  <div style={{ 
                    color: 'var(--cisa-black)', 
                    marginBottom: 'var(--spacing-xs)',
                    fontWeight: 500,
                    lineHeight: 1.5
                  }}>
                    {r.new_text || r.text || r.title || 'Submission'}
                  </div>
                  <div style={{ 
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--spacing-md)',
                    fontSize: 'var(--font-size-xs)', 
                    color: 'var(--cisa-gray)'
                  }}>
                    {r.similarity && (
                      <span style={{
                        padding: '2px 8px',
                        borderRadius: 'var(--border-radius)',
                        backgroundColor: 'rgba(138, 43, 226, 0.1)',
                        color: '#6f42c1',
                        fontWeight: 600
                      }}>
                        sim {r.similarity.toFixed(3)}
                      </span>
                    )}
                    {r.source_doc && (
                      <span style={{ fontFamily: 'monospace' }}>{r.source_doc}</span>
                    )}
                    {r.created_at && (
                      <span style={{ marginLeft: 'auto' }}>
                        {new Date(r.created_at).toLocaleString('en-US', { timeZone: 'America/New_York', timeZoneName: 'short' })}
                      </span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <div style={{ 
              padding: 'var(--spacing-xl)', 
              textAlign: 'center',
              color: 'var(--cisa-gray)'
            }}>
              <p style={{ margin: 0, fontSize: 'var(--font-size-lg)' }}>
                No recent activity
              </p>
              <p style={{ margin: 'var(--spacing-sm) 0 0 0', fontSize: 'var(--font-size-sm)' }}>
                Activity will appear here as submissions are processed
              </p>
            </div>
          )}
        </div>
      </section>

      <style jsx>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
