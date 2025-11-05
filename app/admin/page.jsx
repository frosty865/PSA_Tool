'use client'

import { useEffect, useState, useCallback } from 'react'
import { fetchWithAuth } from '../lib/fetchWithAuth'
import '@/styles/cisa.css'
import Link from 'next/link'

export default function AdminOverviewPage() {
  const [stats, setStats] = useState([])
  const [soft, setSoft] = useState([])
  const [system, setSystem] = useState({ flask: 'checking', ollama: 'checking', supabase: 'checking' })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastRefresh, setLastRefresh] = useState(null)
  const [progress, setProgress] = useState(null)

  // System health checker - uses Next.js API route proxy to avoid CORS issues
  const fetchSystemHealth = useCallback(async () => {
    try {
      // Use Next.js API route proxy instead of calling Flask directly
      // This avoids CORS issues and provides better error handling
      const res = await fetch('/api/system/health', { 
        cache: 'no-store',
        headers: {
          'Accept': 'application/json'
        }
      })
      
      if (!res.ok) {
        throw new Error(`Health check API returned ${res.status}`)
      }
      
      const json = await res.json()
      
      // Handle the response data structure
      if (json.components) {
        setSystem(json.components)
      } else if (json.status === 'error' || json.status === 'timeout') {
        // API route returned an error state
        setSystem({
          flask: json.components?.flask || 'offline',
          ollama: json.components?.ollama || 'unknown',
          supabase: json.components?.supabase || 'unknown'
        })
      } else {
        // Fallback if structure is unexpected
        setSystem({ flask: 'unknown', ollama: 'unknown', supabase: 'unknown' })
      }
    } catch (err) {
      console.error('[System Health] Fetch failed:', err)
      setSystem({ flask: 'offline', ollama: 'unknown', supabase: 'unknown' })
    }
  }, [])

  useEffect(() => {
    let isMounted = true
    fetchSystemHealth()
    const interval = setInterval(() => {
      if (isMounted) fetchSystemHealth()
    }, 15000)
    return () => { isMounted = false; clearInterval(interval) }
  }, [fetchSystemHealth])

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
      case 'online': return { bg: '#e6f6ea', border: '#00a651', text: '#007a3d' }
      case 'offline': return { bg: '#fdecea', border: '#c00', text: '#a00' }
      default: return { bg: '#f5f5f5', border: '#ccc', text: '#666' }
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
            Started: {new Date(progress.timestamp).toLocaleTimeString()}
          </p>
        </div>
      )}

      {/* System Health Summary */}
      <section style={{ marginBottom: 'var(--spacing-xl)' }}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          marginBottom: 'var(--spacing-md)'
        }}>
          <h2 style={{ 
            fontSize: 'var(--font-size-xl)', 
            fontWeight: 600, 
            color: 'var(--cisa-blue)', 
            margin: 0
          }}>
            System Health
          </h2>
          <Link 
            href="/admin/system" 
            style={{ 
              fontSize: 'var(--font-size-sm)', 
              color: 'var(--cisa-blue)',
              textDecoration: 'none'
            }}
          >
            View Details →
          </Link>
        </div>
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', 
          gap: 'var(--spacing-lg)'
        }}>
          {['flask', 'ollama', 'supabase'].map(key => {
            const status = system[key] || 'checking'
            const colors = getSystemStatusColor(status)
            return (
              <div 
                key={key} 
                className="card" 
                style={{
                  backgroundColor: colors.bg,
                  border: `2px solid ${colors.border}`,
                  transition: 'all 0.3s ease',
                  position: 'relative',
                  overflow: 'hidden'
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
                  <div style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    backgroundColor: colors.border,
                    boxShadow: `0 0 8px ${colors.border}`
                  }}></div>
                  <div style={{ 
                    fontWeight: 700, 
                    color: colors.text,
                    fontSize: 'var(--font-size-lg)'
                  }}>
                    {key.charAt(0).toUpperCase() + key.slice(1)} Server
                  </div>
                </div>
                <div style={{ 
                  fontSize: 'var(--font-size-sm)', 
                  color: '#444',
                  fontWeight: 500
                }}>
                  Status: <strong style={{ color: colors.text }}>{status}</strong>
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
                  Last updated: {new Date(s.updated_at).toLocaleString()}
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
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', 
          gap: 'var(--spacing-md)'
        }}>
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
            }}>Add, activate, and manage users</div>
          </Link>

          <Link href="/admin/review" className="card" style={{ 
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
            }}>📋</div>
            <div style={{ 
              fontWeight: 700, 
              color: 'var(--cisa-blue)', 
              marginBottom: 'var(--spacing-xs)',
              fontSize: 'var(--font-size-lg)'
            }}>Review Submissions</div>
            <div style={{ 
              fontSize: 'var(--font-size-sm)', 
              color: 'var(--cisa-gray)'
            }}>Moderate new content</div>
          </Link>

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
            }}>Accept rate, edits, softmatch ratio</div>
          </Link>

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
            }}>Near-duplicate detections</div>
          </Link>

          <Link href="/admin/system" className="card" style={{ 
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
            }}>⚙️</div>
            <div style={{ 
              fontWeight: 700, 
              color: 'var(--cisa-blue)', 
              marginBottom: 'var(--spacing-xs)',
              fontSize: 'var(--font-size-lg)'
            }}>System Health</div>
            <div style={{ 
              fontSize: 'var(--font-size-sm)', 
              color: 'var(--cisa-gray)'
            }}>Backend and Ollama status</div>
          </Link>

          <Link href="/learning" className="card" style={{ 
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
            }}>🧠</div>
            <div style={{ 
              fontWeight: 700, 
              color: 'var(--cisa-blue)', 
              marginBottom: 'var(--spacing-xs)',
              fontSize: 'var(--font-size-lg)'
            }}>Learning Monitor</div>
            <div style={{ 
              fontSize: 'var(--font-size-sm)', 
              color: 'var(--cisa-gray)'
            }}>Continuous learning overview</div>
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
                        {new Date(r.created_at).toLocaleString()}
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
