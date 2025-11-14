'use client'

import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { fetchWithAuth } from '../../lib/fetchWithAuth'
import RoleGate from '@/components/RoleGate'
import '@/styles/cisa.css'

export default function ProcessingMonitorPage() {
  const router = useRouter()
  const [progress, setProgress] = useState(null)
  const [logLines, setLogLines] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [watcherStatus, setWatcherStatus] = useState('unknown') // 'unknown' | 'running' | 'stopped'
  const [controlLoading, setControlLoading] = useState(false)
  const logEndRef = useRef(null)
  const eventSourceRef = useRef(null)

  // Global error handler to suppress browser extension errors
  useEffect(() => {
    const handleError = (event) => {
      const errorMessage = event.error?.message || event.message || ''
      if (
        errorMessage.includes('message channel') ||
        errorMessage.includes('asynchronous response') ||
        errorMessage.includes('channel closed')
      ) {
        event.preventDefault() // Suppress browser extension errors
        event.stopPropagation()
        return false
      }
    }
    const handleRejection = (event) => {
      const errorMessage = event.reason?.message || event.reason || ''
      if (
        errorMessage.includes('message channel') ||
        errorMessage.includes('asynchronous response') ||
        errorMessage.includes('channel closed')
      ) {
        event.preventDefault() // Suppress browser extension errors
        event.stopPropagation()
        return false
      }
    }
    
    // Add listeners with capture phase to catch early
    window.addEventListener('error', handleError, true)
    window.addEventListener('unhandledrejection', handleRejection, true)
    
    // Also override console.error to filter these messages
    const originalConsoleError = console.error
    console.error = (...args) => {
      const message = args.join(' ')
      if (
        message.includes('message channel') ||
        message.includes('asynchronous response') ||
        message.includes('channel closed')
      ) {
        return // Suppress console output
      }
      originalConsoleError.apply(console, args)
    }
    
    return () => {
      window.removeEventListener('error', handleError, true)
      window.removeEventListener('unhandledrejection', handleRejection, true)
      console.error = originalConsoleError
    }
  }, [])

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
        
        // Use explicit watcher_status from backend if available, otherwise fall back to timestamp inference
        if (data.watcher_status) {
          setWatcherStatus(data.watcher_status)
        } else if (data.timestamp) {
          // Fallback: Determine watcher status based on timestamp freshness
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
        // Don't show timeout errors or browser extension errors - silently handle
        // Ignore browser extension message channel errors
        const errorMsg = err.message || err.toString() || ''
        if (
          errorMsg.includes('message channel') ||
          errorMsg.includes('asynchronous response') ||
          errorMsg.includes('channel closed')
        ) {
          return // Silently ignore browser extension errors
        }
        console.error('Error fetching progress:', err)
        // Only show non-timeout errors
        if (!errorMsg.includes('timeout') && !errorMsg.includes('aborted')) {
          setError(err.message)
        }
      } finally {
        setLoading(false)
      }
    }

    fetchProgress()
    const timer = setInterval(fetchProgress, 30000) // Poll every 30 seconds (reduced from 10s to reduce network load)
    
    return () => clearInterval(timer)
  }, [])

  // Live log stream (using reliable polling method)
  useEffect(() => {
    let pollInterval = null
    let lastKnownLines = new Set() // Track seen lines to avoid duplicates
    
    // Initial load of recent logs
    const loadInitialLogs = async () => {
      try {
        const res = await fetch('/api/system/logs?tail=50', { cache: 'no-store' })
        if (res.ok) {
          const data = await res.json()
          if (data.lines && Array.isArray(data.lines) && data.lines.length > 0) {
            // Filter out empty lines and create hash set
            const validLines = data.lines.filter(line => line && line.trim())
            setLogLines(validLines)
            // Track initial lines
            validLines.forEach(line => {
              if (line) lastKnownLines.add(line.substring(0, 100)) // Use first 100 chars as hash
            })
          }
        }
      } catch (err) {
        console.error('Error loading initial logs:', err)
      }
    }

    // Polling method - more reliable than SSE through Next.js
    const setupPolling = () => {
      pollInterval = setInterval(async () => {
        try {
          const res = await fetch('/api/system/logs?tail=50', { cache: 'no-store' })
          if (res.ok) {
            const data = await res.json()
            if (data.lines && Array.isArray(data.lines) && data.lines.length > 0) {
              setLogLines((prev) => {
                // Filter out empty lines
                const validLines = data.lines.filter(line => line && line.trim())
                
                // Find new lines by comparing with what we've seen
                const newLines = validLines.filter(line => {
                  const hash = line.substring(0, 100)
                  if (!lastKnownLines.has(hash)) {
                    lastKnownLines.add(hash)
                    return true
                  }
                  return false
                })
                
                // If we have new lines, add them
                if (newLines.length > 0) {
                  const combined = [...prev, ...newLines]
                  // Keep only last 200 lines to prevent memory issues
                  const trimmed = combined.slice(-200)
                  
                  // Also trim the hash set to prevent memory growth
                  if (lastKnownLines.size > 500) {
                    // Rebuild hash set from current lines
                    lastKnownLines.clear()
                    trimmed.forEach(line => {
                      if (line) lastKnownLines.add(line.substring(0, 100))
                    })
                  }
                  
                  return trimmed
                }
                
                // No new lines, return previous state
                return prev
              })
            }
          }
        } catch (err) {
          // Silently handle errors - don't spam console
          const errorMsg = err.message || err.toString() || ''
          if (
            !errorMsg.includes('aborted') &&
            !errorMsg.includes('timeout') &&
            !errorMsg.includes('message channel') &&
            !errorMsg.includes('asynchronous response') &&
            !errorMsg.includes('channel closed')
          ) {
            console.error('Error polling logs:', err)
          }
        }
      }, 5000)  // Poll every 5 seconds (reduced from 1.5s to reduce network load)
    }

    // Load initial logs and start polling
    loadInitialLogs()
    // Small delay before starting polling to let initial load complete
    setTimeout(setupPolling, 500)

    return () => {
      if (pollInterval) {
        clearInterval(pollInterval)
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
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
      // Don't show timeout errors or browser extension errors to user
      const errorMsg = (err.message || err.toString() || '').toLowerCase()
      if (
        !errorMsg.includes('timeout') &&
        !errorMsg.includes('aborted') &&
        !errorMsg.includes('message channel') &&
        !errorMsg.includes('asynchronous response') &&
        !errorMsg.includes('channel closed')
      ) {
        alert(`❌ Error: ${err.message}`)
      }
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
              Last updated: {new Date(progress.timestamp).toLocaleString('en-US', { timeZone: 'America/New_York', timeZoneName: 'short' })}
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
              style={{
                padding: 'var(--spacing-xs) var(--spacing-md)',
                backgroundColor: 'var(--cisa-gray)',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--border-radius)',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: 'var(--font-size-sm)'
              }}
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
              onClick={() => router.push('/admin/review')}
              style={{
                padding: 'var(--spacing-sm) var(--spacing-md)',
                backgroundColor: 'var(--cisa-blue)',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--border-radius)',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: 'var(--font-size-base)'
              }}
            >
              📋 Review Submissions
            </button>
          </div>
        </div>
      </div>
    </RoleGate>
  )
}

