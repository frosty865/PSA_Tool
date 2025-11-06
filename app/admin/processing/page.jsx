'use client'

import { useEffect, useState, useRef } from 'react'
import { fetchWithAuth } from '../../lib/fetchWithAuth'
import RoleGate from '@/components/RoleGate'
import '@/styles/cisa.css'

export default function ProcessingMonitorPage() {
  const [progress, setProgress] = useState(null)
  const [logLines, setLogLines] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [watcherStatus, setWatcherStatus] = useState('unknown') // 'unknown' | 'running' | 'stopped'
  const [controlLoading, setControlLoading] = useState(false)
  const logEndRef = useRef(null)
  const eventSourceRef = useRef(null)

  // Poll progress.json every 10 seconds
  useEffect(() => {
    const fetchProgress = async () => {
      try {
        const res = await fetch('/api/system/progress', { cache: 'no-store' })
        if (!res.ok) {
          throw new Error(`Failed to fetch progress: ${res.status}`)
        }
        const data = await res.json()
        setProgress(data)
        
        // Determine watcher status based on timestamp freshness
        if (data.timestamp) {
          const timestamp = new Date(data.timestamp)
          const now = new Date()
          const diffSeconds = (now.getTime() - timestamp.getTime()) / 1000
          
          // If timestamp is less than 30 seconds old, watcher is likely running
          if (diffSeconds < 30) {
            setWatcherStatus('running')
          } else if (diffSeconds < 300) {
            setWatcherStatus('unknown')
          } else {
            setWatcherStatus('stopped')
          }
        }
        
        setError(null)
      } catch (err) {
        console.error('Error fetching progress:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchProgress()
    const timer = setInterval(fetchProgress, 10000) // Poll every 10 seconds
    
    return () => clearInterval(timer)
  }, [])

  // Live log stream (Server-Sent Events with polling fallback)
  useEffect(() => {
    let pollInterval = null
    let evtSource = null
    
    // Initial load of recent logs
    const loadInitialLogs = async () => {
      try {
        const res = await fetch('/api/system/logs?tail=50', { cache: 'no-store' })
        if (res.ok) {
          const data = await res.json()
          if (data.lines && data.lines.length > 0) {
            setLogLines(data.lines)
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
        
        console.log('[SSE] Attempting to connect to:', streamUrl)
        
        evtSource = new EventSource(streamUrl)
        eventSourceRef.current = evtSource

        evtSource.onopen = () => {
          console.log('[SSE] Connection opened successfully')
        }

        evtSource.onmessage = (e) => {
          if (e.data) {
            setLogLines((prev) => {
              const newLines = [...prev, e.data]
              // Keep only last 100 lines to prevent memory issues
              return newLines.slice(-100)
            })
          }
        }

        evtSource.onerror = (err) => {
          console.warn('[SSE] Connection error, falling back to polling:', {
            readyState: evtSource?.readyState,
            url: streamUrl,
            error: err
          })
          // Close SSE and fall back to polling
          if (evtSource) {
            evtSource.close()
          }
          setupPolling()
        }
      } catch (error) {
        console.warn('[SSE] Setup failed, using polling:', error)
        setupPolling()
      }
    }

    // Fallback polling method
    const setupPolling = () => {
      pollInterval = setInterval(async () => {
        try {
          const res = await fetch('/api/system/logs?tail=10', { cache: 'no-store' })
          if (res.ok) {
            const data = await res.json()
            if (data.lines && data.lines.length > 0) {
              setLogLines((prev) => {
                // Only add new lines that aren't already in the list
                const existingLastLine = prev[prev.length - 1]
                const newLines = data.lines.filter((line) => line !== existingLastLine)
                const combined = [...prev, ...newLines]
                return combined.slice(-100)
              })
            }
          }
        } catch (err) {
          console.error('Error polling logs:', err)
        }
      }, 5000)
    }

    // Load initial logs and setup streaming
    loadInitialLogs()
    setupSSE()

    return () => {
      if (evtSource) {
        evtSource.close()
      }
      if (pollInterval) {
        clearInterval(pollInterval)
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  // Auto-scroll log to bottom
  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logLines])

  const getWatcherStatusColor = () => {
    switch (watcherStatus) {
      case 'running':
        return { bg: '#e6f6ea', border: '#00a651', text: '#007a3d', icon: '🟢' }
      case 'stopped':
        return { bg: '#fdecea', border: '#c00', text: '#a00', icon: '🔴' }
      default:
        return { bg: '#fff9e6', border: '#ffc107', text: '#856404', icon: '🟡' }
    }
  }

  const watcherColors = getWatcherStatusColor()

  if (loading && !progress) {
    return (
      <RoleGate requiredRole="admin">
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
            <p style={{ marginTop: 'var(--spacing-md)', color: 'var(--cisa-gray)' }}>Loading processor status...</p>
          </div>
        </div>
      </RoleGate>
    )
  }

  // Control action handler
  async function controlAction(action) {
    try {
      setControlLoading(true)
      console.log(`[Control Action] Sending action: ${action}`)
      
      const res = await fetch('/api/system/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action })
      })
      
      // Always try to parse JSON, even if status is not OK
      // The proxy returns 200 with error status in body for graceful handling
      let data
      try {
        data = await res.json()
      } catch (parseError) {
        console.error('[Control Action] Failed to parse response:', parseError)
        throw new Error(`Failed to parse server response: ${parseError.message}`)
      }
      
      console.log('[Control Action] Response:', data)
      
      // Check if response indicates an error
      if (data.status === 'error' || !data.status || (res.status !== 200 && res.status !== 201)) {
        let errorMsg = data.message || data.error || `Control action failed (HTTP ${res.status})`
        
        // Add hint if available
        if (data.hint) {
          errorMsg += `\n\n💡 ${data.hint}`
        }
        
        // Add troubleshooting steps if available
        if (data.troubleshooting) {
          errorMsg += `\n\n🔧 Troubleshooting:\n`
          if (data.troubleshooting.checkTunnel) {
            errorMsg += `   • Check tunnel: ${data.troubleshooting.checkTunnel}\n`
          }
          if (data.troubleshooting.checkFlask) {
            errorMsg += `   • Check Flask: ${data.troubleshooting.checkFlask}\n`
          }
          if (data.troubleshooting.testLocal) {
            errorMsg += `   • Test locally: ${data.troubleshooting.testLocal}\n`
          }
        }
        
        throw new Error(errorMsg)
      }
      
      // Success
      const message = data.message || data.status || 'Action completed'
      alert(`✅ ${message}`)
      
      // Refresh progress after action (with delay to allow processing)
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
      }, 2000) // Increased delay for actions that may take time
    } catch (err) {
      console.error('[Control Action] Error:', err)
      alert(`❌ Error: ${err.message}`)
    } finally {
      setControlLoading(false)
    }
  }

  return (
    <RoleGate requiredRole="admin">
      <div style={{ padding: 'var(--spacing-lg)', minHeight: '100vh' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-lg)' }}>
          <div>
            <h1 style={{ fontSize: 'var(--font-size-xxl)', fontWeight: 700, color: 'var(--cisa-black)', marginBottom: 'var(--spacing-sm)' }}>
              Auto-Processor Monitor
            </h1>
            <p style={{ color: 'var(--cisa-gray)', fontSize: 'var(--font-size-base)' }}>
              Real-time monitoring of document processing pipeline and folder watcher
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)' }}>
            <div
              className="card"
              style={{
                padding: 'var(--spacing-sm) var(--spacing-md)',
                backgroundColor: watcherColors.bg,
                border: `2px solid ${watcherColors.border}`,
                borderRadius: 'var(--border-radius)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)' }}>
                <span style={{ fontSize: '1.2rem' }}>{watcherColors.icon}</span>
                <div>
                  <div style={{ fontSize: 'var(--font-size-xs)', color: watcherColors.text, fontWeight: 600 }}>
                    Watcher Status
                  </div>
                  <div style={{ fontSize: 'var(--font-size-sm)', color: watcherColors.text, fontWeight: 700 }}>
                    {watcherStatus === 'running' ? 'Running' : watcherStatus === 'stopped' ? 'Stopped' : 'Unknown'}
                  </div>
                </div>
              </div>
            </div>
          </div>
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
          </div>
        )}

        {/* Folder Status Card */}
        <div className="card" style={{ padding: 'var(--spacing-lg)', marginBottom: 'var(--spacing-lg)' }}>
          <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 600, color: 'var(--cisa-blue)', marginBottom: 'var(--spacing-md)' }}>
            Folder Status
          </h2>
          {progress ? (
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
              gap: 'var(--spacing-md)'
            }}>
              {Object.entries(progress)
                .filter(([key]) => key !== 'timestamp' && key !== 'status')
                .map(([key, val]) => (
                  <div
                    key={key}
                    style={{
                      textAlign: 'center',
                      padding: 'var(--spacing-md)',
                      borderRadius: 'var(--border-radius-lg)',
                      backgroundColor: 'var(--cisa-gray-lighter)',
                      border: '1px solid var(--cisa-gray-light)'
                    }}
                  >
                    <p style={{ fontWeight: 600, textTransform: 'capitalize', marginBottom: 'var(--spacing-sm)', color: 'var(--cisa-gray)' }}>
                      {key.replace('_', ' ')}
                    </p>
                    <div
                      style={{
                        display: 'inline-block',
                        padding: 'var(--spacing-sm) var(--spacing-md)',
                        borderRadius: '999px',
                        fontWeight: 700,
                        fontSize: 'var(--font-size-lg)',
                        backgroundColor: 'var(--cisa-blue)',
                        color: 'white'
                      }}
                    >
                      {val}
                    </div>
                  </div>
                ))}
            </div>
          ) : (
            <p style={{ color: 'var(--cisa-gray)' }}>No progress data available</p>
          )}
          
          {progress?.timestamp && (
            <div style={{ marginTop: 'var(--spacing-md)', fontSize: 'var(--font-size-sm)', color: 'var(--cisa-gray)' }}>
              Last updated: {new Date(progress.timestamp).toLocaleString()}
            </div>
          )}
        </div>

        {/* Live Logs Card */}
        <div className="card" style={{ padding: 'var(--spacing-lg)', marginBottom: 'var(--spacing-lg)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-md)' }}>
            <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 600, color: 'var(--cisa-blue)' }}>
              Live Logs
            </h2>
            <button
              onClick={() => setLogLines([])}
              className="btn btn-secondary btn-sm"
            >
              Clear Logs
            </button>
          </div>
          <div
            style={{
              fontFamily: 'monospace',
              fontSize: 'var(--font-size-sm)',
              overflowY: 'auto',
              padding: 'var(--spacing-md)',
              borderRadius: 'var(--border-radius)',
              backgroundColor: '#1a1a1a',
              color: '#00ff00',
              height: '400px',
              lineHeight: '1.5'
            }}
          >
            {logLines.length === 0 ? (
              <div style={{ color: '#888' }}>Waiting for log entries...</div>
            ) : (
              logLines.map((line, i) => (
                <div key={i} style={{ marginBottom: '2px' }}>
                  {line}
                </div>
              ))
            )}
            <div ref={logEndRef} />
          </div>
        </div>

        {/* Quick Actions */}
        <div className="card" style={{ padding: 'var(--spacing-lg)' }}>
          <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 600, color: 'var(--cisa-blue)', marginBottom: 'var(--spacing-md)' }}>
            Quick Actions
          </h2>
          <div style={{ display: 'flex', gap: 'var(--spacing-md)', flexWrap: 'wrap' }}>
            <button
              onClick={async () => {
                try {
                  const res = await fetch('/api/system/progress', { cache: 'no-store' })
                  if (res.ok) {
                    const data = await res.json()
                    setProgress(data)
                  }
                } catch (err) {
                  console.error('Error refreshing:', err)
                  alert(`❌ Error refreshing: ${err.message}`)
                }
              }}
              className="btn btn-primary"
            >
              🔄 Refresh Status
            </button>
            <button
              onClick={() => setLogLines([])}
              className="btn btn-secondary"
            >
              🗑️ Clear Logs
            </button>
            <button
              onClick={() => controlAction('process_existing')}
              className="btn btn-success"
              disabled={controlLoading}
            >
              {controlLoading ? '⏳ Processing...' : '⚡ Process Existing Files'}
            </button>
            <button
              onClick={() => controlAction('sync_review')}
              className="btn btn-info"
              disabled={controlLoading}
            >
              🔄 Sync Review
            </button>
            <button
              onClick={() => controlAction('start_watcher')}
              className="btn btn-success"
              disabled={controlLoading}
            >
              ▶️ Start Watcher
            </button>
            <button
              onClick={() => controlAction('stop_watcher')}
              className="btn btn-warning"
              disabled={controlLoading}
            >
              ⏹️ Stop Watcher
            </button>
            <button
              onClick={() => {
                if (confirm('Clear all files from the errors folder?')) {
                  controlAction('clear_errors')
                }
              }}
              className="btn btn-danger"
              disabled={controlLoading}
            >
              🗑️ Clear Errors
            </button>
          </div>
        </div>
      </div>
    </RoleGate>
  )
}

