'use client'

import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { fetchWithAuth } from '../../lib/fetchWithAuth'
import RoleGate from '@/components/RoleGate'
import '@/styles/cisa.css'

export default function ProcessingMonitorPage() {
  const router = useRouter()
  const [progress, setProgress] = useState(null)
  // BULLETPROOF: Initialize with heartbeat so we always show something
  const [logLines, setLogLines] = useState([`${new Date().toISOString().replace('T', ' ').substring(0, 19)} | INFO | [MONITOR] Initializing log monitor...`])
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

  // Poll progress.json every 30 seconds
  useEffect(() => {
    const fetchProgress = async () => {
      try {
        const res = await fetch('/api/system/progress', { cache: 'no-store' })
        // Always try to parse JSON, even if status is not OK
        // The route returns 200 with default values on errors for graceful handling
        let data
        try {
          data = await res.json()
        } catch (parseError) {
          // If JSON parsing fails, use default progress data
          data = {
            status: 'unknown',
            message: 'Unable to fetch progress',
            timestamp: new Date().toISOString(),
            incoming: 0,
            processed: 0,
            library: 0,
            errors: 0,
            review: 0,
            watcher_status: 'unknown'
          }
        }
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
        // Only show non-timeout errors
        if (!errorMsg.includes('timeout') && !errorMsg.includes('aborted')) {
          setError(err.message)
        }
      } finally {
        setLoading(false)
      }
    }

    // Force immediate fetch on mount to avoid stale data
    fetchProgress()
    // Also fetch after a short delay to ensure we get latest data
    const immediateRefresh = setTimeout(fetchProgress, 1000)
    const timer = setInterval(fetchProgress, 30000) // Poll every 30 seconds (reduced from 10s to reduce network load)
    
    return () => {
      clearTimeout(immediateRefresh)
      clearInterval(timer)
    }
  }, [])

  // Live log stream (BULLETPROOF polling with automatic retry)
  useEffect(() => {
    let pollInterval = null
    let lastKnownLines = new Set() // Track seen lines to avoid duplicates
    let retryCount = 0
    const MAX_RETRIES = 3
    const POLL_INTERVAL = 3000 // 3 seconds - faster updates
    
    // BULLETPROOF: Always show something, even on errors
    const showConnectionStatus = (status, message) => {
      const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19)
      setLogLines(prev => {
        // Only update if we don't already have a status message
        const hasStatus = prev.some(line => line && line.includes('[MONITOR]'))
        if (!hasStatus || status === 'error') {
          return [`${timestamp} | ${status.toUpperCase()} | [MONITOR] ${message}`]
        }
        return prev
      })
    }
    
    // Initial load of recent logs with retry
    const loadInitialLogs = async (retry = 0) => {
      try {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 10000) // 10 second timeout
        
        const res = await fetch('/api/system/logs?tail=50', { 
          cache: 'no-store',
          signal: controller.signal
        })
        clearTimeout(timeoutId)
        
        // ALWAYS try to parse JSON - backend ALWAYS returns valid JSON
        let data = { lines: [] }
        try {
          data = await res.json()
        } catch (parseError) {
          // Fallback: create valid structure
          data = { lines: [`[ERROR] Failed to parse response: ${parseError.message}`] }
        }
        
        // BULLETPROOF: Backend ALWAYS returns lines array, even if empty
        if (!data.lines || !Array.isArray(data.lines)) {
          data.lines = [`[ERROR] Invalid response from server`]
        }
        
        // Filter out empty lines
        const validLines = data.lines.filter(line => line && typeof line === 'string' && line.trim())
        
        if (validLines.length > 0) {
          setLogLines(validLines)
          // Track initial lines
          validLines.forEach(line => {
            if (line) lastKnownLines.add(line.substring(0, 100)) // Use first 100 chars as hash
          })
          retryCount = 0 // Reset retry on success
        } else {
          // No valid lines - ALWAYS show connection status (don't leave empty)
          const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19)
          setLogLines([`${timestamp} | INFO | [MONITOR] Connected - waiting for log entries...`])
        }
      } catch (err) {
        retryCount++
        const errorMsg = err.message || err.toString() || 'Unknown error'
        
        // Retry with exponential backoff
        if (retryCount < MAX_RETRIES) {
          const delay = Math.min(1000 * Math.pow(2, retryCount), 5000)
          setTimeout(() => loadInitialLogs(retry + 1), delay)
        } else {
          // Max retries reached - ALWAYS show error status (don't leave empty)
          const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19)
          setLogLines([`${timestamp} | ERROR | [MONITOR] Connection failed after ${MAX_RETRIES} retries: ${errorMsg}`])
        }
      }
    }

    // BULLETPROOF polling with automatic error recovery
    const setupPolling = () => {
      let consecutiveErrors = 0
      const MAX_CONSECUTIVE_ERRORS = 5
      
      pollInterval = setInterval(async () => {
        try {
          const controller = new AbortController()
          const timeoutId = setTimeout(() => controller.abort(), 8000) // 8 second timeout
          
          const res = await fetch('/api/system/logs?tail=50', { 
            cache: 'no-store',
            signal: controller.signal
          })
          clearTimeout(timeoutId)
          
          // ALWAYS try to parse JSON - backend ALWAYS returns valid JSON
          let data = { lines: [] }
          try {
            data = await res.json()
          } catch (parseError) {
            consecutiveErrors++
            if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
              showConnectionStatus('error', 'Failed to parse server response')
            }
            return // Skip this poll
          }
          
          // Reset error counter on success
          consecutiveErrors = 0
          
          // BULLETPROOF: Backend ALWAYS returns lines array
          if (!data.lines || !Array.isArray(data.lines)) {
            data.lines = []
          }
          
          // Filter out empty lines
          const validLines = data.lines.filter(line => line && typeof line === 'string' && line.trim())
          
          // BULLETPROOF: Always update, even if no new lines (to show heartbeat/status)
          setLogLines((prev) => {
            // If this is the first poll and we have no previous lines, just set all lines
            if (prev.length === 0 && validLines.length > 0) {
              validLines.forEach(line => {
                if (line) lastKnownLines.add(line.substring(0, 100))
              })
              return validLines
            }
            
            // If we have valid lines, process them
            if (validLines.length > 0) {
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
              
              // No new lines, but keep existing (don't clear)
              return prev
            } else {
              // No valid lines from API - check if we should show heartbeat
              const hasHeartbeat = prev.some(line => line && line.includes('[MONITOR]'))
              if (!hasHeartbeat) {
                // No heartbeat yet - add one
                const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19)
                return [`${timestamp} | INFO | [MONITOR] Connected - waiting for log entries...`]
              }
              // Already have heartbeat, keep it
              return prev
            }
          })
          
          // Handle error status
          if (data.error || data.status === 'error') {
            const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19)
            setLogLines(prev => {
              // Replace any existing status with error
              const filtered = prev.filter(line => !line || !line.includes('[MONITOR]'))
              return [...filtered, `${timestamp} | ERROR | [MONITOR] ${data.message || data.error || 'Unknown error'}`]
            })
          }
        } catch (err) {
          consecutiveErrors++
          const errorMsg = err.message || err.toString() || ''
          
          // Show error status if too many consecutive errors
          if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
            showConnectionStatus('error', `Connection issues (${consecutiveErrors} errors)`)
          }
        }
      }, POLL_INTERVAL)
    }

    // Load initial logs and start polling
    loadInitialLogs()
    // Start polling after initial load completes (with delay for retries)
    setTimeout(setupPolling, 2000)
    
    // Cleanup on unmount
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
        return { bg: '#e6f6ea', border: '#00a651', text: '#007a3d', icon: '[OK]' }
      case 'stopped':
        return { bg: '#fdecea', border: '#c00', text: '#a00', icon: '[STOP]' }
      default:
        return { bg: '#fff9e6', border: '#ffc107', text: '#856404', icon: '[WARN]' }
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
        throw new Error(`Failed to parse server response: ${parseError.message}`)
      }
      
      // Check if response indicates an error
      if (data.status === 'error' || !data.status || (res.status !== 200 && res.status !== 201)) {
        let errorMsg = data.message || data.error || `Control action failed (HTTP ${res.status})`
        
        // Add hint if available
        if (data.hint) {
          errorMsg += `\n\n[HINT] ${data.hint}`
        }
        
        // Add troubleshooting steps if available
        if (data.troubleshooting) {
          errorMsg += `\n\n[TROUBLESHOOTING]\n`
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
      alert(`[OK] ${message}`)
      
      // Refresh progress and watcher status after action (with delay to allow processing)
      setTimeout(async () => {
        try {
          const progressRes = await fetch('/api/system/progress', { cache: 'no-store' })
          let progressData
          try {
            progressData = await progressRes.json()
          } catch {
            // Use default if parsing fails
            progressData = {
              timestamp: new Date().toISOString(),
              incoming: 0,
              processed: 0,
              library: 0,
              errors: 0,
              review: 0,
              watcher_status: 'unknown'
            }
          }
          setProgress(progressData)
          
          // Update watcher status from response
          if (progressData.watcher_status) {
            setWatcherStatus(progressData.watcher_status)
          }
        } catch (err) {
          // Silently handle refresh errors
        }
      }, 2000) // Increased delay for actions that may take time
    } catch (err) {
      // Don't show timeout errors or browser extension errors to user
      const errorMsg = (err.message || err.toString() || '').toLowerCase()
      if (
        !errorMsg.includes('timeout') &&
        !errorMsg.includes('aborted') &&
        !errorMsg.includes('message channel') &&
        !errorMsg.includes('asynchronous response') &&
        !errorMsg.includes('channel closed')
      ) {
        alert(`[ERROR] Error: ${err.message}`)
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
            <button
              onClick={async () => {
                setLoading(true)
                try {
                  const progressRes = await fetch('/api/system/progress', { cache: 'no-store' })
                  let progressData
                  try {
                    progressData = await progressRes.json()
                  } catch {
                    progressData = {
                      timestamp: new Date().toISOString(),
                      incoming: 0,
                      processed: 0,
                      library: 0,
                      errors: 0,
                      review: 0,
                      watcher_status: 'unknown'
                    }
                  }
                  setProgress(progressData)
                  if (progressData.watcher_status) {
                    setWatcherStatus(progressData.watcher_status)
                  }
                } catch (err) {
                  // Silently handle refresh errors
                } finally {
                  setLoading(false)
                }
              }}
              disabled={loading}
              style={{
                padding: 'var(--spacing-sm) var(--spacing-md)',
                backgroundColor: 'var(--cisa-blue)',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--border-radius)',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontWeight: 600,
                fontSize: 'var(--font-size-sm)',
                opacity: loading ? 0.6 : 1
              }}
            >
              {loading ? '[PROCESSING] Refreshing...' : '[REFRESH] Refresh'}
            </button>
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
                .filter(([key]) => {
                  // Only show folder counts, not metadata fields
                  const folderKeys = ['incoming', 'processed', 'library', 'errors', 'review'];
                  return folderKeys.includes(key) && typeof progress[key] === 'number';
                })
                .map(([key, val]) => {
                  const label = progress[`${key}_label`] || key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
                  const description = progress[`${key}_description`] || '';
                  // Color coding based on folder type
                  let bgColor = 'var(--cisa-gray-lighter)';
                  let borderColor = 'var(--cisa-gray-light)';
                  let badgeColor = 'var(--cisa-blue)';
                  
                  if (key === 'incoming') {
                    bgColor = '#FEF3C7';
                    borderColor = '#FDE68A';
                    badgeColor = '#D97706';
                  } else if (key === 'library') {
                    bgColor = '#D1FAE5';
                    borderColor = '#A7F3D0';
                    badgeColor = '#059669';
                  } else if (key === 'errors') {
                    bgColor = '#FEE2E2';
                    borderColor = '#FECACA';
                    badgeColor = '#DC2626';
                  } else if (key === 'processed' || key === 'review') {
                    bgColor = '#DBEAFE';
                    borderColor = '#BFDBFE';
                    badgeColor = '#2563EB';
                  }
                  
                  return (
                    <div
                      key={key}
                      style={{
                        textAlign: 'center',
                        padding: 'var(--spacing-md)',
                        borderRadius: 'var(--border-radius-lg)',
                        backgroundColor: bgColor,
                        border: `1px solid ${borderColor}`
                      }}
                    >
                      <p style={{ 
                        fontWeight: 600, 
                        marginBottom: 'var(--spacing-xs)', 
                        color: 'var(--cisa-gray)',
                        fontSize: 'var(--font-size-sm)'
                      }}>
                        {label}
                      </p>
                      <div
                        style={{
                          display: 'inline-block',
                          padding: 'var(--spacing-sm) var(--spacing-md)',
                          borderRadius: '999px',
                          fontWeight: 700,
                          fontSize: 'var(--font-size-lg)',
                          backgroundColor: badgeColor,
                          color: 'white',
                          marginBottom: description ? 'var(--spacing-xs)' : 0
                        }}
                      >
                        {val}
                      </div>
                      {description && (
                        <p style={{ 
                          fontSize: 'var(--font-size-xs)', 
                          color: 'var(--cisa-gray)',
                          marginTop: 'var(--spacing-xs)',
                          fontStyle: 'italic'
                        }}>
                          {description}
                        </p>
                      )}
                    </div>
                  );
                })}
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
              onClick={async () => {
                if (confirm('Are you sure you want to clear all logs? This will wipe the log file.')) {
                  try {
                    await controlAction('clear_logs')
                    // Clear UI after successful file clear
                    setLogLines([])
                  } catch (error) {
                    alert(`Failed to clear logs: ${error.message}`)
                  }
                }
              }}
              disabled={controlLoading}
              style={{
                padding: 'var(--spacing-xs) var(--spacing-md)',
                backgroundColor: 'var(--cisa-gray)',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--border-radius)',
                cursor: controlLoading ? 'not-allowed' : 'pointer',
                fontWeight: 600,
                fontSize: 'var(--font-size-sm)',
                opacity: controlLoading ? 0.6 : 1
              }}
            >
              {controlLoading ? 'Clearing...' : 'Clear Logs'}
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
            {logLines.map((line, i) => (
              <div key={i} style={{ marginBottom: '2px' }}>
                {line}
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        </div>

        {/* Watcher Controls */}
        <div className="card" style={{ padding: 'var(--spacing-lg)', marginBottom: 'var(--spacing-lg)' }}>
          <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 600, color: 'var(--cisa-blue)', marginBottom: 'var(--spacing-md)' }}>
            Watcher Controls
          </h2>
          <div style={{ display: 'flex', gap: 'var(--spacing-md)', flexWrap: 'wrap', alignItems: 'center' }}>
            <button
              onClick={() => controlAction('start_watcher')}
              disabled={controlLoading || watcherStatus === 'running'}
              style={{
                padding: 'var(--spacing-sm) var(--spacing-md)',
                backgroundColor: watcherStatus === 'running' ? 'var(--cisa-gray)' : '#059669',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--border-radius)',
                cursor: watcherStatus === 'running' || controlLoading ? 'not-allowed' : 'pointer',
                fontWeight: 600,
                fontSize: 'var(--font-size-base)',
                opacity: watcherStatus === 'running' || controlLoading ? 0.6 : 1
              }}
            >
              {controlLoading ? '[PROCESSING] Processing...' : watcherStatus === 'running' ? '[OK] Watcher Running' : '[START] Start Watcher'}
            </button>
            <button
              onClick={() => controlAction('stop_watcher')}
              disabled={controlLoading || watcherStatus === 'stopped'}
              style={{
                padding: 'var(--spacing-sm) var(--spacing-md)',
                backgroundColor: watcherStatus === 'stopped' ? 'var(--cisa-gray)' : '#DC2626',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--border-radius)',
                cursor: watcherStatus === 'stopped' || controlLoading ? 'not-allowed' : 'pointer',
                fontWeight: 600,
                fontSize: 'var(--font-size-base)',
                opacity: watcherStatus === 'stopped' || controlLoading ? 0.6 : 1
              }}
            >
              {controlLoading ? '[PROCESSING] Processing...' : watcherStatus === 'stopped' ? '[STOP] Watcher Stopped' : '[STOP] Stop Watcher'}
            </button>
            <button
              onClick={() => controlAction('process_pending')}
              disabled={controlLoading}
              style={{
                padding: 'var(--spacing-sm) var(--spacing-md)',
                backgroundColor: 'var(--cisa-blue)',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--border-radius)',
                cursor: controlLoading ? 'not-allowed' : 'pointer',
                fontWeight: 600,
                fontSize: 'var(--font-size-base)',
                opacity: controlLoading ? 0.6 : 1
              }}
            >
              {controlLoading ? '[PROCESSING] Processing...' : '[PROCESS] Process Pending Files'}
            </button>
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

