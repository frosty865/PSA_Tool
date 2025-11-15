'use client'

import { useState, useEffect, useMemo } from 'react'
import '@/styles/cisa.css'

export default function SectorsPage() {
  const [sectors, setSectors] = useState([])
  const [subsectorsMap, setSubsectorsMap] = useState({})
  const [expandedSectors, setExpandedSectors] = useState(new Set())
  const [searchTerm, setSearchTerm] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Load sectors
  useEffect(() => {
    const loadSectors = async () => {
      try {
        setLoading(true)
        const response = await fetch('/api/sectors', { cache: 'no-store' })
        if (!response.ok) {
          throw new Error('Failed to load sectors')
        }
        const data = await response.json()
        const sectorsData = data.sectors || []
        
        // Filter to only active sectors, sort by name
        const activeSectors = sectorsData
          .filter(s => s.is_active !== false)
          .sort((a, b) => {
            const nameA = (a.sector_name || a.name || '').toLowerCase()
            const nameB = (b.sector_name || b.name || '').toLowerCase()
            // Put "General" at the end
            if (nameA === 'general') return 1
            if (nameB === 'general') return -1
            return nameA.localeCompare(nameB)
          })
        
        setSectors(activeSectors)
        
        // Load subsectors for each sector
        const subsectors = {}
        for (const sector of activeSectors) {
          try {
            const subsResponse = await fetch(`/api/subsectors?sectorId=${sector.id}`, { cache: 'no-store' })
            if (subsResponse.ok) {
              const subsData = await subsResponse.json()
              subsectors[sector.id] = (subsData.subsectors || [])
                .filter(s => s.is_active !== false)
                .sort((a, b) => (a.name || '').localeCompare(b.name || ''))
            }
          } catch (err) {
            console.warn(`Failed to load subsectors for sector ${sector.id}:`, err)
            subsectors[sector.id] = []
          }
        }
        setSubsectorsMap(subsectors)
        setError(null)
      } catch (err) {
        console.error('Error loading sectors:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    loadSectors()
  }, [])

  // Toggle sector expansion
  const toggleSector = (sectorId) => {
    setExpandedSectors(prev => {
      const newSet = new Set(prev)
      if (newSet.has(sectorId)) {
        newSet.delete(sectorId)
      } else {
        newSet.add(sectorId)
      }
      return newSet
    })
  }

  // Expand/collapse all
  const expandAll = () => {
    setExpandedSectors(new Set(sectors.map(s => s.id)))
  }

  const collapseAll = () => {
    setExpandedSectors(new Set())
  }

  // Filter sectors based on search term
  const filteredSectors = useMemo(() => {
    if (!searchTerm.trim()) {
      return sectors
    }

    const term = searchTerm.toLowerCase()
    return sectors.filter(sector => {
      const sectorName = (sector.sector_name || sector.name || '').toLowerCase()
      const sectorDesc = (sector.description || '').toLowerCase()
      
      // Check if sector matches
      if (sectorName.includes(term) || sectorDesc.includes(term)) {
        return true
      }

      // Check if any subsector matches
      const subsectors = subsectorsMap[sector.id] || []
      return subsectors.some(sub => {
        const subName = (sub.name || '').toLowerCase()
        const subDesc = (sub.description || '').toLowerCase()
        return subName.includes(term) || subDesc.includes(term)
      })
    })
  }, [sectors, subsectorsMap, searchTerm])

  // Calculate statistics
  const stats = useMemo(() => {
    const totalSubsectors = Object.values(subsectorsMap).reduce((sum, subs) => sum + subs.length, 0)
    const dhsSectors = sectors.filter(s => {
      const name = (s.sector_name || s.name || '').toLowerCase()
      return name !== 'general'
    }).length
    
    return {
      totalSectors: sectors.length,
      dhsSectors,
      generalSector: sectors.find(s => (s.sector_name || s.name || '').toLowerCase() === 'general') ? 1 : 0,
      totalSubsectors
    }
  }, [sectors, subsectorsMap])

  if (loading) {
    return (
      <div style={{ padding: 'var(--spacing-xl)', textAlign: 'center' }}>
        <div style={{
          width: '48px',
          height: '48px',
          border: '4px solid var(--cisa-gray-light)',
          borderTop: '4px solid var(--cisa-blue)',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite',
          margin: '0 auto var(--spacing-md)'
        }}></div>
        <p style={{ color: 'var(--cisa-gray)', fontSize: 'var(--font-size-base)' }}>
          Loading sectors and subsectors...
        </p>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: 'var(--spacing-xl)' }}>
        <div className="card" style={{
          padding: 'var(--spacing-lg)',
          backgroundColor: 'var(--cisa-red-light)',
          border: '1px solid var(--cisa-red)',
          color: 'var(--cisa-red-dark)'
        }}>
          <h2 style={{ marginTop: 0 }}>Error Loading Sectors</h2>
          <p>{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div style={{ padding: 'var(--spacing-xl)', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 'var(--spacing-xl)' }}>
        <h1 style={{
          fontSize: 'var(--font-size-xxl)',
          fontWeight: 700,
          color: 'var(--cisa-blue)',
          marginBottom: 'var(--spacing-sm)'
        }}>
          DHS Critical Infrastructure Sectors
        </h1>
        <p style={{
          fontSize: 'var(--font-size-base)',
          color: 'var(--cisa-gray)',
          lineHeight: '1.6',
          marginBottom: 'var(--spacing-md)'
        }}>
          This page displays the Department of Homeland Security (DHS) Critical Infrastructure Sectors 
          and their subsectors. These classifications are used throughout the system to categorize 
          vulnerabilities and options for consideration.
        </p>

        {/* Statistics */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 'var(--spacing-md)',
          marginBottom: 'var(--spacing-lg)'
        }}>
          <div className="card" style={{ padding: 'var(--spacing-md)', textAlign: 'center' }}>
            <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 700, color: 'var(--cisa-blue)' }}>
              {stats.dhsSectors}
            </div>
            <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--cisa-gray)' }}>
              DHS Sectors
            </div>
          </div>
          <div className="card" style={{ padding: 'var(--spacing-md)', textAlign: 'center' }}>
            <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 700, color: 'var(--cisa-blue)' }}>
              {stats.totalSectors}
            </div>
            <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--cisa-gray)' }}>
              Total Sectors
            </div>
          </div>
          <div className="card" style={{ padding: 'var(--spacing-md)', textAlign: 'center' }}>
            <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 700, color: 'var(--cisa-blue)' }}>
              {stats.totalSubsectors}
            </div>
            <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--cisa-gray)' }}>
              Total Subsectors
            </div>
          </div>
        </div>

        {/* Search and Controls */}
        <div className="card" style={{ padding: 'var(--spacing-md)', marginBottom: 'var(--spacing-lg)' }}>
          <div style={{
            display: 'flex',
            gap: 'var(--spacing-md)',
            flexWrap: 'wrap',
            alignItems: 'center'
          }}>
            <div style={{ flex: '1', minWidth: '200px' }}>
              <input
                type="text"
                placeholder="Search sectors or subsectors..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{
                  width: '100%',
                  padding: 'var(--spacing-sm) var(--spacing-md)',
                  border: '1px solid var(--cisa-gray-light)',
                  borderRadius: 'var(--border-radius)',
                  fontSize: 'var(--font-size-base)'
                }}
              />
            </div>
            <button
              onClick={expandAll}
              style={{
                padding: 'var(--spacing-sm) var(--spacing-md)',
                backgroundColor: 'var(--cisa-blue)',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--border-radius)',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: 'var(--font-size-sm)'
              }}
            >
              Expand All
            </button>
            <button
              onClick={collapseAll}
              style={{
                padding: 'var(--spacing-sm) var(--spacing-md)',
                backgroundColor: 'var(--cisa-gray)',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--border-radius)',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: 'var(--font-size-sm)'
              }}
            >
              Collapse All
            </button>
          </div>
        </div>
      </div>

      {/* Sectors List */}
      {filteredSectors.length === 0 ? (
        <div className="card" style={{ padding: 'var(--spacing-lg)', textAlign: 'center' }}>
          <p style={{ color: 'var(--cisa-gray)', fontSize: 'var(--font-size-base)' }}>
            No sectors found matching "{searchTerm}"
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
          {filteredSectors.map(sector => {
            const sectorName = sector.sector_name || sector.name || 'Unknown Sector'
            const sectorDesc = sector.description || ''
            const sectorId = sector.id
            const subsectors = subsectorsMap[sectorId] || []
            const isExpanded = expandedSectors.has(sectorId)
            const isGeneral = sectorName.toLowerCase() === 'general'
            const subsectorCount = subsectors.length

            return (
              <div
                key={sectorId}
                className="card"
                style={{
                  padding: 0,
                  overflow: 'hidden',
                  border: isGeneral ? '2px solid var(--cisa-gray)' : '1px solid var(--cisa-gray-light)'
                }}
              >
                {/* Sector Header */}
                <button
                  onClick={() => toggleSector(sectorId)}
                  style={{
                    width: '100%',
                    padding: 'var(--spacing-lg)',
                    textAlign: 'left',
                    backgroundColor: isGeneral ? 'var(--cisa-gray-lighter)' : 'var(--cisa-blue)',
                    color: isGeneral ? 'var(--cisa-gray-dark)' : 'white',
                    border: 'none',
                    cursor: 'pointer',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    transition: 'background-color 0.2s'
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.backgroundColor = isGeneral 
                      ? 'var(--cisa-gray-light)' 
                      : 'var(--cisa-blue-dark)'
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.backgroundColor = isGeneral 
                      ? 'var(--cisa-gray-lighter)' 
                      : 'var(--cisa-blue)'
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <h2 style={{
                      margin: 0,
                      fontSize: 'var(--font-size-xl)',
                      fontWeight: 600,
                      marginBottom: sectorDesc ? 'var(--spacing-xs)' : 0
                    }}>
                      {sectorName}
                      {isGeneral && (
                        <span style={{
                          marginLeft: 'var(--spacing-sm)',
                          fontSize: 'var(--font-size-sm)',
                          fontWeight: 400,
                          opacity: 0.8
                        }}>
                          (Special Category)
                        </span>
                      )}
                    </h2>
                    {sectorDesc && (
                      <p style={{
                        margin: 0,
                        fontSize: 'var(--font-size-sm)',
                        opacity: isGeneral ? 0.8 : 0.9,
                        fontWeight: 400
                      }}>
                        {sectorDesc}
                      </p>
                    )}
                    <div style={{
                      marginTop: 'var(--spacing-xs)',
                      fontSize: 'var(--font-size-xs)',
                      opacity: 0.8
                    }}>
                      {subsectorCount} {subsectorCount === 1 ? 'subsector' : 'subsectors'}
                    </div>
                  </div>
                  <div style={{
                    fontSize: 'var(--font-size-xl)',
                    fontWeight: 600,
                    marginLeft: 'var(--spacing-md)'
                  }}>
                    {isExpanded ? '▼' : '▶'}
                  </div>
                </button>

                {/* Subsectors List */}
                {isExpanded && (
                  <div style={{
                    padding: 'var(--spacing-md) var(--spacing-lg)',
                    backgroundColor: 'var(--cisa-gray-lighter)',
                    borderTop: '1px solid var(--cisa-gray-light)'
                  }}>
                    {subsectors.length === 0 ? (
                      <p style={{
                        color: 'var(--cisa-gray)',
                        fontSize: 'var(--font-size-sm)',
                        fontStyle: 'italic',
                        margin: 0
                      }}>
                        No subsectors available for this sector.
                      </p>
                    ) : (
                      <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
                        gap: 'var(--spacing-sm)'
                      }}>
                        {subsectors.map(subsector => (
                          <div
                            key={subsector.id}
                            style={{
                              padding: 'var(--spacing-sm) var(--spacing-md)',
                              backgroundColor: 'white',
                              borderRadius: 'var(--border-radius)',
                              border: '1px solid var(--cisa-gray-light)'
                            }}
                          >
                            <div style={{
                              fontWeight: 600,
                              fontSize: 'var(--font-size-sm)',
                              color: 'var(--cisa-blue)',
                              marginBottom: subsector.description ? 'var(--spacing-xs)' : 0
                            }}>
                              {subsector.name}
                            </div>
                            {subsector.description && (
                              <div style={{
                                fontSize: 'var(--font-size-xs)',
                                color: 'var(--cisa-gray)',
                                lineHeight: '1.4'
                              }}>
                                {subsector.description}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

