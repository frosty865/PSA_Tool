'use client'

import { useEffect, useState } from 'react'
import { fetchWithAuth } from '../../lib/fetchWithAuth'
import RoleGate from '@/components/RoleGate'
import '@/styles/cisa.css'

export default function ReviewSubmissionsPage() {
  const [submissions, setSubmissions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [vulnDuplicates, setVulnDuplicates] = useState({}) // Map of vuln index -> duplicate info
  const [ofcDuplicates, setOfcDuplicates] = useState({}) // Map of ofc index -> duplicate info
  const [checkingDuplicates, setCheckingDuplicates] = useState(false)

  useEffect(() => {
    loadSubmissions()
    const interval = setInterval(loadSubmissions, 30000)
    return () => clearInterval(interval)
  }, [])

  // Check for duplicates when submissions load
  useEffect(() => {
    if (submissions.length > 0) {
      checkDuplicates()
    }
  }, [submissions])

  const checkDuplicates = async () => {
    setCheckingDuplicates(true)
    try {
      // Collect all vulnerabilities and OFCs from all submissions
      const allVulns = []
      const allOfcs = []
      
      submissions.forEach((submission, subIdx) => {
        let data = {}
        try {
          if (submission.data) {
            data = typeof submission.data === 'string' ? JSON.parse(submission.data) : submission.data
          }
        } catch {}
        
        const vulns = Array.isArray(data.vulnerabilities) ? data.vulnerabilities : []
        const ofcs = Array.isArray(data.ofcs) ? data.ofcs : []
        
        vulns.forEach((v, vIdx) => {
          allVulns.push({ submission_idx: subIdx, vuln_idx: vIdx, ...v })
        })
        
        ofcs.forEach((o, oIdx) => {
          allOfcs.push({ submission_idx: subIdx, ofc_idx: oIdx, ...o })
        })
      })
      
      if (allVulns.length === 0 && allOfcs.length === 0) {
        setCheckingDuplicates(false)
        return
      }
      
      const res = await fetchWithAuth('/api/admin/check-duplicates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vulnerabilities: allVulns.map(v => ({ title: v.title || v.vulnerability, description: v.description })),
          ofcs: allOfcs.map(o => ({ title: o.title || o.option, description: o.description }))
        })
      })
      
      if (res.ok) {
        const result = await res.json()
        // Map duplicates back to submission/vuln indices
        const vulnDupMap = {}
        result.duplicates.vulnerabilities.forEach((dup, idx) => {
          if (dup.is_duplicate && allVulns[idx]) {
            const key = `${allVulns[idx].submission_idx}-${allVulns[idx].vuln_idx}`
            vulnDupMap[key] = dup
          }
        })
        
        const ofcDupMap = {}
        result.duplicates.ofcs.forEach((dup, idx) => {
          if (dup.is_duplicate && allOfcs[idx]) {
            const key = `${allOfcs[idx].submission_idx}-${allOfcs[idx].ofc_idx}`
            ofcDupMap[key] = dup
          }
        })
        
        setVulnDuplicates(vulnDupMap)
        setOfcDuplicates(ofcDupMap)
      }
    } catch (e) {
      console.error('Error checking duplicates:', e)
    } finally {
      setCheckingDuplicates(false)
    }
  }

  const loadSubmissions = async () => {
    try {
      setError(null)
      const res = await fetchWithAuth('/api/admin/submissions?status=pending_review', {
        cache: 'no-store'
      })
      
      // Log response status for debugging
      if (!res.ok) {
        const errorText = await res.text()
        const errorData = await res.json().catch(() => ({ error: `HTTP ${res.status}` }))
        console.error(`[Admin Review] API error: ${res.status}`, errorText.substring(0, 200))
        
        if (res.status === 401) {
          throw new Error('Authentication failed. Please sign in again.')
        } else if (res.status === 403) {
          throw new Error('Access denied. Admin role required.')
        } else {
          throw new Error(errorData.error || `HTTP ${res.status}: Server error`)
        }
      }
      
      const data = await res.json()
      // Handle both response formats: direct array or {success, submissions, allSubmissions}
      const submissionsList = Array.isArray(data) 
        ? data 
        : (data.submissions || data.allSubmissions || [])
      setSubmissions(submissionsList)
      setError(null)
    } catch (e) {
      setError(e.message)
      console.error('[Admin Review] Error loading submissions:', e)
    } finally {
      setLoading(false)
    }
  }

  const handleApprove = async (submissionId) => {
    if (!confirm('Approve this submission? This will:\n- Add data to production tables\n- Feed the learning algorithm\n- Mark as approved')) {
      return
    }
    
    try {
      const res = await fetchWithAuth(`/api/submissions/${submissionId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'approve' })
      })
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ error: 'Failed to approve' }))
        throw new Error(errorData.error || 'Failed to approve')
      }
      await loadSubmissions()
      alert('✅ Submission approved! Data moved to production and learning algorithm notified.')
    } catch (e) {
      alert('❌ Error approving submission: ' + e.message)
    }
  }

  const handleReject = async (submissionId, reason) => {
    const rejectionReason = reason || prompt('Reason for rejection (optional):')
    if (rejectionReason === null && !reason) return // User cancelled prompt
    
    if (!confirm(`Reject this submission?\nReason: ${rejectionReason || 'None provided'}\n\nThis will mark the submission as rejected and remove it from the review queue.`)) {
      return
    }
    
    try {
      const res = await fetchWithAuth(`/api/submissions/${submissionId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          action: 'reject',
          comments: rejectionReason || 'Rejected by admin' 
        })
      })
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ error: 'Failed to reject' }))
        throw new Error(errorData.error || 'Failed to reject')
      }
      await loadSubmissions()
      alert('✅ Submission rejected and removed from review queue.')
    } catch (e) {
      alert('❌ Error rejecting submission: ' + e.message)
    }
  }

  return (
    <RoleGate>
      <div className="space-y-4">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Review Submissions</h1>
          <p className="text-gray-600 mt-2">Review vulnerabilities and their associated OFCs. Approve to feed learning algorithm and move to production.</p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            Error: {error}
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading submissions...</p>
          </div>
        ) : submissions.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <p className="text-gray-500 text-lg">No pending submissions to review</p>
          </div>
        ) : (
          <div className="space-y-6">
            {submissions.map((submission) => {
              // Parse submission data once for the entire component
              let data = {};
              try {
                if (submission.data) {
                  data = typeof submission.data === 'string' 
                    ? JSON.parse(submission.data) 
                    : submission.data;
                }
              } catch (parseError) {
                console.error('Error parsing submission data:', parseError, submission.id);
                data = {};
              }

              // Debug: Log the data structure
              console.log('🔍 Submission data structure:', {
                id: submission.id,
                hasVulns: !!data.vulnerabilities,
                hasOfcs: !!data.ofcs,
                vulnCount: Array.isArray(data.vulnerabilities) ? data.vulnerabilities.length : (data.vulnerabilities_count || 0),
                ofcCount: Array.isArray(data.ofcs) ? data.ofcs.length : (data.ofcs_count || 0),
                dataKeys: Object.keys(data),
                dataType: typeof data,
                fullData: data // Log full data for debugging
              });
              
              // Extract vulnerabilities - handle multiple possible structures
              let vulnerabilities = [];
              if (Array.isArray(data.vulnerabilities)) {
                vulnerabilities = data.vulnerabilities;
              } else if (data.vulnerabilities && typeof data.vulnerabilities === 'object') {
                // If it's an object, try to convert to array
                vulnerabilities = Object.values(data.vulnerabilities);
              }

              // Extract OFCs - handle multiple possible structures
              let ofcs = [];
              if (Array.isArray(data.ofcs)) {
                ofcs = data.ofcs;
              } else if (data.ofcs && typeof data.ofcs === 'object') {
                // If it's an object, try to convert to array
                ofcs = Object.values(data.ofcs);
              } else if (Array.isArray(data.options_for_consideration)) {
                // Alternative field name
                ofcs = data.options_for_consideration;
              }

              // Also check if OFCs are nested within vulnerabilities
              if (vulnerabilities.length > 0 && ofcs.length === 0) {
                vulnerabilities.forEach(vuln => {
                  if (vuln.options_for_consideration && Array.isArray(vuln.options_for_consideration)) {
                    vuln.options_for_consideration.forEach(ofc => {
                      ofcs.push({
                        ...ofc,
                        linked_vulnerability: vuln.id || vuln.title || vuln.vulnerability
                      });
                    });
                  }
                });
              }

              // Extract sources/references
              let sources = [];
              if (Array.isArray(data.sources)) {
                sources = data.sources;
              } else if (data.sources && typeof data.sources === 'object') {
                sources = Object.values(data.sources);
              } else if (data.links && Array.isArray(data.links)) {
                // Sometimes sources are in links array
                sources = data.links.filter(link => link.source || link.source_title || link.source_url);
              }

              const hasData = vulnerabilities.length > 0 || ofcs.length > 0 || sources.length > 0;
              // Only show "Load Data" if we have counts but no actual data (indicates old submission or missing data)
              // New submissions should already have full data stored
              const needsDataLoad = !hasData && 
                ((data.vulnerabilities_count > 0) || (data.ofcs_count > 0)) &&
                (data.vulnerabilities_count > 0 || data.ofcs_count > 0);

              console.log('Extracted data:', {
                vulnerabilities: vulnerabilities.length,
                ofcs: ofcs.length,
                needsDataLoad,
                reason: needsDataLoad ? 'Has counts but no full data - likely old submission' : 'Full data present or no data at all'
              });

              // Group OFCs by their linked vulnerability
              // First, try to match by ID, then by title/text matching
              const ofcsByVuln = {};
              ofcs.forEach(ofc => {
                let vulnId = 'unlinked';
                
                // Try direct ID match
                if (ofc.linked_vulnerability) {
                  const matchedVuln = vulnerabilities.find(v => 
                    v.id === ofc.linked_vulnerability || 
                    v.title === ofc.linked_vulnerability ||
                    v.vulnerability === ofc.linked_vulnerability
                  );
                  if (matchedVuln) {
                    vulnId = matchedVuln.id || matchedVuln.title || matchedVuln.vulnerability || 'unlinked';
                  }
                }
                
                // If still unlinked, try matching by other fields
                if (vulnId === 'unlinked' && (ofc.vulnerability_id || ofc.vuln_id)) {
                  const matchId = ofc.vulnerability_id || ofc.vuln_id;
                  const matchedVuln = vulnerabilities.find(v => 
                    v.id === matchId || 
                    v.title === matchId ||
                    v.vulnerability === matchId
                  );
                  if (matchedVuln) {
                    vulnId = matchedVuln.id || matchedVuln.title || matchedVuln.vulnerability || 'unlinked';
                  }
                }
                
                if (!ofcsByVuln[vulnId]) {
                  ofcsByVuln[vulnId] = [];
                }
                ofcsByVuln[vulnId].push(ofc);
              });

              return (
              <div key={submission.id} className="bg-white rounded-lg shadow-lg border border-gray-200">
                {/* Header */}
                <div className="bg-gradient-to-r from-blue-50 to-gray-50 px-6 py-4 border-b border-gray-200">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="text-xl font-bold text-gray-900 mb-2">
                        Submission: {submission.id.slice(0, 8)}...
                      </h3>
                      <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm text-gray-600">
                        <div>
                          <span className="font-medium">Document:</span> {data?.document_name || 'Unknown'}
                        </div>
                        <div>
                          <span className="font-medium">Created:</span> {new Date(submission.created_at).toLocaleString()}
                        </div>
                        <div>
                          <span className="font-medium">Type:</span> <span className="capitalize">{submission.type}</span>
                        </div>
                        <div>
                          <span className="font-medium">Status:</span> <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs font-medium">Pending Review</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      {needsDataLoad && (
                        <button
                          onClick={async () => {
                            if (!confirm('This submission only has metadata counts but not the full data. Load from JSON file?')) {
                              return;
                            }
                            try {
                              const res = await fetchWithAuth(`/api/admin/submissions/${submission.id}/update-data`, {
                                method: 'POST'
                              });
                              if (res.ok) {
                                const result = await res.json();
                                alert(`✅ Loaded ${result.vulnerabilities || 0} vulnerabilities and ${result.ofcs || 0} OFCs from JSON file!`);
                                loadSubmissions();
                              } else {
                                const error = await res.json();
                                alert('❌ Error: ' + (error.error || 'Failed to load data') + '\n\n' + (error.message || '') + '\n' + (error.note || ''));
                              }
                            } catch (e) {
                              alert('❌ Error: ' + e.message);
                            }
                          }}
                          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium text-sm"
                          title="This submission was created before we started storing full data. Click to load from JSON file."
                        >
                          📥 Load Data (Legacy)
                        </button>
                      )}
                      <button
                        onClick={() => handleApprove(submission.id)}
                        className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-semibold shadow-md"
                        title="Approve submission - moves to production and feeds learning algorithm"
                      >
                        ✅ Approve
                      </button>
                      <button
                        onClick={() => handleReject(submission.id)}
                        className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-semibold shadow-md"
                        title="Reject submission - marks as rejected and removes from queue"
                      >
                        ❌ Reject
                      </button>
                    </div>
                  </div>
                </div>

                {/* Content */}
                <div className="p-6">
                  {/* Summary Stats */}
                  <div className="mb-6 grid grid-cols-4 gap-4">
                    <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                      <div className="text-sm text-blue-600 font-medium mb-1">Vulnerabilities</div>
                      <div className="text-2xl font-bold text-blue-900">{vulnerabilities.length || data?.vulnerabilities_count || 0}</div>
                    </div>
                    <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
                      <div className="text-sm text-purple-600 font-medium mb-1">Options for Consideration</div>
                      <div className="text-2xl font-bold text-purple-900">{ofcs.length || data?.ofcs_count || 0}</div>
                    </div>
                    <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                      <div className="text-sm text-green-600 font-medium mb-1">Linked OFCs</div>
                      <div className="text-2xl font-bold text-green-900">{Object.keys(ofcsByVuln).filter(k => k !== 'unlinked').length}</div>
                    </div>
                    <div className="bg-amber-50 p-4 rounded-lg border border-amber-200">
                      <div className="text-sm text-amber-600 font-medium mb-1">Reference Sources</div>
                      <div className="text-2xl font-bold text-amber-900">{sources.length || 0}</div>
                    </div>
                  </div>

                  {/* Warning if data needs loading (only for legacy submissions) */}
                  {needsDataLoad && (
                    <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                      <p className="text-sm text-yellow-800 font-medium mb-1">
                        ⚠️ Legacy Submission Detected
                      </p>
                      <p className="text-xs text-yellow-700">
                        This submission was created before we started storing full extraction data in the database. 
                        The submission has {data.vulnerabilities_count || 0} vulnerabilities and {data.ofcs_count || 0} OFCs according to metadata, 
                        but the full details are stored in the JSON file. Click "Load Data (Legacy)" above to fetch the complete data.
                      </p>
                    </div>
                  )}

                  {/* Debug info */}
                  {process.env.NODE_ENV === 'development' && (
                    <div className="mb-4 p-3 bg-gray-100 rounded text-xs font-mono">
                      <strong>Debug:</strong> Vulnerabilities={vulnerabilities.length}, OFCs={ofcs.length}, 
                      DataKeys={Object.keys(data).join(', ')}, 
                      HasVulns={!!data.vulnerabilities ? 'yes' : 'no'},
                      HasOfcs={!!data.ofcs ? 'yes' : 'no'}
                    </div>
                  )}

                  {/* Vulnerabilities with their OFCs */}
                  {vulnerabilities && vulnerabilities.length > 0 ? (
                    <div className="space-y-4">
                      <h4 className="text-lg font-semibold text-gray-900 border-b border-gray-200 pb-2">
                        Vulnerabilities and Associated OFCs ({vulnerabilities.length} total)
                      </h4>
                      <div className="mb-2 text-xs text-gray-500">
                        Showing {vulnerabilities.length} vulnerability/vulnerabilities with their associated options for consideration
                      </div>
                      <div className="space-y-6 max-h-[600px] overflow-y-auto">
                        {vulnerabilities.map((vuln, idx) => {
                          // Try multiple ways to match vulnerability ID
                          const vulnId = vuln.id || vuln.title || vuln.vulnerability || `vuln-${idx}`;
                          const vulnKey = vuln.id || vuln.title || vuln.vulnerability || `vuln-${idx}`;
                          
                          // Find OFCs linked to this vulnerability by multiple methods
                          const linkedOfcs = [
                            ...(ofcsByVuln[vulnId] || []),
                            ...(ofcsByVuln[vulnKey] || []),
                            ...(ofcsByVuln[vuln.id] || []),
                            ...(ofcsByVuln[vuln.title] || []),
                            ...(ofcsByVuln[vuln.vulnerability] || [])
                          ];
                          
                          // Remove duplicates
                          const uniqueLinkedOfcs = linkedOfcs.filter((ofc, index, self) =>
                            index === self.findIndex(o => 
                              (o.id && o.id === ofc.id) || 
                              (o.title && o.title === ofc.title) ||
                              (o.option && o.option === ofc.option)
                            )
                          );
                          
                          return (
                            <div key={vulnId} className="border border-gray-300 rounded-lg p-4 bg-gray-50 hover:bg-gray-100 transition-colors">
                              {/* Vulnerability Header */}
                              <div className="mb-3 pb-3 border-b border-gray-300">
                                <div className="flex items-start justify-between">
                                  <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-1">
                                      <span className="px-2 py-1 bg-red-100 text-red-800 rounded text-xs font-semibold">
                                        VULNERABILITY #{idx + 1}
                                      </span>
                                      {vuln.category && (
                                        <span className="px-2 py-1 bg-gray-200 text-gray-700 rounded text-xs">
                                          {vuln.category}
                                        </span>
                                      )}
                                      {vuln.severity && (
                                        <span className="px-2 py-1 bg-orange-100 text-orange-800 rounded text-xs">
                                          {vuln.severity}
                                        </span>
                                      )}
                                    </div>
                                    {/* Assessment Question */}
                                    {vuln.question ? (
                                      <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                                        <div className="text-xs font-semibold text-blue-700 mb-1 uppercase tracking-wide">Assessment Question</div>
                                        <p className="text-sm font-medium text-blue-900">{vuln.question}</p>
                                      </div>
                                    ) : (
                                      <div className="mb-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
                                        ⚠️ Missing assessment question
                                      </div>
                                    )}
                                    {/* Vulnerability Statement (Answer) */}
                                    <h5 className="text-base font-bold text-gray-900 mt-2">
                                      {vuln.title || vuln.vulnerability || 'Untitled Vulnerability'}
                                    </h5>
                                    <p className="text-xs text-gray-500 italic mt-1">
                                      (Vulnerability Statement - Answer to the question)
                                    </p>
                                    {/* Structured What and So What */}
                                    {(vuln.what || vuln.so_what) ? (
                                      <div className="mt-3 space-y-2">
                                        {vuln.what && (
                                          <div className="p-2 bg-yellow-50 border border-yellow-200 rounded">
                                            <div className="text-xs font-semibold text-yellow-800 mb-1">WHAT:</div>
                                            <p className="text-sm text-gray-700">{vuln.what}</p>
                                          </div>
                                        )}
                                        {vuln.so_what && (
                                          <div className="p-2 bg-orange-50 border border-orange-200 rounded">
                                            <div className="text-xs font-semibold text-orange-800 mb-1">SO WHAT:</div>
                                            <p className="text-sm text-gray-700">{vuln.so_what}</p>
                                          </div>
                                        )}
                                      </div>
                                    ) : vuln.description ? (
                                      <p className="text-sm text-gray-600 mt-2">{vuln.description}</p>
                                    ) : null}
                                    {/* Sector, Subsector, Discipline metadata - Always show */}
                                    <div className="mt-3 flex flex-wrap gap-2">
                                      <span className={`px-2 py-1 rounded text-xs font-semibold ${
                                        vuln.sector 
                                          ? 'bg-purple-100 text-purple-800' 
                                          : 'bg-gray-100 text-gray-500 italic'
                                      }`}>
                                        Sector: {vuln.sector || 'Not specified'}
                                      </span>
                                      <span className={`px-2 py-1 rounded text-xs font-semibold ${
                                        vuln.subsector 
                                          ? 'bg-indigo-100 text-indigo-800' 
                                          : 'bg-gray-100 text-gray-500 italic'
                                      }`}>
                                        Subsector: {vuln.subsector || 'Not specified'}
                                      </span>
                                      <span className={`px-2 py-1 rounded text-xs font-semibold ${
                                        vuln.discipline 
                                          ? 'bg-teal-100 text-teal-800' 
                                          : 'bg-gray-100 text-gray-500 italic'
                                      }`}>
                                        Discipline: {vuln.discipline || 'Not specified'}
                                      </span>
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <div className="text-xs text-gray-500">
                                      {uniqueLinkedOfcs.length} OFC{uniqueLinkedOfcs.length !== 1 ? 's' : ''}
                                    </div>
                                  </div>
                                </div>
                              </div>
                              
                              {/* Duplicate Warning */}
                              {(() => {
                                const vulnKey = `${submissions.findIndex(s => s.id === submission.id)}-${idx}`
                                const isDuplicate = vulnDuplicates[vulnKey]
                                if (isDuplicate) {
                                  return (
                                    <div className="mb-3 p-3 bg-red-100 border border-red-300 rounded-lg">
                                      <div className="flex items-center gap-2 mb-1">
                                        <span className="px-2 py-1 bg-red-600 text-white rounded text-xs font-bold">
                                          DUPLICATE
                                        </span>
                                        <span className="text-xs text-red-800 font-medium">
                                          This vulnerability already exists in the database
                                        </span>
                                      </div>
                                      <div className="text-xs text-red-700 mt-1">
                                        Similar to: {isDuplicate.existing_vuln?.title || 'Existing vulnerability'}
                                        {(isDuplicate.similarity * 100).toFixed(0)}% similarity
                                      </div>
                                      <div className="text-xs text-red-600 mt-2 italic">
                                        This will be automatically skipped if approved.
                                      </div>
                                    </div>
                                  )
                                }
                                return null
                              })()}

                              {/* Action Buttons for this vulnerability */}
                              <div className="flex justify-end gap-2 mt-3 pt-3 border-t border-gray-300">
                                <button
                                  onClick={async () => {
                                    if (!confirm(`Approve this vulnerability?\n\n"${vuln.title || vuln.vulnerability}"\n\nThis will check for duplicates and only add if unique.`)) {
                                      return
                                    }
                                    try {
                                      const res = await fetchWithAuth(`/api/submissions/${submission.id}/approve-vulnerability`, {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({
                                          action: 'approve',
                                          vulnerability: vuln,
                                          linkedOfcs: uniqueLinkedOfcs
                                        })
                                      })
                                      if (!res.ok) {
                                        const errorData = await res.json().catch(() => ({ error: 'Failed to approve' }))
                                        throw new Error(errorData.error || 'Failed to approve')
                                      }
                                      const result = await res.json()
                                      if (result.duplicate) {
                                        alert(`⚠️ DUPLICATE: This vulnerability already exists in the database. It has been skipped.`)
                                      } else {
                                        alert(`✅ Vulnerability approved!\n${result.ofcs_inserted || 0} OFCs added\n${result.ofcs_duplicates || 0} duplicate OFCs skipped`)
                                      }
                                      await loadSubmissions()
                                    } catch (e) {
                                      alert('❌ Error: ' + e.message)
                                    }
                                  }}
                                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium text-sm"
                                >
                                  ✅ Approve
                                </button>
                                <button
                                  onClick={async () => {
                                    const reason = prompt('Rejection reason (optional):')
                                    if (reason === null) return
                                    try {
                                      const res = await fetchWithAuth(`/api/submissions/${submission.id}/approve-vulnerability`, {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({
                                          action: 'reject',
                                          vulnerability: vuln
                                        })
                                      })
                                      if (!res.ok) {
                                        throw new Error('Failed to reject')
                                      }
                                      alert('✅ Vulnerability rejected')
                                      await loadSubmissions()
                                    } catch (e) {
                                      alert('❌ Error: ' + e.message)
                                    }
                                  }}
                                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium text-sm"
                                >
                                  ❌ Reject
                                </button>
                              </div>

                              {/* Associated OFCs */}
                              {uniqueLinkedOfcs.length > 0 ? (
                                <div className="ml-4 pl-4 border-l-2 border-blue-400">
                                  <div className="text-xs font-semibold text-blue-700 mb-2 uppercase tracking-wide">
                                    Options for Consideration ({uniqueLinkedOfcs.length})
                                  </div>
                                  <div className="space-y-2">
                                    {uniqueLinkedOfcs.map((ofc, ofcIdx) => (
                                      <div key={ofc.id || `ofc-${idx}-${ofcIdx}`} className="bg-white rounded p-3 border border-blue-200 shadow-sm">
                                        <div className="font-medium text-sm text-gray-900">
                                          {ofc.title || ofc.option || ofc.name || 'Untitled OFC'}
                                        </div>
                                        {ofc.description && (
                                          <div className="text-xs text-gray-600 mt-1">{ofc.description}</div>
                                        )}
                                        {!ofc.title && !ofc.option && typeof ofc === 'string' && (
                                          <div className="text-xs text-gray-600 mt-1">{ofc}</div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              ) : (
                                <div className="ml-4 pl-4 border-l-2 border-gray-300">
                                  <div className="text-xs text-gray-400 italic">No OFCs linked to this vulnerability</div>
                                  {ofcs.length > 0 && (
                                    <div className="text-xs text-yellow-600 mt-1">
                                      (Note: {ofcs.length} OFC{ofcs.length !== 1 ? 's' : ''} found but not linked to this vulnerability)
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : vulnerabilities.length === 0 && ofcs.length > 0 ? (
                    <div className="p-6 bg-gray-50 rounded-lg">
                      <h4 className="text-lg font-semibold text-gray-900 mb-3">
                        Options for Consideration (Not Linked to Vulnerabilities)
                      </h4>
                      <div className="space-y-2 max-h-96 overflow-y-auto">
                        {ofcs.map((ofc, idx) => (
                          <div key={ofc.id || `ofc-${idx}`} className="bg-white rounded p-3 border border-purple-200">
                            <div className="font-medium text-sm text-gray-900">
                              {ofc.title || ofc.option || ofc.name || 'Untitled OFC'}
                            </div>
                            {ofc.description && (
                              <div className="text-xs text-gray-600 mt-1">{ofc.description}</div>
                            )}
                            <div className="text-xs text-purple-600 mt-1 italic">
                              ⚠️ Not linked to any vulnerability
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="p-6 bg-gray-50 rounded-lg text-center text-gray-500">
                      {needsDataLoad 
                        ? 'Click "Load Data" to view vulnerabilities and OFCs'
                        : 'No vulnerabilities or OFCs extracted from this submission'}
                      {vulnerabilities.length === 0 && ofcs.length === 0 && (
                        <div className="mt-2 text-xs text-gray-400">
                          Check console logs for data structure details
                        </div>
                      )}
                    </div>
                  )}

                  {/* Unlinked OFCs */}
                  {ofcsByVuln['unlinked'] && ofcsByVuln['unlinked'].length > 0 && (
                    <div className="mt-6 pt-6 border-t border-gray-300">
                      <h4 className="text-lg font-semibold text-gray-900 mb-3">
                        Unlinked Options for Consideration ({ofcsByVuln['unlinked'].length})
                      </h4>
                      <div className="space-y-2 max-h-96 overflow-y-auto">
                        {ofcsByVuln['unlinked'].map((ofc, idx) => (
                          <div key={ofc.id || `unlinked-${idx}`} className="bg-yellow-50 border border-yellow-200 rounded p-3">
                            <div className="font-medium text-sm text-gray-900">
                              {ofc.title || ofc.option || 'Untitled OFC'}
                            </div>
                            {ofc.description && (
                              <div className="text-xs text-gray-600 mt-1">{ofc.description}</div>
                            )}
                            <div className="text-xs text-yellow-700 mt-1 italic">
                              ⚠️ Not linked to any vulnerability
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Reference Sources */}
                  {sources && sources.length > 0 && (
                    <div className="mt-6 pt-6 border-t border-gray-300">
                      <h4 className="text-lg font-semibold text-gray-900 mb-4">
                        📚 Reference Sources ({sources.length})
                      </h4>
                      <div className="space-y-3 max-h-96 overflow-y-auto">
                        {sources.map((source, idx) => (
                          <div key={source.id || `source-${idx}`} className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1">
                                {/* Source Title */}
                                {source.source_title && (
                                  <div className="font-semibold text-sm text-gray-900 mb-1">
                                    {source.source_title}
                                  </div>
                                )}
                                
                                {/* Source Text/Description */}
                                {source.source_text && (
                                  <div className="text-sm text-gray-700 mb-2">
                                    {source.source_text}
                                  </div>
                                )}
                                
                                {/* Source URL */}
                                {source.source_url && (
                                  <div className="mt-2">
                                    <a 
                                      href={source.source_url} 
                                      target="_blank" 
                                      rel="noopener noreferrer"
                                      className="text-xs text-blue-600 hover:text-blue-800 underline break-all"
                                    >
                                      🔗 {source.source_url}
                                    </a>
                                  </div>
                                )}
                                
                                {/* Fallback for different field names */}
                                {!source.source_title && !source.source_text && !source.source_url && (
                                  <div className="text-sm text-gray-700">
                                    {source.title || source.text || source.url || source.source || JSON.stringify(source)}
                                  </div>
                                )}
                              </div>
                              <div className="text-xs text-amber-700 bg-amber-100 px-2 py-1 rounded">
                                Source #{idx + 1}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Raw Data (collapsible) */}
                  <details className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
                    <summary className="font-medium text-gray-900 cursor-pointer hover:text-blue-600">
                      📋 View Raw Submission Data
                    </summary>
                    <pre className="text-xs text-gray-700 overflow-x-auto mt-3 max-h-96 overflow-y-auto">
                      {JSON.stringify(data, null, 2)}
                    </pre>
                  </details>
                </div>
              </div>
              );
            })}
          </div>
        )}
      </div>
    </RoleGate>
  )
}
