'use client';
import { useState, useEffect, useMemo } from 'react';
import SafeHTML from './SafeHTML';
import { fetchWithAuth } from '../lib/fetchWithAuth';

export default function SubmissionReview() {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [stats, setStats] = useState({ total: 0, pending: 0, approved: 0, rejected: 0 });
  const [processingSubmission, setProcessingSubmission] = useState(null);
  const [comments, setComments] = useState('');
  const [mounted, setMounted] = useState(false);
  const [expanded, setExpanded] = useState({});
  const [reprocessing, setReprocessing] = useState(null);

  useEffect(() => {
    setMounted(true);
    loadSubmissions();
  }, []);

  const loadSubmissions = async () => {
    try {
      setLoading(true);
      const response = await fetchWithAuth('/api/admin/submissions');
      const data = await response.json();
      
      if (data.success) {
        setSubmissions(data.allSubmissions || []);
        
        // Calculate stats
        const allSubmissions = data.allSubmissions || [];
        const pendingCount = allSubmissions.filter(s => s.status === 'pending_review').length;
        const approvedCount = allSubmissions.filter(s => s.status === 'approved').length;
        const rejectedCount = allSubmissions.filter(s => s.status === 'rejected').length;
        
        setStats({
          total: allSubmissions.length,
          pending: pendingCount,
          approved: approvedCount,
          rejected: rejectedCount
        });
      } else {
        setError(data.error || 'Failed to load submissions');
      }
    } catch (err) {
      setError('Error loading submissions: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const getSubmissionData = (submission) => {
    return typeof submission.data === 'string' 
      ? JSON.parse(submission.data) 
      : submission.data;
  };

  const getSubmissionSource = (submission) => {
    const data = getSubmissionData(submission);
    return data.source_title || data.source || submission.source || 'Document Submission';
  };

  const getSubmissionDate = (submission) => {
    const data = getSubmissionData(submission);
    return data.parsed_at || data.created_at || submission.created_at;
  };

  const getVulnerabilitiesFromSubmission = (submission) => {
    const data = getSubmissionData(submission);
    
    // Check if this submission has enhanced extraction data
    if (data.enhanced_extraction && Array.isArray(data.enhanced_extraction)) {
      const vulnerabilities = [];
      
      data.enhanced_extraction.forEach(record => {
        if (record.content && Array.isArray(record.content)) {
          record.content.forEach(entry => {
            if (entry.type === 'vulnerability') {
              vulnerabilities.push({
                id: `${submission.id}-${vulnerabilities.length}`,
                vulnerability: entry.text,
                discipline: data.discipline || 'General',
                source: getSubmissionSource(submission),
                associated_ofcs: [],
                submission_id: submission.id,
                submission_status: submission.status,
                submission_date: getSubmissionDate(submission)
              });
            }
          });
        }
      });
      
      // Now find associated OFCs for each vulnerability
      vulnerabilities.forEach(vuln => {
        data.enhanced_extraction.forEach(record => {
          if (record.content && Array.isArray(record.content)) {
            record.content.forEach(entry => {
              if (entry.type === 'ofc') {
                vuln.associated_ofcs.push({
                  id: `${vuln.id}-ofc-${vuln.associated_ofcs.length}`,
                  question_text: entry.text,
                  discipline: data.discipline || 'General',
                  source: getSubmissionSource(submission)
                });
              }
            });
          }
        });
      });
      
      return vulnerabilities;
    }
    
    // Fallback for submissions without enhanced extraction
    if (submission.type === 'vulnerability') {
      const data = getSubmissionData(submission);
      return [{
        id: submission.id,
        vulnerability: data.vulnerability || 'Vulnerability from submission',
        discipline: data.discipline || 'General',
        source: getSubmissionSource(submission),
        associated_ofcs: data.associated_ofcs ? data.associated_ofcs.map((ofc, index) => ({
          id: `${submission.id}-ofc-${index}`,
          question_text: ofc,
          discipline: data.discipline || 'General',
          source: getSubmissionSource(submission)
        })) : [],
        submission_id: submission.id,
        submission_status: submission.status,
        submission_date: getSubmissionDate(submission)
      }];
    }
    
    return [];
  };

  const toggleExpand = (submissionId) => {
    setExpanded(prev => ({ ...prev, [submissionId]: !prev[submissionId] }));
  };

  const reprocessSubmission = async (submissionId) => {
    try {
      setReprocessing(submissionId);
      // process-one works with Supabase submissions, keep using Next.js API
      const response = await fetchWithAuth('/api/documents/process-one', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ submissionId })
      });
      const result = await response.json();
      if (!response.ok || !result.success) {
        alert(`Reprocess failed: ${result.error || response.statusText}`);
      } else {
        alert(`Reprocess started/completed. Extracted: ${result.count ?? 0}`);
        await loadSubmissions();
      }
    } catch (e) {
      alert(`Reprocess error: ${e.message}`);
    } finally {
      setReprocessing(null);
    }
  };

  const vulnerabilities = useMemo(() => {
    const allVulnerabilities = [];
    
    submissions.forEach(submission => {
      const submissionVulnerabilities = getVulnerabilitiesFromSubmission(submission);
      allVulnerabilities.push(...submissionVulnerabilities);
    });
    
    return allVulnerabilities;
  }, [submissions]);

  const approveSubmission = async (submissionId) => {
    try {
      setProcessingSubmission(submissionId);
      const response = await fetchWithAuth(`/api/submissions/${submissionId}/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          approver: 'admin@vofc.gov', // TODO: Get from auth context
          comments: comments
        }),
      });
      const result = await response.json();
      if (result.success) {
        alert('Submission approved!');
        loadSubmissions();
        setComments('');
      } else {
        alert(`Failed to approve: ${result.error}`);
      }
    } catch (err) {
      console.error('Error approving submission:', err);
      alert('Error approving submission.');
    } finally {
      setProcessingSubmission(null);
    }
  };

  const rejectSubmission = async (submissionId) => {
    const reason = prompt('Please provide a reason for rejection:');
    if (!reason) return;

    try {
      setProcessingSubmission(submissionId);
      const response = await fetchWithAuth(`/api/submissions/${submissionId}/reject`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          comments: reason,
          processedBy: 'admin@vofc.gov' // TODO: Get from auth context
        }),
      });
      const result = await response.json();
      if (result.success) {
        alert('Submission rejected!');
        loadSubmissions();
      } else {
        alert(`Failed to reject: ${result.error}`);
      }
    } catch (err) {
      console.error('Error rejecting submission:', err);
      alert('Error rejecting submission.');
    } finally {
      setProcessingSubmission(null);
    }
  };

  const deleteSubmission = async (submissionId) => {
    if (!confirm('Are you sure you want to permanently delete this submission and all its data? This action cannot be undone.')) {
      return;
    }

    try {
      setProcessingSubmission(submissionId);
      const response = await fetchWithAuth(`/api/submissions/${submissionId}/delete`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          reason: 'Manual deletion by admin',
          deletedBy: 'admin@vofc.gov' // TODO: Get from auth context
        }),
      });
      const result = await response.json();
      if (result.success) {
        alert('Submission and all associated data deleted!');
        loadSubmissions();
      } else {
        alert(`Failed to delete: ${result.error}`);
      }
    } catch (err) {
      console.error('Error deleting submission:', err);
      alert('Error deleting submission.');
    } finally {
      setProcessingSubmission(null);
    }
  };

  if (!mounted) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading submissions...</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading submissions...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-600 text-xl mb-4">⚠️ Error</div>
          <p className="text-gray-600">{error}</p>
          <button 
            onClick={loadSubmissions}
            className="btn btn-primary mt-4"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // vulnerabilities is now memoized above

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-blue-900 text-white p-4">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-2xl font-bold">Submission Review</h1>
          <p className="text-blue-200">Review vulnerabilities and OFCs from submitted documents</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6">
        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="card">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-blue-100 text-blue-600">
                <i className="fas fa-file-alt text-xl"></i>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Submissions</p>
                <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-body">
              <div className="flex items-center">
                <div className="p-3 rounded-full bg-yellow-100 text-yellow-600">
                  <i className="fas fa-clock text-xl"></i>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Pending Review</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.pending}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-body">
              <div className="flex items-center">
                <div className="p-3 rounded-full bg-green-100 text-green-600">
                  <i className="fas fa-check text-xl"></i>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Approved</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.approved}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-body">
              <div className="flex items-center">
                <div className="p-3 rounded-full bg-red-100 text-red-600">
                  <i className="fas fa-times text-xl"></i>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Rejected</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.rejected}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Vulnerabilities List */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-xl font-semibold text-gray-900">
              Vulnerabilities from Submissions ({vulnerabilities.length})
            </h2>
            <p className="text-gray-600 mt-1">
              Vulnerabilities extracted from submitted documents with their associated Options for Consideration
            </p>
          </div>

          <div className="card-body">
            {vulnerabilities.length === 0 ? (
              <div className="text-center py-12">
                <div className="text-gray-400 text-6xl mb-4">
                  <i className="fas fa-shield-alt"></i>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">No vulnerabilities found</h3>
                <p className="text-gray-600">No vulnerabilities have been extracted from submissions yet.</p>
              </div>
            ) : (
              <div className="space-y-6">
                {vulnerabilities.map((vulnerability) => (
                  <div key={vulnerability.id} className="border border-gray-200 rounded-lg p-6">
                    {/* Vulnerability Header */}
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <h3 className="text-lg font-semibold text-gray-900">
                            {vulnerability.discipline}
                          </h3>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            vulnerability.submission_status === 'pending_review' 
                              ? 'bg-yellow-100 text-yellow-800'
                              : vulnerability.submission_status === 'approved'
                              ? 'bg-green-100 text-green-800'
                              : 'bg-red-100 text-red-800'
                          }`}>
                            {vulnerability.submission_status?.replace('_', ' ') || 'Unknown'}
                          </span>
                        </div>
                        <p className="text-gray-700 mb-3">{vulnerability.vulnerability}</p>
                        <div className="flex items-center space-x-4 text-sm text-gray-500">
                          <div className="flex items-center">
                            <i className="fas fa-file-alt mr-1"></i>
                            <span>Source: {vulnerability.source}</span>
                          </div>
                          <div className="flex items-center">
                            <i className="fas fa-calendar mr-1"></i>
                            <span>Date: {new Date(vulnerability.submission_date).toLocaleDateString()}</span>
                          </div>
                          <div className="flex items-center">
                            <i className="fas fa-hashtag mr-1"></i>
                            <span>ID: {vulnerability.submission_id.slice(0,8)}</span>
                          </div>
                        </div>
                      </div>
                      <div className="ml-4 flex flex-col gap-2">
                        <button
                          onClick={() => reprocessSubmission(vulnerability.submission_id)}
                          disabled={reprocessing === vulnerability.submission_id}
                          className="btn btn-outline-primary btn-sm"
                          title="Re-run Ollama parsing for this submission"
                        >
                          {reprocessing === vulnerability.submission_id ? 'Reprocessing...' : 'Reprocess'}
                        </button>
                        <button
                          onClick={() => toggleExpand(vulnerability.submission_id)}
                          className="btn btn-outline-secondary btn-sm"
                          title="Show raw submission data and extraction"
                        >
                          {expanded[vulnerability.submission_id] ? 'Hide Data' : 'View Data'}
                        </button>
                      </div>
                    </div>

                    {/* Associated OFCs */}
                    {vulnerability.associated_ofcs && vulnerability.associated_ofcs.length > 0 && (
                      <div className="mt-4">
                        <h4 className="text-md font-medium text-gray-900 mb-3">
                          Associated Options for Consideration ({vulnerability.associated_ofcs.length})
                        </h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {vulnerability.associated_ofcs.map((ofc) => (
                            <div key={ofc.id} className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                              <div className="flex justify-between items-start mb-2">
                                <h5 className="font-medium text-blue-900">{ofc.discipline}</h5>
                                <span className="text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded">
                                  OFC
                                </span>
                              </div>
                              <p className="text-blue-800 text-sm mb-2">{ofc.question_text}</p>
                              <div className="text-xs text-blue-600">
                                <i className="fas fa-file-alt mr-1"></i>
                                Source: {ofc.source}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* No OFCs message */}
                    {(!vulnerability.associated_ofcs || vulnerability.associated_ofcs.length === 0) && (
                      <div className="mt-4 p-3 bg-gray-50 border border-gray-200 rounded-lg">
                        <p className="text-sm text-gray-600">
                          <i className="fas fa-info-circle mr-2"></i>
                          No associated Options for Consideration found for this vulnerability.
                        </p>
                      </div>
                    )}

                    {/* Action Buttons for Pending Submissions */}
                    {vulnerability.submission_status === 'pending_review' && (
                      <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <h5 className="font-medium text-yellow-900 mb-3">Review Actions</h5>
                        <div className="mb-3">
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Comments (optional):
                          </label>
                          <textarea
                            value={comments}
                            onChange={(e) => setComments(e.target.value)}
                            placeholder="Add comments for the submitter..."
                            className="w-full p-2 border border-gray-300 rounded-md text-sm"
                            rows="2"
                          />
                        </div>
                        <div className="flex space-x-3">
                          <button
                            onClick={() => approveSubmission(vulnerability.submission_id)}
                            disabled={processingSubmission === vulnerability.submission_id}
                            className="btn btn-success btn-sm"
                          >
                            {processingSubmission === vulnerability.submission_id ? 'Processing...' : 'Approve'}
                          </button>
                          <button
                            onClick={() => rejectSubmission(vulnerability.submission_id)}
                            disabled={processingSubmission === vulnerability.submission_id}
                            className="btn btn-danger btn-sm"
                          >
                            {processingSubmission === vulnerability.submission_id ? 'Processing...' : 'Reject'}
                          </button>
                          <button
                            onClick={() => deleteSubmission(vulnerability.submission_id)}
                            disabled={processingSubmission === vulnerability.submission_id}
                            className="btn btn-secondary btn-sm"
                          >
                            {processingSubmission === vulnerability.submission_id ? 'Processing...' : 'Delete'}
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Raw Data Panel */}
                    {expanded[vulnerability.submission_id] && (
                      <div className="mt-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
                        <h5 className="font-medium text-gray-900 mb-3">Submission Data</h5>
                        <SubmissionDataView submission={submissions.find(s => s.id === vulnerability.submission_id)} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Refresh Button */}
        <div className="mt-6 flex justify-center">
          <button
            onClick={loadSubmissions}
            className="btn btn-primary"
          >
            <i className="fas fa-sync-alt mr-2"></i>
            Refresh Submissions
          </button>
        </div>
      </div>
    </div>
  );
}

function SubmissionDataView({ submission }) {
  if (!submission) return null;
  const data = typeof submission.data === 'string' ? safeParse(submission.data) : submission.data;
  const pretty = (() => {
    try { return JSON.stringify(data, null, 2); } catch { return String(submission.data); }
  })();
  const hasExtraction = Array.isArray(data?.enhanced_extraction) && data.enhanced_extraction.length > 0;
  const vulnCount = Number(data?.vulnerabilities_count) || 0;
  const ofcCount = Number(data?.options_for_consideration_count) || 0;
  return (
    <div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3 text-sm">
        <div className="p-2 bg-white border rounded">Status: <strong>{submission.status}</strong></div>
        <div className="p-2 bg-white border rounded">Parsed At: <strong>{data?.parsed_at ? new Date(data.parsed_at).toLocaleString() : '—'}</strong></div>
        <div className="p-2 bg-white border rounded">Extraction: <strong>{hasExtraction ? 'Yes' : 'No'}</strong></div>
        <div className="p-2 bg-white border rounded">Vulns: <strong>{vulnCount}</strong></div>
        <div className="p-2 bg-white border rounded">OFCs: <strong>{ofcCount}</strong></div>
        <div className="p-2 bg-white border rounded">Filename: <strong>{data?.document_name || '—'}</strong></div>
      </div>
      <pre className="text-xs bg-white p-3 border rounded overflow-auto" style={{ maxHeight: 300 }}>{pretty}</pre>
    </div>
  );
}

function safeParse(text) {
  try { return JSON.parse(text); } catch { return null; }
}