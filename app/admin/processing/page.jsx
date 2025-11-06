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
  const logEndRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

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
        
        evtSource = new EventSource(streamUrl)
        eventSourceRef.current = evtSource

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
          console.warn('SSE connection error, falling back to polling:', err)
          // Close SSE and fall back to polling
          if (evtSource) {
            evtSource.close()
          }
          setupPolling()
        }
      } catch (error) {
        console.warn('SSE not available, using polling:', error)
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
        <div className="flex justify-center items-center h-full min-h-screen">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading processor status...</p>
          </div>
        </div>
      </RoleGate>
    )
  }

  return (
    <RoleGate requiredRole="admin">
      <div className="p-6 space-y-6" style={{ minHeight: '100vh' }}>
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Auto-Processor Monitor</h1>
            <p className="text-gray-600">
              Real-time monitoring of document processing pipeline and folder watcher
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div
              className="card"
              style={{
                padding: 'var(--spacing-sm) var(--spacing-md)',
                backgroundColor: watcherColors.bg,
                border: `2px solid ${watcherColors.border}`,
                borderRadius: 'var(--border-radius)'
              }}
            >
              <div className="flex items-center gap-2">
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
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Folder Status Card */}
        <div className="card" style={{ padding: 'var(--spacing-lg)' }}>
          <h2 className="text-xl font-semibold text-gray-900 mb-4" style={{ color: 'var(--cisa-blue)' }}>
            Folder Status
          </h2>
          {progress ? (
            <div className="grid md:grid-cols-5 gap-4">
              {Object.entries(progress)
                .filter(([key]) => key !== 'timestamp' && key !== 'status')
                .map(([key, val]) => (
                  <div
                    key={key}
                    className="text-center p-4 rounded-lg"
                    style={{
                      backgroundColor: 'var(--cisa-gray-lighter)',
                      border: '1px solid var(--cisa-gray-light)'
                    }}
                  >
                    <p className="font-semibold capitalize mb-2" style={{ color: 'var(--cisa-gray)' }}>
                      {key.replace('_', ' ')}
                    </p>
                    <div
                      className="inline-block px-4 py-2 rounded-full font-bold text-lg"
                      style={{
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
            <p className="text-gray-500">No progress data available</p>
          )}
          
          {progress?.timestamp && (
            <div className="mt-4 text-sm text-gray-500">
              Last updated: {new Date(progress.timestamp).toLocaleString()}
            </div>
          )}
        </div>

        {/* Live Logs Card */}
        <div className="card" style={{ padding: 'var(--spacing-lg)' }}>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900" style={{ color: 'var(--cisa-blue)' }}>
              Live Logs
            </h2>
            <button
              onClick={() => setLogLines([])}
              className="btn btn-secondary btn-sm"
              style={{ padding: 'var(--spacing-xs) var(--spacing-sm)' }}
            >
              Clear Logs
            </button>
          </div>
          <div
            className="font-mono text-sm overflow-y-auto p-4 rounded"
            style={{
              backgroundColor: '#1a1a1a',
              color: '#00ff00',
              height: '400px',
              fontFamily: 'monospace',
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
          <h2 className="text-xl font-semibold text-gray-900 mb-4" style={{ color: 'var(--cisa-blue)' }}>
            Quick Actions
          </h2>
          <div className="flex gap-4">
            <button
              onClick={() => {
                if (progress) {
                  const fetchProgress = async () => {
                    const res = await fetch('/api/system/progress', { cache: 'no-store' })
                    if (res.ok) {
                      const data = await res.json()
                      setProgress(data)
                    }
                  }
                  fetchProgress()
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
          </div>
        </div>
      </div>
    </RoleGate>
  )
}

