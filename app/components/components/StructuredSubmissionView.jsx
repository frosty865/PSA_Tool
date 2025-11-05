'use client';
import { useState, useEffect } from 'react';

export default function StructuredSubmissionView({ submissionId, onClose }) {
  const [structuredData, setStructuredData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (submissionId) {
      fetchStructuredData();
    }
  }, [submissionId]);

  const fetchStructuredData = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/submissions/structured?submission_id=${submissionId}`);
      const data = await response.json();
      
      if (data.success) {
        setStructuredData(data);
      } else {
        setError(data.error || 'Failed to fetch structured data');
      }
    } catch (err) {
      setError('Error fetching structured data: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 max-w-4xl w-full mx-4">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-3">Loading structured data...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 max-w-4xl w-full mx-4">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-red-600">Error Loading Data</h2>
            <button onClick={onClose} className="text-gray-500 hover:text-gray-700">×</button>
          </div>
          <p className="text-red-600">{error}</p>
        </div>
      </div>
    );
  }

  if (!structuredData) {
    return null;
  }

  const { submission, structured_data, summary } = structuredData;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-6xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-gray-800">Structured Submission Review</h2>
          <button 
            onClick={onClose} 
            className="text-gray-500 hover:text-gray-700 text-2xl font-bold"
          >
            ×
          </button>
        </div>

        {/* Submission Overview */}
        <div className="mb-6 p-4 bg-blue-50 rounded-lg">
          <h3 className="text-lg font-semibold mb-3 text-blue-800">Submission Overview</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="font-medium">Type:</span> {submission.type}
            </div>
            <div>
              <span className="font-medium">Status:</span> 
              <span className={`ml-1 px-2 py-1 rounded text-xs ${
                submission.status === 'pending_review' ? 'bg-yellow-100 text-yellow-800' :
                submission.status === 'approved' ? 'bg-green-100 text-green-800' :
                'bg-red-100 text-red-800'
              }`}>
                {submission.status}
              </span>
            </div>
            <div>
              <span className="font-medium">Submitted:</span> {new Date(submission.created_at).toLocaleDateString()}
            </div>
            <div>
              <span className="font-medium">Submitter:</span> {submission.submitter_email || 'N/A'}
            </div>
          </div>
        </div>

        {/* Summary Statistics */}
        <div className="mb-6 p-4 bg-green-50 rounded-lg">
          <h3 className="text-lg font-semibold mb-3 text-green-800">Parsed Content Summary</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{summary.vulnerability_count}</div>
              <div className="text-gray-600">Vulnerabilities</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{summary.ofc_count}</div>
              <div className="text-gray-600">Options for Consideration</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">{summary.source_count}</div>
              <div className="text-gray-600">Sources</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">{summary.link_count}</div>
              <div className="text-gray-600">Links</div>
            </div>
          </div>
        </div>

        {/* Vulnerabilities with Associated OFCs */}
        {structured_data.vulnerabilities && structured_data.vulnerabilities.length > 0 && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-3 text-red-800">Vulnerabilities Found</h3>
            <div className="space-y-6">
              {structured_data.vulnerabilities.map((vuln, index) => {
                // Find OFCs associated with this vulnerability
                const associatedOFCs = structured_data.options_for_consideration?.filter(
                  ofc => ofc.vulnerability_id === vuln.id
                ) || [];
                
                return (
                  <div key={vuln.id || index} className="border border-red-200 rounded-lg p-4 bg-red-50">
                    {/* Vulnerability */}
                    <div className="mb-4">
                      <div className="flex justify-between items-start mb-2">
                        <h4 className="font-medium text-red-800">Vulnerability #{index + 1}</h4>
                        <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded">
                          {vuln.discipline || 'General'}
                        </span>
                      </div>
                      <p className="text-sm text-gray-700 mb-2">{vuln.vulnerability}</p>
                      <div className="text-xs text-gray-500">
                        <div>Source: {vuln.source || 'N/A'}</div>
                        <div>Associated OFCs: {associatedOFCs.length}</div>
                      </div>
                    </div>
                    
                    {/* Associated OFCs */}
                    {associatedOFCs.length > 0 && (
                      <div className="ml-4 border-l-2 border-red-300 pl-4">
                        <h5 className="text-sm font-medium text-blue-800 mb-2">
                          Options for Consideration ({associatedOFCs.length})
                        </h5>
                        <div className="space-y-2">
                          {associatedOFCs.map((ofc, ofcIndex) => (
                            <div key={ofc.id || ofcIndex} className="bg-blue-50 border border-blue-200 rounded p-3">
                              <p className="text-sm text-gray-700 mb-1">{ofc.option_text}</p>
                              <div className="text-xs text-gray-500">
                                <span>Confidence: {(ofc.confidence_score * 100).toFixed(0)}%</span>
                                {ofc.pattern_matched && (
                                  <span className="ml-2">Pattern: {ofc.pattern_matched}</span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Standalone Options for Consideration (not associated with vulnerabilities) */}
        {(() => {
          const vulnerabilityIds = structured_data.vulnerabilities?.map(v => v.id) || [];
          const standaloneOFCs = structured_data.options_for_consideration?.filter(
            ofc => !ofc.vulnerability_id || !vulnerabilityIds.includes(ofc.vulnerability_id)
          ) || [];
          
          return standaloneOFCs.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold mb-3 text-blue-800">Standalone Options for Consideration</h3>
              <div className="space-y-3">
                {standaloneOFCs.map((ofc, index) => (
                  <div key={ofc.id || index} className="border border-blue-200 rounded-lg p-4 bg-blue-50">
                    <div className="flex justify-between items-start mb-2">
                      <h4 className="font-medium text-blue-800">OFC #{index + 1}</h4>
                      <div className="flex gap-2">
                        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                          {ofc.discipline || 'General'}
                        </span>
                        <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                          Confidence: {Math.round((ofc.confidence_score || 0.8) * 100)}%
                        </span>
                      </div>
                    </div>
                    <p className="text-sm text-gray-700 mb-2">{ofc.option_text}</p>
                    {ofc.context && (
                      <div className="text-xs text-gray-600 mb-2">
                        <strong>Context:</strong> {ofc.context}
                      </div>
                    )}
                    <div className="text-xs text-gray-500">
                      <div>Source: {ofc.source || 'N/A'}</div>
                      {ofc.pattern_matched && (
                        <div>Pattern: {ofc.pattern_matched}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })()}

        {/* Sources */}
        {structured_data.sources && structured_data.sources.length > 0 && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-3 text-purple-800">Sources</h3>
            <div className="space-y-3">
              {structured_data.sources.map((source, index) => (
                <div key={source.id || index} className="border border-purple-200 rounded-lg p-4 bg-purple-50">
                  <div className="flex justify-between items-start mb-2">
                    <h4 className="font-medium text-purple-800">Source #{index + 1}</h4>
                    <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">
                      {source.content_restriction || 'public'}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700 mb-2">{source.source_text}</p>
                  <div className="text-xs text-gray-500">
                    <div>Title: {source.source_title || 'N/A'}</div>
                    <div>URL: {source.source_url || 'N/A'}</div>
                    <div>Reference: {source.reference_number || 'N/A'}</div>
                    {source.author_org && <div>Organization: {source.author_org}</div>}
                    {source.publication_year && <div>Year: {source.publication_year}</div>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Links */}
        {structured_data.vulnerability_ofc_links && structured_data.vulnerability_ofc_links.length > 0 && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-3 text-orange-800">Vulnerability-OFC Links</h3>
            <div className="space-y-2">
              {structured_data.vulnerability_ofc_links.map((link, index) => (
                <div key={link.id || index} className="border border-orange-200 rounded-lg p-3 bg-orange-50">
                  <div className="text-sm text-gray-700">
                    <span className="font-medium">Link #{index + 1}:</span> {link.link_type || 'direct'}
                    {link.confidence_score && (
                      <span className="ml-2 text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded">
                        Confidence: {Math.round(link.confidence_score * 100)}%
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex justify-end gap-3 mt-6 pt-4 border-t">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
          >
            Close
          </button>
          <button
            onClick={() => {
              // TODO: Implement approval action
              console.log('Approve submission:', submissionId);
            }}
            className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
          >
            Approve Submission
          </button>
        </div>
      </div>
    </div>
  );
}
