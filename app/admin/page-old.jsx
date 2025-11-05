'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { fetchVulnerabilities, fetchVOFC } from '../lib/fetchVOFC';
import { getCurrentUser, getUserProfile, canAccessAdmin } from '../lib/auth';
import { supabase } from '../lib/supabaseClient';
import StructuredSubmissionView from '../components/StructuredSubmissionView';
// import SessionTimeoutWarning from '../../components/SessionTimeoutWarning';

export default function AdminPage() {
  const [stats, setStats] = useState({
    vulnerabilities: 0,
    ofcs: 0,
    users: 0,
    pendingVulnerabilities: 0,
    pendingOFCs: 0
  });
  const [dbHealth, setDbHealth] = useState({
    connection: 'Unknown',
    responseTime: 0,
    lastChecked: null
  });
  const [loading, setLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState(null);
  const [userRole, setUserRole] = useState(null);
  const [showBackToTop, setShowBackToTop] = useState(false);
  const router = useRouter();

  useEffect(() => {
    checkAuth();
    loadStats();
    checkDatabaseHealth();
  }, []);

  useEffect(() => {
    const handleScroll = () => {
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      setShowBackToTop(scrollTop > 300);
    };

    const handleVisibilityChange = () => {
      if (!document.hidden) {
        loadStats();
        checkDatabaseHealth();
      }
    };

    window.addEventListener('scroll', handleScroll);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      window.removeEventListener('scroll', handleScroll);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  const checkAuth = async () => {
    try {
      const user = await getCurrentUser();
      if (!user) {
        router.push('/splash');
        return;
      }

      const profile = await getUserProfile();
      console.log('🔐 User profile:', profile);
      console.log('🔐 User data:', user);
      setCurrentUser(user);
      setUserRole(profile?.role || user.role);

      // Check both profile.role and user.role for admin access
      const userRole = profile?.role || user.role;
      console.log('🔐 Checking role:', userRole);
      console.log('🔐 Profile role:', profile?.role);
      console.log('🔐 User role:', user.role);
      
      // Allow admin, spsa, analyst, and psa roles to access admin tools
      const allowedRoles = ['admin', 'spsa', 'analyst', 'psa'];
      if (!allowedRoles.includes(userRole)) {
        console.log('❌ Access denied for role:', userRole);
        console.log('❌ Allowed roles:', allowedRoles);
        console.log('❌ Profile role:', profile?.role);
        console.log('❌ User role:', user.role);
        router.push('/');
        return;
      }

    } catch (error) {
      console.error('Auth check failed:', error);
      router.push('/splash');
    }
  };

  const loadStats = async () => {
    try {
      const [vulnerabilities, ofcs] = await Promise.all([
        fetchVulnerabilities(),
        fetchVOFC()
      ]);

      setStats({
        vulnerabilities: vulnerabilities.length,
        ofcs: ofcs.length,
        users: 4, // We know we have 4 users
        pendingVulnerabilities: 0,
        pendingOFCs: 0
      });
    } catch (error) {
      console.error('Error loading stats:', error);
    } finally {
      setLoading(false);
    }
  };







  const handleSignOut = async () => {
    try {
      const { error } = await supabase.auth.signOut();
      if (error) {
        console.error('Error signing out:', error);
        alert('Error signing out');
      } else {
        router.push('/login');
      }
    } catch (error) {
      console.error('Error signing out:', error);
      alert('Error signing out');
    }
  };

  const checkDatabaseHealth = async () => {
    try {
      const startTime = Date.now();

      // Test database connection with a simple query
      const { data, error } = await supabase
        .from('user_profiles')
        .select('count')
        .limit(1);

      const responseTime = Date.now() - startTime;

      if (error) {
        setDbHealth({
          connection: 'Error',
          responseTime: responseTime,
          lastChecked: new Date().toLocaleTimeString()
        });
      } else {
        setDbHealth({
          connection: 'Healthy',
          responseTime: responseTime,
          lastChecked: new Date().toLocaleTimeString()
        });
      }
    } catch (error) {
      setDbHealth({
        connection: 'Error',
        responseTime: 0,
        lastChecked: new Date().toLocaleTimeString()
      });
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-lg">Loading admin dashboard...</div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* <SessionTimeoutWarning /> */}
      <div className="card mb-6">
        <div className="card-header">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="card-title">Admin Dashboard</h1>
              <p className="text-secondary">Welcome, {currentUser?.email} ({userRole})</p>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => {
                  loadStats();
                  loadSubmittedItems();
                  loadSubmissions();
                  checkDatabaseHealth();
                }}
                className="btn btn-primary"
              >
                Refresh Data
              </button>
              <button
                onClick={async () => {
                  console.log('🔧 Disabling RLS...');
                  try {
                    const response = await fetch('/api/admin/disable-rls', { method: 'POST' });
                    const result = await response.json();
                    if (result.success) {
                      alert(`RLS disabled! Found ${result.submissionsFound} submissions.`);
                      loadSubmittedItems(); // Refresh data
                    } else {
                      alert('Error disabling RLS: ' + result.error);
                    }
                  } catch (error) {
                    console.error('Error:', error);
                    alert('Error disabling RLS');
                  }
                }}
                className="btn btn-warning"
              >
                Fix RLS
              </button>
              <Link href="/" className="btn btn-secondary">
                Back to Dashboard
              </Link>
              <button
                onClick={handleSignOut}
                className="btn btn-danger"
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </div>

        <div className="card mb-6">
          <div className="card-header">
            <div className="flex justify-between items-center">
              <h2 className="card-title">Database Health and Status</h2>
              <div className="flex gap-2">
                <Link href="/admin/users" className="btn btn-primary btn-sm">
                  <i className="fas fa-users mr-2"></i>
                  Manage Users
                </Link>
                <Link href="/admin/ofcs" className="btn btn-success btn-sm">
                  <i className="fas fa-lightbulb mr-2"></i>
                  Manage OFCs
                </Link>
              </div>
            </div>
          </div>
        <div className="row">
          <div className="col-md-3">
            <div className="card bg-warning text-white">
              <div className="card-body text-center">
                <div className="text-2xl font-bold">{stats.vulnerabilities}</div>
                <div className="text-sm">Vulnerabilities</div>
                {stats.pendingVulnerabilities > 0 && (
                  <div className="text-xs mt-1">
                    {stats.pendingVulnerabilities} pending
                  </div>
                )}
              </div>
            </div>
          </div>
          <div className="col-md-3">
            <div className="card bg-info text-white">
              <div className="card-body text-center">
                <div className="text-2xl font-bold">{stats.ofcs}</div>
                <div className="text-sm">OFCs</div>
                {stats.pendingOFCs > 0 && (
                  <div className="text-xs mt-1">
                    {stats.pendingOFCs} pending
                  </div>
                )}
              </div>
            </div>
          </div>
          <div className="col-md-3">
            <div className="card bg-primary text-white">
              <div className="card-body text-center">
                <div className="text-2xl font-bold">{stats.users}</div>
                <div className="text-sm">Users</div>
              </div>
            </div>
          </div>
          <div className="col-md-3">
            <div className={`card ${dbHealth.connection === 'Healthy' ? 'bg-success' : 'bg-danger'} text-white`}>
              <div className="card-body text-center">
                <div className="text-2xl font-bold">{dbHealth.responseTime}ms</div>
                <div className="text-sm">DB Response</div>
                <div className="text-xs mt-1">
                  {dbHealth.connection}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="card mb-6">
        <div className="card-header">
          <h2 className="card-title">Admin Actions</h2>
        </div>
        <div className="card-body">
          <div className="row">
            <div className="col-md-6">
              <div className="card">
                <div className="card-body">
                  <h4 className="card-title">User Management</h4>
                  <p className="card-text">Create, edit, and manage user accounts and roles.</p>
                  <Link href="/admin/users" className="btn btn-primary">
                    Manage Users
                  </Link>
                </div>
              </div>
            </div>
            <div className="col-md-6">
              <div className="card">
                <div className="card-body">
                  <h4 className="card-title">System Settings</h4>
                  <p className="card-text">Configure system-wide settings and preferences.</p>
                  <button className="btn btn-secondary" disabled>
                    Coming Soon
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>


      {/* Database Health and Status Section */}
          <div className="text-center py-8 text-secondary">
            <p>No vulnerabilities submitted yet</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {submittedVulnerabilities.filter(s => s.status !== 'rejected').slice(0, 6).map((submission) => {
              const data = typeof submission.data === 'string'
                ? JSON.parse(submission.data)
                : submission.data;
              console.log('Vulnerability submission data:', data);
              return (
                <div key={submission.id} className="card">
                  <div className="card-header">
                    <div className="flex justify-between items-start">
                      <h4 className="card-title text-lg">{data.vulnerability}</h4>
                      <div className="flex flex-col space-y-1">
                        <span className="badge bg-primary text-white text-xs">
                          {data.discipline}
                        </span>
                        <span className={`badge ${submission.status === 'pending_review' ? 'bg-warning' :
                          submission.status === 'approved' ? 'bg-success' :
                            submission.status === 'rejected' ? 'bg-danger' :
                              'bg-secondary'
                          } text-white text-xs`}>
                          {submission.status === 'pending_review' ? 'Pending Review' :
                            submission.status === 'approved' ? 'Approved' :
                              submission.status === 'rejected' ? 'Rejected' :
                                submission.status}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="card-body">
                    {editingSubmission === submission.id ? (
                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium mb-1">Vulnerability:</label>
                          <textarea
                            value={editData.vulnerability || ''}
                            onChange={(e) => setEditData({ ...editData, vulnerability: e.target.value })}
                            className="w-full p-2 border rounded text-sm"
                            rows="3"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium mb-1">Discipline:</label>
                          <input
                            type="text"
                            value={editData.discipline || ''}
                            onChange={(e) => setEditData({ ...editData, discipline: e.target.value })}
                            className="w-full p-2 border rounded text-sm"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium mb-1">Source:</label>
                          <input
                            type="text"
                            value={editData.source || ''}
                            onChange={(e) => setEditData({ ...editData, source: e.target.value })}
                            className="w-full p-2 border rounded text-sm"
                          />
                        </div>
                        {editData.associated_ofcs && editData.associated_ofcs.length > 0 && (
                          <div>
                            <label className="block text-sm font-medium mb-1">Associated OFCs:</label>
                            {editData.associated_ofcs.map((ofc, index) => (
                              <input
                                key={index}
                                type="text"
                                value={ofc}
                                onChange={(e) => {
                                  const newOfcs = [...editData.associated_ofcs];
                                  newOfcs[index] = e.target.value;
                                  setEditData({ ...editData, associated_ofcs: newOfcs });
                                }}
                                className="w-full p-2 border rounded text-sm mb-2"
                              />
                            ))}
                          </div>
                        )}
                        <div className="flex space-x-2">
                          <button
                            onClick={() => handleSaveEdit(submission.id)}
                            disabled={processingSubmission === submission.id}
                            className="btn btn-success btn-sm"
                          >
                            {processingSubmission === submission.id ? 'Saving...' : 'Save'}
                          </button>
                          <button
                            onClick={handleCancelEdit}
                            className="btn btn-secondary btn-sm"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="mb-4">
                          <h5 className="font-medium mb-2">Vulnerability:</h5>
                          <p className="text-sm text-secondary">{data.vulnerability}</p>
                        </div>

                        {/* Show associated OFCs if they exist */}
                        {data.associated_ofcs && data.associated_ofcs.length > 0 && (
                          <div className="mb-4">
                            <h5 className="font-medium mb-2">Associated Options for Consideration:</h5>
                            <ul className="list-disc list-inside space-y-1">
                              {data.associated_ofcs.map((ofc, index) => (
                                <li key={index} className="text-sm text-secondary">{ofc}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        <div className="text-xs text-secondary space-y-1">
                          <div>Discipline: {data.discipline}</div>
                          <div>Source: {data.source || 'N/A'}</div>
                          <div>Associated OFCs: {data.ofc_count || data.associated_ofcs?.length || 0}</div>
                          <div>Submitter Email: {submission.submitter_email || 'Not provided'}</div>
                          <div>Submitted: {new Date(submission.created_at).toLocaleDateString()}</div>
                        </div>
                      </>
                    )}

                    {submission.status === 'pending_review' && (userRole === 'spsa' || userRole === 'admin') && (
                      <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
                        <h5 className="font-medium mb-2 text-sm">Admin Actions:</h5>
                        <div className="space-y-2">
                          <textarea
                            value={comments}
                            onChange={(e) => setComments(e.target.value)}
                            placeholder="Add comments (optional)"
                            className="w-full p-2 border rounded text-xs"
                            rows="2"
                          />
                          <div className="flex space-x-2">
                            <button
                              onClick={() => handleApproveSubmission(submission.id)}
                              disabled={processingSubmission === submission.id}
                              className="btn btn-success btn-sm"
                            >
                              {processingSubmission === submission.id ? 'Processing...' : 'Approve'}
                            </button>
                            <button
                              onClick={() => handleRejectSubmission(submission.id)}
                              disabled={processingSubmission === submission.id}
                              className="btn btn-danger btn-sm"
                            >
                              {processingSubmission === submission.id ? 'Processing...' : 'Reject'}
                            </button>
                            <button
                              onClick={() => handleEditSubmission(submission)}
                              disabled={processingSubmission === submission.id}
                              className="btn btn-warning btn-sm"
                            >
                              Edit
                            </button>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Submitted OFCs */}
      <div className="mb-6">
        <div className="mb-4">
          <h2 className="text-2xl font-bold text-primary">Active Standalone OFC Submissions</h2>
          <p className="text-sm text-secondary">Standalone OFCs not associated with vulnerabilities (pending review or approved)</p>
        </div>

        {submittedOFCs.filter(s => s.status !== 'rejected').length === 0 ? (
          <div className="text-center py-8 text-secondary">
            <p>No OFCs submitted yet</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {submittedOFCs.filter(s => s.status !== 'rejected').slice(0, 6).map((submission) => {
              const data = typeof submission.data === 'string'
                ? JSON.parse(submission.data)
                : submission.data;
              console.log('OFC submission data:', data);
              return (
                <div key={submission.id} className="card">
                  <div className="card-header">
                    <div className="flex justify-between items-start">
                      <h4 className="card-title text-lg">{data.option_text}</h4>
                      <div className="flex flex-col space-y-1">
                        <span className="badge bg-primary text-white text-xs">
                          {data.discipline}
                        </span>
                        <span className={`badge ${submission.status === 'pending_review' ? 'bg-warning' :
                          submission.status === 'approved' ? 'bg-success' :
                            submission.status === 'rejected' ? 'bg-danger' :
                              'bg-secondary'
                          } text-white text-xs`}>
                          {submission.status === 'pending_review' ? 'Pending Review' :
                            submission.status === 'approved' ? 'Approved' :
                              submission.status === 'rejected' ? 'Rejected' :
                                submission.status}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="card-body">
                    <p className="text-sm text-secondary mb-3">{data.option_text}</p>
                    <div className="text-xs text-secondary space-y-1">
                      <div>Discipline: {data.discipline}</div>
                      <div>Source: {data.source || 'N/A'}</div>
                      <div>Associated Vulnerability: {data.associated_vulnerability ? 'Yes' : 'No'}</div>
                      <div>Submitter Email: {submission.submitter_email || 'Not provided'}</div>
                      <div>Submitted: {new Date(submission.created_at).toLocaleDateString()}</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Rejected Submissions Section */}
      <div className="mb-6">
        <div className="mb-4">
          <h2 className="text-2xl font-bold text-danger">Rejected Submissions</h2>
          <p className="text-sm text-secondary">Rejected submissions that can be deleted to clean up the interface</p>
        </div>

        {submissions.filter(s => s.status === 'rejected').length === 0 ? (
          <div className="text-center py-8 text-secondary">
            <p>No rejected submissions found</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {submissions.filter(s => s.status === 'rejected').map((submission) => {
              const data = typeof submission.data === 'string'
                ? JSON.parse(submission.data)
                : submission.data;
              return (
                <div key={submission.id} className="card border-danger">
                  <div className="card-header bg-danger text-white">
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="card-title text-lg text-white">
                          {submission.type === 'vulnerability' ? 'Vulnerability' : 'OFC'} Submission
                        </h4>
                        <p className="text-sm text-white opacity-75">ID: {submission.id.slice(0, 8)}...</p>
                      </div>
                      <div className="flex flex-col space-y-1">
                        <span className="badge bg-white text-danger">
                          Rejected
                        </span>
                        <span className="badge bg-secondary text-white text-xs">
                          {submission.source}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="card-body">
                    <div className="mb-3">
                      <div className="flex justify-between items-center mb-2">
                        <h5 className="font-medium text-sm">Submission Data:</h5>
                        <button
                          onClick={() => setViewingStructuredData(submission.id)}
                          className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
                        >
                          View Structured Data
                        </button>
                      </div>
                      <div className="bg-gray-50 p-3 rounded text-xs max-h-32 overflow-y-auto">
                        <pre className="whitespace-pre-wrap">{JSON.stringify(data, null, 2)}</pre>
                      </div>
                    </div>

                    <div className="text-xs text-secondary space-y-1 mb-3">
                      <div>Created: {new Date(submission.created_at).toLocaleString()}</div>
                      <div>Rejected: {new Date(submission.processed_at || submission.updated_at).toLocaleString()}</div>
                      {submission.processed_by && (
                        <div>Rejected by: {submission.processed_by}</div>
                      )}
                    </div>

                    {/* Show comments if submission was processed */}
                    {submission.comments && (
                      <div className="mb-3 p-2 bg-gray-50 rounded text-xs">
                        <strong>Review Comments:</strong> {submission.comments}
                      </div>
                    )}

                    {/* Delete Button */}
                    <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded">
                      <h6 className="font-medium mb-2 text-sm text-red-800">Delete Submission</h6>
                      <p className="text-xs text-red-600 mb-3">
                        This will permanently delete the rejected submission from the database.
                      </p>
                      <button
                        onClick={() => handleDeleteSubmission(submission.id)}
                        disabled={processingSubmission === submission.id}
                        className="btn bg-danger text-white text-xs px-3 py-1"
                      >
                        {processingSubmission === submission.id ? 'Deleting...' : 'Delete Permanently'}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* API Submissions Section */}
      <div className="mb-6">
        <div className="mb-4">
          <h2 className="text-2xl font-bold text-primary">Active API Submissions</h2>
          <p className="text-sm text-secondary">External system submissions (pending review or approved)</p>
        </div>

        {submissions.filter(s => s.status !== 'rejected').length === 0 ? (
          <div className="text-center py-8 text-secondary">
            <p>No API submissions found</p>
            <p className="text-sm">Submissions will appear here when external systems submit data via the API endpoints</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {submissions.filter(s => s.status !== 'rejected').map((submission) => (
              <div key={submission.id} className="card">
                <div className="card-header">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="card-title text-lg">
                        {submission.type === 'vulnerability' ? 'Vulnerability' : 'OFC'} Submission
                      </h4>
                      <p className="text-sm text-secondary">ID: {submission.id.slice(0, 8)}...</p>
                    </div>
                    <div className="flex flex-col space-y-1">
                      <span className={`badge ${submission.status === 'pending_review' ? 'bg-warning' :
                        submission.status === 'approved' ? 'bg-success' :
                          submission.status === 'rejected' ? 'bg-danger' :
                            'bg-info'
                        } text-white`}>
                        {submission.status}
                      </span>
                      <span className="badge bg-secondary text-white text-xs">
                        {submission.source}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="card-body">
                  <div className="mb-3">
                    <div className="flex justify-between items-center mb-2">
                      <h5 className="font-medium text-sm">Submission Data:</h5>
                      <button
                        onClick={() => setViewingStructuredData(submission.id)}
                        className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
                      >
                        View Structured Data
                      </button>
                    </div>
                    <div className="bg-gray-50 p-3 rounded text-xs max-h-32 overflow-y-auto">
                      <pre className="whitespace-pre-wrap">{JSON.stringify(
                        typeof submission.data === 'string'
                          ? JSON.parse(submission.data)
                          : submission.data,
                        null, 2
                      )}</pre>
                    </div>
                  </div>

                  <div className="text-xs text-secondary space-y-1">
                    <div>Created: {new Date(submission.created_at).toLocaleString()}</div>
                    <div>Updated: {new Date(submission.updated_at).toLocaleString()}</div>
                  </div>

                  {/* SPSA Approval/Rejection Section */}
                  {(() => {
                    console.log('Submission status:', submission.status);
                    console.log('User role:', userRole);
                    console.log('Show approval section:', submission.status === 'pending_review' && (userRole === 'spsa' || userRole === 'admin'));
                    return null;
                  })()}
                  {submission.status === 'pending_review' && (userRole === 'spsa' || userRole === 'admin') && (
                    <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
                      <h6 className="font-medium mb-2 text-sm">SPSA Review</h6>
                      <div className="mb-3">
                        <label className="block text-xs font-medium mb-1">Comments (optional):</label>
                        <textarea
                          className="form-input w-full text-xs"
                          rows="2"
                          value={comments}
                          onChange={(e) => setComments(e.target.value)}
                          placeholder="Add comments for the submitter..."
                        />
                      </div>
                      <div className="flex space-x-2">
                        <button
                          onClick={() => handleApproveSubmission(submission.id)}
                          disabled={processingSubmission === submission.id}
                          className="btn bg-success text-white text-xs px-3 py-1"
                        >
                          {processingSubmission === submission.id ? 'Processing...' : 'Approve'}
                        </button>
                        <button
                          onClick={() => handleRejectSubmission(submission.id)}
                          disabled={processingSubmission === submission.id}
                          className="btn bg-danger text-white text-xs px-3 py-1"
                        >
                          {processingSubmission === submission.id ? 'Processing...' : 'Reject'}
                        </button>
                        <button
                          onClick={() => handleEditSubmission(submission)}
                          disabled={processingSubmission === submission.id}
                          className="btn bg-warning text-white text-xs px-3 py-1"
                        >
                          Edit
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Show comments if submission was processed */}
                  {submission.comments && (
                    <div className="mt-3 p-2 bg-gray-50 rounded text-xs">
                      <strong>Review Comments:</strong> {submission.comments}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">System Status</h2>
        </div>
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <span>Database Connection</span>
            <span className={`px-2 py-1 rounded-full text-xs ${dbHealth.connection === 'Healthy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
              }`}>
              {dbHealth.connection} ({dbHealth.responseTime}ms)
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span>Last Health Check</span>
            <span className="text-sm text-secondary">{dbHealth.lastChecked}</span>
          </div>
          <div className="flex justify-between items-center">
            <span>Authentication Service</span>
            <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">Operational</span>
          </div>
          <div className="flex justify-between items-center">
            <span>API Endpoints</span>
            <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">All Systems Go</span>
          </div>
        </div>
      </div>

      {/* Back to Top Button */}
      {showBackToTop && (
        <button
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          className="back-to-top"
          title="Back to top"
        >
          <i className="fas fa-arrow-up"></i>
        </button>
      )}

      {/* Structured Submission View Modal */}
      {viewingStructuredData && (
        <StructuredSubmissionView
          submissionId={viewingStructuredData}
          onClose={() => setViewingStructuredData(null)}
        />
      )}
    </div>
  );
}


