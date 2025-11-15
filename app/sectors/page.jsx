'use client'

import { useState, useEffect, useMemo } from 'react'
import '@/styles/cisa.css'

// Comprehensive subsector descriptions for educational purposes
const SUBSECTOR_DESCRIPTIONS = {
  // Chemical Sector
  'Chemical Distribution': 'Facilities and systems involved in the storage, transportation, and distribution of chemical products, including warehouses, distribution centers, and transportation networks that move chemicals from manufacturers to end users.',
  'Chemical Manufacturing': 'Industrial facilities that produce chemical products through synthesis, processing, and formulation, including petrochemical plants, specialty chemical manufacturers, and pharmaceutical ingredient production.',
  'Chemical Storage': 'Facilities designed for the safe storage of chemical materials, including bulk storage tanks, warehouses, and specialized containment systems that prevent environmental contamination and ensure worker safety.',
  'Chemical Supply Chain': 'The interconnected network of suppliers, manufacturers, distributors, and logistics providers that ensure the secure and reliable flow of chemical products from raw materials to end users.',
  'Chemical Transportation': 'Systems and infrastructure for moving chemical products safely, including specialized tanker trucks, rail cars, pipelines, and maritime vessels with appropriate safety and security measures.',
  
  // Commercial Facilities
  'Gaming and Entertainment': 'Casinos, gaming facilities, amusement parks, and entertainment venues that host large gatherings and require security measures to protect patrons, employees, and assets.',
  'Lodging': 'Hotels, motels, resorts, and other accommodation facilities that provide temporary housing and services to travelers, requiring security for guests, staff, and property.',
  'Outdoor Events': 'Large-scale outdoor gatherings such as concerts, festivals, sporting events, and public celebrations that require crowd management, security, and emergency response planning.',
  'Public Assembly': 'Venues designed for large public gatherings including convention centers, arenas, stadiums, theaters, and community centers that need security and safety measures.',
  'Real Estate': 'Commercial and residential real estate properties, including office buildings, shopping centers, and mixed-use developments that require physical security and access control.',
  'Religious Facilities': 'Churches, synagogues, mosques, temples, and other places of worship that serve as community gathering spaces and may be targets for security threats.',
  'Retail': 'Shopping malls, retail stores, and commercial establishments open to the public that require security measures to protect customers, employees, and merchandise.',
  'Sports Leagues': 'Professional and amateur sports organizations, leagues, and facilities including stadiums, training facilities, and administrative offices.',
  
  // Communications
  'Broadcasting': 'Television and radio broadcast facilities, networks, and transmission systems that provide news, entertainment, and emergency communications to the public.',
  'Cable': 'Cable television and broadband internet service providers, including network infrastructure, headend facilities, and customer service operations.',
  'Internet Service Providers': 'Companies and organizations that provide internet connectivity services, including fiber optic networks, wireless broadband, and data transmission infrastructure.',
  'Satellite': 'Satellite communications systems including satellite operators, ground stations, and satellite-based services for telecommunications, broadcasting, and data transmission.',
  'Voice over Internet Protocol': 'VoIP service providers and systems that enable voice communications over internet networks, including business and residential VoIP services.',
  'Wireless': 'Cellular networks, mobile communications providers, and wireless infrastructure including cell towers, base stations, and mobile network equipment.',
  'Wireline': 'Traditional landline telephone services and fixed-line telecommunications infrastructure including copper and fiber optic networks.',
  
  // Critical Manufacturing
  'Appliance Manufacturing': 'Facilities that produce household and commercial appliances including refrigerators, washing machines, HVAC systems, and other consumer and industrial equipment.',
  'Component Manufacturing': 'Production of specialized components and parts used in larger systems, including electronic components, mechanical parts, and sub-assemblies for various industries.',
  'Electrical Equipment Manufacturing': 'Facilities producing electrical equipment including transformers, generators, motors, switchgear, and power distribution equipment.',
  'Machinery Manufacturing': 'Production of industrial machinery, manufacturing equipment, construction machinery, and specialized tools used across multiple industries.',
  'Primary Metals Manufacturing': 'Facilities involved in the production of primary metals including steel mills, aluminum smelters, foundries, and metal processing plants.',
  'Transportation Equipment Manufacturing': 'Production of vehicles and transportation equipment including automobiles, aircraft, ships, rail cars, and related components.',
  
  // Dams
  'Flood Control Systems': 'Dams, levees, and water management structures designed to prevent flooding and protect communities, infrastructure, and agricultural land from water damage.',
  'Hydroelectric Power Generation': 'Dams and facilities that generate electricity from flowing water, providing renewable energy and requiring security for power generation infrastructure.',
  'Irrigation Systems': 'Dams, canals, and water distribution systems that provide water for agricultural irrigation, supporting food production and rural economies.',
  'Levees': 'Earthen or concrete structures built along rivers and coastlines to prevent flooding, protecting communities and critical infrastructure from water damage.',
  'Navigation Locks': 'Waterway structures that enable ships and boats to navigate elevation changes in rivers and canals, supporting commercial and recreational transportation.',
  'Water Storage': 'Reservoirs and storage facilities created by dams that hold water for municipal supply, irrigation, industrial use, and environmental purposes.',
  
  // Defense Industrial Base
  'Aerospace': 'Companies and facilities involved in the design, development, and production of aircraft, spacecraft, and related systems for defense and commercial applications.',
  'Ammunition and Explosives': 'Facilities that manufacture, store, and handle ammunition, explosives, and ordnance for military and law enforcement use.',
  'Military Communications': 'Communication systems, equipment, and networks designed for military use including secure communications, command and control systems, and tactical radios.',
  'Military Electronics': 'Electronic systems and components for military applications including radar, sensors, guidance systems, and electronic warfare equipment.',
  'Military Optics': 'Optical systems and equipment for military use including targeting systems, night vision devices, surveillance equipment, and precision optics.',
  'Military Research and Development': 'Research facilities, laboratories, and development centers that create new technologies, weapons systems, and capabilities for defense applications.',
  'Military Software': 'Software systems and applications developed for military use including command and control systems, simulation software, and cybersecurity tools.',
  'Military Vehicles': 'Production of military vehicles including tanks, armored personnel carriers, tactical vehicles, and specialized military transportation equipment.',
  'Missiles and Space Systems': 'Development and production of missiles, rockets, satellites, and space systems for defense, intelligence, and strategic applications.',
  'Radar and Navigation': 'Radar systems, navigation equipment, and positioning systems used for military surveillance, targeting, and navigation purposes.',
  'Ships': 'Naval shipbuilding, maintenance, and support facilities including shipyards, dry docks, and facilities that build and service military vessels.',
  'Weapons': 'Manufacturing of weapons systems including firearms, artillery, and advanced weaponry for military and law enforcement applications.',
  
  // Emergency Services
  'Emergency Management': 'Organizations and systems responsible for coordinating disaster response, emergency planning, and recovery operations at local, state, and federal levels.',
  'Emergency Medical Services': 'Ambulance services, paramedic units, and medical response teams that provide emergency medical care and transportation to healthcare facilities.',
  'Fire and Emergency Services': 'Fire departments, firefighting equipment, and emergency response services that protect lives and property from fires and other emergencies.',
  'Law Enforcement': 'Police departments, sheriff\'s offices, and law enforcement agencies responsible for public safety, crime prevention, and maintaining order.',
  'Public Works': 'Municipal services and infrastructure including water and sewer systems, road maintenance, public buildings, and utilities that support community operations.',
  'Search and Rescue': 'Specialized teams and resources for locating and rescuing people in emergency situations including wilderness, water, and urban search and rescue operations.',
  
  // Energy
  'Coal': 'Coal mining operations, processing facilities, and coal-fired power plants that extract and utilize coal as an energy source for electricity generation.',
  'Electric Power': 'Electricity generation, transmission, and distribution systems including power plants, electrical grids, substations, and power lines that deliver electricity to consumers.',
  'Energy Storage': 'Facilities and systems for storing energy including battery storage, pumped hydro storage, and other technologies that help balance electricity supply and demand.',
  'Natural Gas': 'Natural gas extraction, processing, transportation, and distribution including pipelines, storage facilities, and gas-fired power plants.',
  'Nuclear': 'Nuclear power plants, nuclear fuel processing facilities, and nuclear waste storage sites that generate electricity using nuclear fission.',
  'Petroleum': 'Oil extraction, refining, transportation, and distribution including oil fields, refineries, pipelines, and fuel distribution networks.',
  'Renewable Energy': 'Solar, wind, hydroelectric, geothermal, and other renewable energy facilities that generate electricity from sustainable sources.',
  
  // Financial Services
  'Banking': 'Commercial banks, savings banks, and financial institutions that provide deposit accounts, loans, and other banking services to consumers and businesses.',
  'Credit Unions': 'Member-owned financial cooperatives that provide banking services, loans, and financial products to their members and communities.',
  'Financial Market Utilities': 'Critical infrastructure that supports financial markets including payment systems, clearinghouses, and settlement systems that enable financial transactions.',
  'Insurance': 'Insurance companies and providers that offer life, health, property, and casualty insurance to protect individuals and businesses from financial losses.',
  'Non-Depository Credit Intermediation': 'Financial institutions that provide credit and lending services without accepting deposits, including finance companies and lending institutions.',
  'Savings Associations': 'Financial institutions that accept deposits and provide loans, typically focused on residential mortgage lending and community banking.',
  'Securities and Investments': 'Investment firms, brokerages, asset management companies, and securities exchanges that facilitate investment and trading activities.',
  
  // Food and Agriculture
  'Agricultural Distribution': 'Systems and facilities for distributing agricultural products including food distribution centers, wholesale markets, and supply chain networks.',
  'Agricultural Inputs': 'Production and distribution of agricultural inputs including seeds, fertilizers, pesticides, and equipment needed for farming operations.',
  'Agricultural Processing': 'Facilities that process raw agricultural products into food and other products including grain mills, food processing plants, and packaging facilities.',
  'Agricultural Production': 'Farms, ranches, and agricultural operations that produce crops, livestock, and other agricultural products for food and industrial use.',
  'Food Distribution': 'Warehouses, distribution centers, and logistics networks that move food products from processors to retailers, restaurants, and consumers.',
  'Food Processing': 'Facilities that transform raw agricultural products into finished food products including canning, freezing, packaging, and preparation of food items.',
  'Food Production': 'Manufacturing facilities that produce processed foods, beverages, and food products for commercial distribution and consumption.',
  
  // Government Facilities
  'Correctional Facilities': 'Prisons, jails, and detention centers that house individuals in custody, requiring security measures to protect staff, inmates, and the public.',
  'Educational Facilities': 'Public and private schools, colleges, and universities that provide education and serve as community gathering places requiring security and safety measures.',
  'Election Infrastructure': 'Systems and facilities that support democratic elections including voting equipment, polling places, and election administration offices.',
  'Federal Facilities': 'Buildings and facilities owned or operated by the federal government including federal offices, courthouses, and government service centers.',
  'Local Facilities': 'Municipal buildings, city halls, county offices, and other facilities operated by local governments to provide public services.',
  'State Facilities': 'State government buildings, offices, and facilities that house state agencies and provide services to state residents.',
  'Tribal Facilities': 'Buildings and facilities operated by Native American tribes and tribal governments to provide services to tribal communities.',
  
  // Healthcare and Public Health
  'Ambulatory Care': 'Outpatient healthcare facilities including clinics, urgent care centers, and medical offices that provide non-emergency medical services.',
  'Blood': 'Blood banks, plasma collection centers, and blood processing facilities that collect, test, and distribute blood products for medical use.',
  'Home Healthcare': 'Healthcare services provided in patients\' homes including home health agencies, hospice care, and visiting nurse services.',
  'Hospitals': 'Medical facilities that provide inpatient and emergency medical care, surgery, and specialized medical services to patients.',
  'Laboratories': 'Medical and research laboratories that conduct diagnostic testing, medical research, and analysis of biological samples.',
  'Long-term Care': 'Nursing homes, assisted living facilities, and long-term care centers that provide extended care and support for elderly and disabled individuals.',
  'Medical Devices': 'Manufacturing and distribution of medical equipment and devices including diagnostic equipment, surgical instruments, and patient monitoring systems.',
  'Medical Research': 'Research institutions, laboratories, and facilities that conduct medical research, clinical trials, and development of new treatments and therapies.',
  'Pharmaceuticals': 'Manufacturing, distribution, and research facilities for pharmaceutical products including drug manufacturing plants and pharmaceutical research laboratories.',
  
  // Information Technology
  'Cloud Computing': 'Cloud service providers and infrastructure that deliver computing resources, storage, and software services over the internet to businesses and consumers.',
  'Data Centers': 'Facilities that house computer systems, servers, and networking equipment for storing, processing, and managing digital data and applications.',
  'IT Hardware': 'Manufacturing and distribution of computer hardware including servers, networking equipment, storage devices, and computer components.',
  'IT Services': 'Companies that provide information technology services including system integration, managed services, consulting, and technical support.',
  'IT Software': 'Development, distribution, and support of software applications, operating systems, and software products for business and consumer use.',
  'IT Support Services': 'Technical support, help desk services, and IT maintenance services that help organizations manage and troubleshoot their technology systems.',
  'IT Training': 'Educational and training services that provide IT skills development, certification programs, and technology education for professionals and organizations.',
  
  // Nuclear Reactors, Materials, and Waste
  'Nuclear Fuel Cycle': 'Facilities involved in the nuclear fuel cycle including uranium mining, enrichment, fuel fabrication, and spent fuel processing.',
  'Nuclear Materials': 'Production, handling, and storage of nuclear materials including enriched uranium, plutonium, and other materials used in nuclear applications.',
  'Nuclear Power Plants': 'Commercial nuclear reactors and power generation facilities that produce electricity using nuclear fission, requiring security and safety measures.',
  'Nuclear Security': 'Security systems, personnel, and protocols designed to protect nuclear facilities, materials, and information from theft, sabotage, and terrorism.',
  'Nuclear Waste': 'Storage and disposal facilities for radioactive waste including spent nuclear fuel, low-level waste, and high-level waste storage sites.',
  'Research Reactors': 'Nuclear reactors used for research, education, and medical isotope production rather than commercial power generation.',
  
  // Transportation Systems
  'Aviation': 'Airports, air traffic control systems, airlines, and aviation infrastructure that support commercial and general aviation operations.',
  'Freight Rail': 'Railroad systems and infrastructure dedicated to transporting freight, cargo, and goods including rail lines, freight yards, and intermodal facilities.',
  'Highway Infrastructure': 'Roads, bridges, tunnels, and highway systems that support vehicular transportation including interstate highways and major road networks.',
  'Maritime Transportation': 'Ports, harbors, shipping facilities, and maritime infrastructure that support commercial shipping, cargo handling, and maritime commerce.',
  'Mass Transit': 'Public transportation systems including buses, subways, light rail, and commuter rail that provide transportation services to the public.',
  'Pipeline Systems': 'Oil, natural gas, and other pipeline networks that transport energy products and materials across long distances.',
  'Postal and Shipping': 'Postal services, package delivery companies, and shipping infrastructure that move mail and packages across the country and internationally.',
  'Rail Transportation': 'Passenger and freight rail systems including Amtrak, commuter rail, and freight railroads that provide transportation services.',
  
  // Water and Wastewater Systems
  'Drinking Water': 'Water treatment facilities, distribution systems, and infrastructure that provide safe, clean drinking water to communities and consumers.',
  'Stormwater Management': 'Systems and infrastructure designed to manage stormwater runoff including drainage systems, retention ponds, and flood control measures.',
  'Wastewater Treatment': 'Facilities and systems that treat and process wastewater and sewage before returning it to the environment, protecting public health and water quality.',
  'Water Distribution': 'Pipelines, pumping stations, and infrastructure that deliver treated water from treatment plants to homes, businesses, and other consumers.',
  'Water Treatment': 'Facilities that treat raw water from sources like rivers, lakes, and groundwater to make it safe for drinking and other uses.',
}

