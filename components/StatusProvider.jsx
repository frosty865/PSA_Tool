'use client'

import { createContext, useContext, useState, useEffect, useCallback } from 'react'

// Status context
const StatusContext = createContext({
  // System health
  health: null,
  healthLoading: true,
  
  // Processing progress
  progress: null,
  progressLoading: true,
  
  // Processing monitoring
  monitoring: null,
  monitoringLoading: true,
  
  // System events
  events: [],
  eventsLoading: true,
  
  // Learning stats
  learningStats: [],
  learningStatsLoading: true,
  
  // Model info
  modelInfo: null,
  modelInfoLoading: true,
  
  // Refresh functions
  refreshHealth: () => {},
  refreshProgress: () => {},
  refreshMonitoring: () => {},
  refreshEvents: () => {},
  refreshLearningStats: () => {},
  refreshModelInfo: () => {},
  refreshAll: () => {},
  
  // Last refresh timestamps
  lastRefresh: {}
})

export const useStatus = () => useContext(StatusContext)

export default function StatusProvider({ children }) {
  // State for all status indicators
  const [health, setHealth] = useState(null)
  const [healthLoading, setHealthLoading] = useState(true)
  
  const [progress, setProgress] = useState(null)
  const [progressLoading, setProgressLoading] = useState(true)
  
  const [monitoring, setMonitoring] = useState(null)
  const [monitoringLoading, setMonitoringLoading] = useState(true)
  
  const [events, setEvents] = useState([])
  const [eventsLoading, setEventsLoading] = useState(true)
  
  const [learningStats, setLearningStats] = useState([])
  const [learningStatsLoading, setLearningStatsLoading] = useState(true)
  
  const [modelInfo, setModelInfo] = useState(null)
  const [modelInfoLoading, setModelInfoLoading] = useState(true)
  
  const [lastRefresh, setLastRefresh] = useState({})

  // Fetch system health
  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch('/api/system/health', { 
        cache: 'no-store',
        headers: { 'Accept': 'application/json' }
      })
      
      if (res.ok) {
        const json = await res.json()
        if (json.components) {
          // Normalize health status
          const normalizedHealth = {
            ...json,
            components: {
              ...json.components,
              flask: json.components.flask === 'ok' || json.components.flask === 'online' ? 'ok' : 'offline',
              ollama: json.components.ollama === 'ok' || json.components.ollama === 'online' ? 'ok' : 'offline',
              supabase: json.components.supabase === 'ok' || json.components.supabase === 'online' ? 'ok' : 'offline',
            }
          }
          setHealth(normalizedHealth)
        } else {
          setHealth(json)
        }
        setLastRefresh(prev => ({ ...prev, health: new Date() }))
      }
    } catch (err) {
      // Silently handle errors - don't break the app
      setHealth(prev => prev || { components: { flask: 'unknown', ollama: 'unknown', supabase: 'unknown' } })
    } finally {
      setHealthLoading(false)
    }
  }, [])

  // Fetch processing progress
  const fetchProgress = useCallback(async () => {
    try {
      const timestamp = Date.now()
      const res = await fetch(`/api/system/progress?t=${timestamp}`, { cache: 'no-store' })
      
      if (res.ok) {
        const data = await res.json()
        setProgress(data)
        setLastRefresh(prev => ({ ...prev, progress: new Date() }))
      }
    } catch (err) {
      // Silently handle errors
      setProgress(prev => prev || {
        status: 'unknown',
        message: 'Unable to fetch progress',
        timestamp: new Date().toISOString(),
        incoming: 0,
        processed: 0,
        library: 0,
        errors: 0,
        review: 0
      })
    } finally {
      setProgressLoading(false)
    }
  }, [])

  // Fetch processing monitoring
  const fetchMonitoring = useCallback(async () => {
    try {
      const timestamp = Date.now()
      const res = await fetch(`/api/monitor/processing?t=${timestamp}`, { cache: 'no-store' })
      
      if (res.ok) {
        const data = await res.json()
        setMonitoring(data.monitoring || null)
        setLastRefresh(prev => ({ ...prev, monitoring: new Date() }))
      }
    } catch (err) {
      // Silently handle errors - keep existing data
    } finally {
      setMonitoringLoading(false)
    }
  }, [])

  // Fetch system events
  const fetchEvents = useCallback(async () => {
    try {
      const res = await fetch('/api/system/events', { cache: 'no-store' })
      
      if (res.ok) {
        const data = await res.json()
        setEvents(Array.isArray(data) ? data : [])
        setLastRefresh(prev => ({ ...prev, events: new Date() }))
      }
    } catch (err) {
      // Silently handle errors - keep existing data
    } finally {
      setEventsLoading(false)
    }
  }, [])

  // Fetch learning stats
  const fetchLearningStats = useCallback(async () => {
    try {
      const res = await fetch('/api/learning/stats?limit=50', { cache: 'no-store' })
      
      if (res.ok) {
        const data = await res.json()
        const statsArray = Array.isArray(data) ? data : (data.stats || [])
        setLearningStats(statsArray)
        setLastRefresh(prev => ({ ...prev, learningStats: new Date() }))
      }
    } catch (err) {
      // Silently handle errors - keep existing data
    } finally {
      setLearningStatsLoading(false)
    }
  }, [])

  // Fetch model info
  const fetchModelInfo = useCallback(async () => {
    try {
      const res = await fetch('/api/models/info', { cache: 'no-store' })
      
      if (res.ok) {
        const data = await res.json()
        setModelInfo(data)
        setLastRefresh(prev => ({ ...prev, modelInfo: new Date() }))
      }
    } catch (err) {
      // Silently handle errors - keep existing data
    } finally {
      setModelInfoLoading(false)
    }
  }, [])

  // Refresh all status indicators
  const refreshAll = useCallback(() => {
    fetchHealth()
    fetchProgress()
    fetchMonitoring()
    fetchEvents()
    fetchLearningStats()
    fetchModelInfo()
  }, [fetchHealth, fetchProgress, fetchMonitoring, fetchEvents, fetchLearningStats, fetchModelInfo])

  // Initial load - fetch all status indicators in parallel
  useEffect(() => {
    // Fetch all status indicators immediately on mount
    Promise.all([
      fetchHealth(),
      fetchProgress(),
      fetchMonitoring(),
      fetchEvents(),
      fetchLearningStats(),
      fetchModelInfo()
    ]).catch(() => {
      // Errors are handled individually in each fetch function
    })
  }, []) // Only run once on mount

  // Periodic refresh - refresh all status indicators every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      refreshAll()
    }, 30000) // 30 seconds

    return () => clearInterval(interval)
  }, [refreshAll])

  const value = {
    // State
    health,
    healthLoading,
    progress,
    progressLoading,
    monitoring,
    monitoringLoading,
    events,
    eventsLoading,
    learningStats,
    learningStatsLoading,
    modelInfo,
    modelInfoLoading,
    lastRefresh,
    
    // Refresh functions
    refreshHealth: fetchHealth,
    refreshProgress: fetchProgress,
    refreshMonitoring: fetchMonitoring,
    refreshEvents: fetchEvents,
    refreshLearningStats: fetchLearningStats,
    refreshModelInfo: fetchModelInfo,
    refreshAll
  }

  return (
    <StatusContext.Provider value={value}>
      {children}
    </StatusContext.Provider>
  )
}

