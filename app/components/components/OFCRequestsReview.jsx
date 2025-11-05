'use client';
import { useState, useEffect } from 'react';
import SafeHTML from './SafeHTML';
import { fetchWithAuth } from '../lib/fetchWithAuth';

export default function OFCRequestsReview() {
  const [ofcRequests, setOFCRequests] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [stats, setStats] = useState({ 
    total: 0, 
    pending: 0, 
    approved: 0, 
    rejected: 0, 
    implemented: 0 
  });
  const [processingRequest, setProcessingRequest] = useState(null);
  const [supervisorNotes, setSupervisorNotes] = useState('');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    loadOFCRequests();
  }, []);

  const loadOFCRequests = async () => {
    try {
      setLoading(true);
      const response = await fetchWithAuth('/api/admin/ofc-requests');
      const data = await response.json();
      
      if (data.success) {
        setOFCRequests(data.ofcRequests || []);
        
        // Calculate stats
        const requests = data.ofcRequests || [];
        const pendingCount = requests.filter(r => r.status === 'pending_review').length;
        const approvedCount = requests.filter(r => r.status === 'approved').length;
        const rejectedCount = requests.filter(r => r.status === 'rejected').length;
        const implementedCount = requests.filter(r => r.status === 'implemented').length;
        
        setStats({
          total: requests.length,
          pending: pendingCount,
          approved: approvedCount,
          rejected: rejectedCount,
          implemented: implementedCount
        });
      } else {
        setError(data.error || 'Failed to load OFC requests');
      }
    } catch (err) {
      setError('Error loading OFC requests: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const approveRequest = async (requestId) => {
    try {
      setProcessingRequest(requestId);
      const response = await fetchWithAuth(`/api/admin/ofc-requests/${requestId}/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          supervisor_notes: supervisorNotes,
          approved_by: 'admin@vofc.gov' // TODO: Get from auth context
        }),
      });
      const result = await response.json();
      if (result.success) {
        alert('OFC request approved!');
        loadOFCRequests();
        setSupervisorNotes('');
      } else {
        alert(`Failed to approve: ${result.error}`);
      }
    } catch (err) {
      console.error('Error approving OFC request:', err);
      alert('Error approving OFC request.');
    } finally {
      setProcessingRequest(null);
    }
  };

  const rejectRequest = async (requestId) => {
    const reason = prompt('Please provide a reason for rejection:');
    if (!reason) return;

    try {
      setProcessingRequest(requestId);
      const response = await fetchWithAuth(`/api/admin/ofc-requests/${requestId}/reject`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          supervisor_notes: reason,
          approved_by: 'admin@vofc.gov' // TODO: Get from auth context
        }),
      });
      const result = await response.json();
      if (result.success) {
        alert('OFC request rejected!');
        loadOFCRequests();
      } else {
        alert(`Failed to reject: ${result.error}`);
      }
    } catch (err) {
      console.error('Error rejecting OFC request:', err);
      alert('Error rejecting OFC request.');
    } finally {
      setProcessingRequest(null);
    }
  };

  const markImplemented = async (requestId) => {
    try {
      setProcessingRequest(requestId);
      const response = await fetchWithAuth(`/api/admin/ofc-requests/${requestId}/implement`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          supervisor_notes: supervisorNotes,
          approved_by: 'admin@vofc.gov' // TODO: Get from auth context
        }),
      });
      const result = await response.json();
      if (result.success) {
        alert('OFC request marked as implemented!');
        loadOFCRequests();
        setSupervisorNotes('');
      } else {
        alert(`Failed to mark as implemented: ${result.error}`);
      }
    } catch (err) {
      console.error('Error marking OFC request as implemented:', err);
      alert('Error marking OFC request as implemented.');
    } finally {
      setProcessingRequest(null);
    }
  };

  if (!mounted) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading OFC requests...</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading OFC requests...</p>
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
            onClick={loadOFCRequests}
            className="btn btn-primary mt-4"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-blue-900 text-white p-4">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-2xl font-bold">OFC Requests Review</h1>
          <p className="text-blue-200">Review and approve Options for Consideration requests</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6">
        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-6 mb-8">
          <div className="card">
            <div className="card-body">
              <div className="flex items-center">
                <div className="p-3 rounded-full bg-blue-100 text-blue-600">
                  <i className="fas fa-list text-xl"></i>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Total Requests</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
                </div>
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

          <div className="card">
            <div className="card-body">
              <div className="flex items-center">
                <div className="p-3 rounded-full bg-purple-100 text-purple-600">
                  <i className="fas fa-check-double text-xl"></i>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Implemented</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.implemented}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* OFC Requests List */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-xl font-semibold text-gray-900">
              OFC Requests ({ofcRequests.length})
            </h2>
            <p className="text-gray-600 mt-1">
              Review and approve Options for Consideration requests from users
            </p>
          </div>

          <div className="card-body">
            {ofcRequests.length === 0 ? (
              <div className="text-center py-12">
                <div className="text-gray-400 text-6xl mb-4">
                  <i className="fas fa-lightbulb"></i>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">No OFC requests found</h3>
                <p className="text-gray-600">No Options for Consideration requests have been submitted yet.</p>
              </div>
            ) : (
              <div className="space-y-6">
                {ofcRequests.map((request) => (
                  <div key={request.id} className="border border-gray-200 rounded-lg p-6">
                    {/* Request Header */}
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <h3 className="text-lg font-semibold text-gray-900">
                            OFC Request #{request.id.slice(-8)}
                          </h3>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            request.status === 'pending_review' 
                              ? 'bg-yellow-100 text-yellow-800' 
                              : request.status === 'approved' 
                                ? 'bg-green-100 text-green-800' 
                                : request.status === 'rejected'
                                  ? 'bg-red-100 text-red-800'
                                  : 'bg-purple-100 text-purple-800'
                          }`}>
                            {request.status.replace('_', ' ')}
                          </span>
                        </div>
                        <div className="text-sm text-gray-600 mb-2">
                          <strong>Submitted by:</strong> {request.submitter}
                        </div>
                        <div className="text-sm text-gray-600 mb-2">
                          <strong>Discipline:</strong> {request.discipline || 'General'}
                        </div>
                        <div className="text-sm text-gray-600">
                          <strong>Submitted:</strong> {new Date(request.created_at).toLocaleDateString()}
                        </div>
                      </div>
                    </div>

                    {/* Vulnerability Context */}
                    <div className="mb-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
                      <h4 className="font-medium text-gray-900 mb-2">Vulnerability Context:</h4>
                      <p className="text-gray-700 text-sm">{request.vulnerability_text}</p>
                    </div>

                    {/* Proposed OFC */}
                    <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                      <h4 className="font-medium text-blue-900 mb-2">Proposed Option for Consideration:</h4>
                      <p className="text-blue-800">{request.ofc_text}</p>
                    </div>

                    {/* Supervisor Notes */}
                    {request.supervisor_notes && (
                      <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <h4 className="font-medium text-yellow-900 mb-2">Supervisor Notes:</h4>
                        <p className="text-yellow-800">{request.supervisor_notes}</p>
                      </div>
                    )}

                    {/* Action Buttons for Pending Requests */}
                    {request.status === 'pending_review' && (
                      <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <h5 className="font-medium text-yellow-900 mb-3">Review Actions</h5>
                        <div className="mb-3">
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Supervisor Notes (optional):
                          </label>
                          <textarea
                            value={supervisorNotes}
                            onChange={(e) => setSupervisorNotes(e.target.value)}
                            placeholder="Add notes for the submitter..."
                            className="w-full p-2 border border-gray-300 rounded-md text-sm"
                            rows="2"
                          />
                        </div>
                        <div className="flex space-x-3">
                          <button
                            onClick={() => approveRequest(request.id)}
                            disabled={processingRequest === request.id}
                            className="btn btn-success btn-sm"
                          >
                            {processingRequest === request.id ? 'Processing...' : 'Approve'}
                          </button>
                          <button
                            onClick={() => rejectRequest(request.id)}
                            disabled={processingRequest === request.id}
                            className="btn btn-danger btn-sm"
                          >
                            {processingRequest === request.id ? 'Processing...' : 'Reject'}
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Action for Approved Requests */}
                    {request.status === 'approved' && (
                      <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
                        <h5 className="font-medium text-green-900 mb-3">Implementation Actions</h5>
                        <div className="mb-3">
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Implementation Notes (optional):
                          </label>
                          <textarea
                            value={supervisorNotes}
                            onChange={(e) => setSupervisorNotes(e.target.value)}
                            placeholder="Add implementation notes..."
                            className="w-full p-2 border border-gray-300 rounded-md text-sm"
                            rows="2"
                          />
                        </div>
                        <div className="flex space-x-3">
                          <button
                            onClick={() => markImplemented(request.id)}
                            disabled={processingRequest === request.id}
                            className="btn btn-primary btn-sm"
                          >
                            {processingRequest === request.id ? 'Processing...' : 'Mark as Implemented'}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Refresh Button */}
          <div className="mt-6 flex justify-center">
            <button
              onClick={loadOFCRequests}
              className="btn btn-primary"
            >
              <i className="fas fa-sync-alt mr-2"></i>
              Refresh OFC Requests
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