// Function to check if a description is generic/non-descriptive
function isGenericDescription(description, subsectorName, sectorName) {
  if (!description) return true
  
  const desc = description.toLowerCase().trim()
  const patterns = [
    /^subsector within the/i,
    /^a subsector within/i,
    /^subsector of/i,
    /^part of the/i,
    /^component of/i,
    /^within the .* sector$/i,
    /^subsector$/i,
    /^subsector \d+$/i
  ]
  
  // Check if description matches generic patterns
  if (patterns.some(pattern => pattern.test(desc))) {
    return true
  }
  
  // Check if description is too short or just repeats the name
  if (desc.length < 30) {
    return true
  }
  
  // Check if it's just the subsector name with minimal text
  const nameWords = subsectorName.toLowerCase().split(/\s+/).filter(w => w.length > 2)
  const descWords = desc.split(/\s+/).filter(w => w.length > 2)
  if (nameWords.length > 0 && descWords.length <= nameWords.length + 3) {
    return true
  }
  
  return false
}

// Function to get a descriptive subsector description
function getSubsectorDescription(subsectorName, sectorName) {
  if (!subsectorName) {
    return `A subsector within the ${sectorName} sector.`
  }
  
  // Normalize the name for matching (trim, remove extra spaces)
  const normalized = subsectorName.trim()
  const lowerName = normalized.toLowerCase()
  
  // First try exact match (case-sensitive)
  if (SUBSECTOR_DESCRIPTIONS[normalized]) {
    return SUBSECTOR_DESCRIPTIONS[normalized]
  }
  
  // Try case-insensitive exact match
  for (const [key, value] of Object.entries(SUBSECTOR_DESCRIPTIONS)) {
    if (key.toLowerCase() === lowerName) {
      return value
    }
  }
  
  // Try partial match - check if subsector name contains key words or vice versa
  // This handles cases where database might have slightly different names
  for (const [key, value] of Object.entries(SUBSECTOR_DESCRIPTIONS)) {
    const keyLower = key.toLowerCase()
    
    // Direct substring match
    if (lowerName.includes(keyLower) || keyLower.includes(lowerName)) {
      // Make sure it's a meaningful match (not just a single word)
      if (keyLower.length > 5 || lowerName.length > 5) {
        return value
      }
    }
    
    // Word-by-word matching for multi-word names
    const keyWords = keyLower.split(/\s+/).filter(w => w.length > 2) // Filter out short words
    const nameWords = lowerName.split(/\s+/).filter(w => w.length > 2)
    
    if (keyWords.length > 1 && nameWords.length > 0) {
      // Count matching words
      const matchingWords = nameWords.filter(word => keyWords.includes(word))
      // If most words match, consider it a match
      if (matchingWords.length >= Math.min(keyWords.length - 1, nameWords.length)) {
        return value
      }
    }
  }
  
  // Fallback: generate a contextual description (improved)
  return `Infrastructure and facilities within the ${sectorName} sector that focus specifically on ${normalized.toLowerCase()}. This subsector represents a specialized area requiring specific security, safety, and operational considerations.`
}

export default function SectorsPage() {
  const [sectors, setSectors] = useState([])
  const [subsectorsMap, setSubsectorsMap] = useState({})
  const [expandedSectors, setExpandedSectors] = useState(new Set())
  const [searchTerm, setSearchTerm] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Global error handler to suppress browser extension errors
  useEffect(() => {
    const handleError = (event) => {
      const errorMessage = event.error?.message || event.message || ''
      if (
        errorMessage.includes('message channel') ||
        errorMessage.includes('asynchronous response') ||
        errorMessage.includes('channel closed')
      ) {
        event.preventDefault()
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
        event.preventDefault()
        event.stopPropagation()
        return false
      }
    }
    
    window.addEventListener('error', handleError, true)
    window.addEventListener('unhandledrejection', handleRejection, true)
    
    return () => {
      window.removeEventListener('error', handleError, true)
      window.removeEventListener('unhandledrejection', handleRejection, true)
    }
  }, [])

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
                <div style={{
                  backgroundColor: isGeneral ? 'var(--cisa-gray-lighter)' : 'var(--cisa-blue)',
                  color: isGeneral ? 'var(--cisa-gray-dark)' : 'white',
                  padding: 'var(--spacing-lg)',
                  borderBottom: sectorDesc ? '1px solid rgba(255,255,255,0.2)' : 'none'
                }}>
                  <button
                    onClick={() => toggleSector(sectorId)}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      backgroundColor: 'transparent',
                      color: 'inherit',
                      border: 'none',
                      cursor: 'pointer',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: 0
                    }}
                  >
                    <div style={{ flex: 1 }}>
                      <h2 style={{
                        margin: 0,
                        fontSize: 'var(--font-size-xl)',
                        fontWeight: 600,
                        marginBottom: 'var(--spacing-xs)'
                      }}>
                        {sectorName}
                        {isGeneral && (
                          <span style={{
                            marginLeft: 'var(--spacing-sm)',
                            fontSize: 'var(--font-size-sm)',
                            fontWeight: 400,
                            opacity: 0.9
                          }}>
                            (Special Category)
                          </span>
                        )}
                      </h2>
                      <div style={{
                        fontSize: 'var(--font-size-sm)',
                        opacity: 0.95,
                        fontWeight: 400
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
                  {sectorDesc && (
                    <div style={{
                      marginTop: 'var(--spacing-md)',
                      paddingTop: 'var(--spacing-md)',
                      borderTop: '1px solid rgba(255,255,255,0.2)',
                      fontSize: 'var(--font-size-base)',
                      lineHeight: '1.6',
                      color: isGeneral ? 'var(--cisa-gray-dark)' : 'rgba(255,255,255,0.95)',
                      fontWeight: 400
                    }}>
                      {sectorDesc}
                    </div>
                  )}
                </div>

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
                        {subsectors.map(subsector => {
                          const subsectorName = subsector.name || 'Unknown Subsector'
                          // Check if database description exists and is not generic
                          const dbDescription = subsector.description?.trim()
                          const useDbDescription = dbDescription && !isGenericDescription(dbDescription, subsectorName, sectorName)
                          
                          // Use our comprehensive mapping if database description is missing or generic
                          const subsectorDesc = useDbDescription 
                            ? dbDescription 
                            : getSubsectorDescription(subsectorName, sectorName)
                          
                          // Debug: Log if we're using fallback (only in development)
                          if (process.env.NODE_ENV === 'development' && !useDbDescription) {
                            console.log(`[Sectors] Looking up description for: "${subsectorName}" in sector "${sectorName}"`)
                            if (dbDescription) {
                              console.log(`[Sectors] Database description is generic, using mapping instead`)
                            }
                            console.log(`[Sectors] Found description:`, subsectorDesc.substring(0, 50) + '...')
                          }
                          
                          return (
                            <div
                              key={subsector.id}
                              style={{
                                padding: 'var(--spacing-md)',
                                backgroundColor: 'white',
                                borderRadius: 'var(--border-radius)',
                                border: '1px solid var(--cisa-gray-light)',
                                boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                                transition: 'box-shadow 0.2s'
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.boxShadow = '0 2px 6px rgba(0,0,0,0.15)'
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)'
                              }}
                            >
                              <div style={{
                                fontWeight: 600,
                                fontSize: 'var(--font-size-base)',
                                color: 'var(--cisa-blue)',
                                marginBottom: 'var(--spacing-sm)'
                              }}>
                                {subsectorName}
                              </div>
                              <div style={{
                                fontSize: 'var(--font-size-sm)',
                                color: 'var(--cisa-gray-dark)',
                                lineHeight: '1.6'
                              }}>
                                {subsectorDesc}
                              </div>
                            </div>
                          )
                        })}
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

