'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser, getUserProfile } from '../lib/auth';
import { supabase } from '@/app/lib/supabase-client.js';

export default function UserProfile() {
    const [user, setUser] = useState(null);
    const [profile, setProfile] = useState(null);
    const [userSubmissions, setUserSubmissions] = useState([]);
    const [returnedSubmissions, setReturnedSubmissions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('overview');
    const router = useRouter();

    useEffect(() => {
        checkAuth();
        loadUserData();
    }, []);

    const checkAuth = async () => {
        try {
            const currentUser = await getCurrentUser();
            if (!currentUser) {
                router.push('/splash');
                return;
            }
            setUser(currentUser);
        } catch (error) {
            console.error('Auth check failed:', error);
            router.push('/splash');
        }
    };

    const loadUserData = async () => {
        try {
            const currentUser = await getCurrentUser();
            if (!currentUser) return;

            // Get user profile
            const userProfile = await getUserProfile();
            setProfile(userProfile);

            // Get user's active submissions (from submissions table)
            // Try submitter_email first, fallback to checking data field if column doesn't exist
            try {
              // First, attempt query with submitter_email column
              // If column doesn't exist, PostgREST will return 400 Bad Request
              const { data: submissions, error } = await supabase
                  .from('submissions')
                  .select('*')
                  .eq('submitter_email', currentUser.email || '')
                  .order('created_at', { ascending: false });

              // Check if error is due to missing column (400) or other issues
              if (error) {
                // If 400 Bad Request or column-related error, fallback to client-side filtering
                if (error.code === 'PGRST116' || error.message?.includes('column') || error.status === 400 || error.code === '42883') {
                  // Column doesn't exist - fetch all and filter client-side
                  const { data: allSubmissions, error: fetchAllError } = await supabase
                      .from('submissions')
                      .select('*')
                      .order('created_at', { ascending: false });
                  
                  if (fetchAllError) {
                    console.error('Error fetching all submissions:', fetchAllError);
                    setUserSubmissions([]);
                  } else {
                    // Filter client-side by checking data field or other fields
                    const userSubmissions = (allSubmissions || []).filter(sub => {
                      // Check direct column first (if it exists in some rows)
                      if (sub.submitter_email === currentUser.email) return true;
                      // Check data JSON field
                      if (sub.data) {
                        try {
                          const data = typeof sub.data === 'string' ? JSON.parse(sub.data) : sub.data;
                          return data.submitter_email === currentUser.email || 
                                 data.submitter === currentUser.email;
                        } catch {}
                      }
                      return false;
                    });
                    setUserSubmissions(userSubmissions);
                  }
                } else {
                  // Other error - log and set empty
                  console.error('Error loading submissions:', error);
                  setUserSubmissions([]);
                }
              } else {
                // Success - use the filtered results
                setUserSubmissions(submissions || []);
              }
            } catch (err) {
              // Catch any unexpected errors (network, etc.)
              console.error('Error loading submissions:', err);
              setUserSubmissions([]);
            }

            // Get rejected submissions (from rejected_submissions table)
            try {
              const { data: rejectedSubmissions, error: rejectedError } = await supabase
                  .from('rejected_submissions')
                  .select('*')
                  .eq('submitter_email', currentUser.email || '')
                  .order('rejected_at', { ascending: false });

              if (rejectedError) {
                // If 400 Bad Request or column-related error, fallback to client-side filtering
                if (rejectedError.code === 'PGRST116' || rejectedError.message?.includes('column') || rejectedError.status === 400 || rejectedError.code === '42883') {
                  // Column doesn't exist - fetch all and filter client-side
                  const { data: allRejected, error: fetchAllError } = await supabase
                      .from('rejected_submissions')
                      .select('*')
                      .order('rejected_at', { ascending: false });
                  
                  if (fetchAllError) {
                    console.error('Error fetching all rejected submissions:', fetchAllError);
                    setReturnedSubmissions([]);
                  } else {
                    // Filter client-side
                    const userRejected = (allRejected || []).filter(sub => {
                      if (sub.submitter_email === currentUser.email) return true;
                      if (sub.data) {
                        try {
                          const data = typeof sub.data === 'string' ? JSON.parse(sub.data) : sub.data;
                          return data.submitter_email === currentUser.email || 
                                 data.submitter === currentUser.email;
                        } catch {}
                      }
                      return false;
                    });
                    setReturnedSubmissions(userRejected);
                  }
                } else {
                  console.error('Error loading rejected submissions:', rejectedError);
                  setReturnedSubmissions([]);
                }
              } else {
                setReturnedSubmissions(rejectedSubmissions || []);
              }
            } catch (err) {
              console.error('Error loading rejected submissions:', err);
              setReturnedSubmissions([]);
            }

        } catch (error) {
            console.error('Error loading user data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleResubmit = async (rejectedSubmissionId) => {
        try {
            // Use the resubmit_rejected_submission function
            const { data, error } = await supabase.rpc('resubmit_rejected_submission', {
                p_rejected_submission_id: rejectedSubmissionId
            });

            if (error) {
                console.error('Error resubmitting:', error);
                alert('Error resubmitting submission: ' + error.message);
                return;
            }

            const result = Array.isArray(data) ? data[0] : data;

            if (result.success) {
                alert('Submission resubmitted for review! New submission ID: ' + result.new_submission_id);
                loadUserData(); // Reload data
            } else {
                alert('Error resubmitting submission: ' + result.message);
            }
        } catch (error) {
            console.error('Error resubmitting:', error);
            alert('Error resubmitting submission');
        }
    };

    const handleDeleteSubmission = async (rejectedSubmissionId) => {
        if (!confirm('Are you sure you want to delete this rejected submission? This action cannot be undone.')) {
            return;
        }

        try {
            const { error } = await supabase
                .from('rejected_submissions')
                .delete()
                .eq('id', rejectedSubmissionId);

            if (error) {
                console.error('Error deleting rejected submission:', error);
                alert('Error deleting submission');
                return;
            }

            alert('Rejected submission deleted successfully!');
            loadUserData(); // Reload data
        } catch (error) {
            console.error('Error deleting submission:', error);
            alert('Error deleting submission');
        }
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <div className="text-lg">Loading profile...</div>
            </div>
        );
    }

    if (!user) {
        return (
            <div className="flex justify-center items-center h-64">
                <div className="text-lg">Redirecting to login...</div>
            </div>
        );
    }

    return (
        <div className="w-full px-4">
            {/* Header */}
            <div className="card mb-6">
                <div className="card-header">
                    <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
                        <div>
                            <h1 className="card-title">{user.full_name}</h1>
                            <p className="text-secondary">@{user.username}</p>
                        </div>
                        <div className="flex flex-col sm:flex-row gap-2 w-full lg:w-auto">
                            <button
                                onClick={() => router.push('/')}
                                className="btn btn-secondary w-full sm:w-auto"
                            >
                                Back to Dashboard
                            </button>
                            <button
                                onClick={() => router.push('/submit')}
                                className="btn btn-primary w-full sm:w-auto"
                            >
                                New Submission
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Profile Info */}
            <div className="card mb-6">
                <div className="card-header">
                    <h2 className="card-title">Profile Information</h2>
                </div>
                <div className="card-body">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="form-group">
                            <label className="form-label">Full Name</label>
                            <div className="form-control-plaintext">{user.full_name}</div>
                        </div>
                        <div className="form-group">
                            <label className="form-label">Username</label>
                            <div className="form-control-plaintext">{user.username}</div>
                        </div>
                        <div className="form-group">
                            <label className="form-label">Email</label>
                            <div className="form-control-plaintext">{user.username}@cisa.dhs.gov</div>
                        </div>
                        <div className="form-group">
                            <label className="form-label">Role</label>
                            <div className="form-control-plaintext">
                                <span className={`badge ${user.role === 'admin' ? 'bg-danger' :
                                    user.role === 'spsa' ? 'bg-warning' :
                                        user.role === 'psa' ? 'bg-info' :
                                            'bg-success'
                                    } text-white`}>
                                    {user.role.toUpperCase()}
                                </span>
                            </div>
                        </div>
                        <div className="form-group">
                            <label className="form-label">Organization</label>
                            <div className="form-control-plaintext">{user.agency || 'CISA'}</div>
                        </div>
                        <div className="form-group">
                            <label className="form-label">Status</label>
                            <div className="form-control-plaintext">
                                <span className="badge bg-success text-white">ACTIVE</span>
                            </div>
                        </div>
                        <div className="form-group">
                            <label className="form-label">Last Sign In</label>
                            <div className="form-control-plaintext">
                                {user.last_login 
                                    ? new Date(user.last_login).toLocaleDateString()
                                    : 'Never'
                                }
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <div className="card mb-6">
                <div className="card-header">
                    <div className="flex flex-col sm:flex-row gap-2">
                        <button
                            className={`btn ${activeTab === 'overview' ? 'btn-primary' : 'btn-secondary'} w-full sm:w-auto`}
                            onClick={() => setActiveTab('overview')}
                        >
                            Overview
                        </button>
                        <button
                            className={`btn ${activeTab === 'submissions' ? 'btn-primary' : 'btn-secondary'} w-full sm:w-auto`}
                            onClick={() => setActiveTab('submissions')}
                        >
                            My Submissions ({userSubmissions.length})
                        </button>
                        <button
                            className={`btn ${activeTab === 'returned' ? 'btn-primary' : 'btn-secondary'} w-full sm:w-auto`}
                            onClick={() => setActiveTab('returned')}
                        >
                            Returned Submissions ({returnedSubmissions.length})
                        </button>
                    </div>
                </div>

                <div className="card-body">
                    {/* Overview Tab */}
                    {activeTab === 'overview' && (
                        <div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                                <div className="card bg-primary text-white">
                                    <div className="card-body text-center">
                                        <div className="text-2xl font-bold">{userSubmissions.length}</div>
                                        <div className="text-sm">Total Submissions</div>
                                    </div>
                                </div>
                                <div className="card bg-success text-white">
                                    <div className="card-body text-center">
                                        <div className="text-2xl font-bold">
                                            {userSubmissions.filter(s => s.status === 'approved').length}
                                        </div>
                                        <div className="text-sm">Approved</div>
                                    </div>
                                </div>
                                <div className="card bg-warning text-white">
                                    <div className="card-body text-center">
                                        <div className="text-2xl font-bold">
                                            {userSubmissions.filter(s => s.status === 'pending_review').length}
                                        </div>
                                        <div className="text-sm">Pending Review</div>
                                    </div>
                                </div>
                                <div className="card bg-danger text-white">
                                    <div className="card-body text-center">
                                        <div className="text-2xl font-bold">
                                            {userSubmissions.filter(s => s.status === 'rejected').length}
                                        </div>
                                        <div className="text-sm">Returned</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Submissions Tab */}
                    {activeTab === 'submissions' && (
                        <div>
                            {userSubmissions.length === 0 ? (
                                <div className="text-center py-8 text-secondary">
                                    <p>No submissions yet</p>
                                    <button
                                        onClick={() => router.push('/submit')}
                                        className="btn btn-primary mt-3"
                                    >
                                        Create First Submission
                                    </button>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    {userSubmissions.map((submission) => {
                                        const data = typeof submission.data === 'string'
                                            ? JSON.parse(submission.data)
                                            : submission.data;

                                        return (
                                            <div key={submission.id} className="card">
                                                <div className="card-header">
                                                    <div className="flex justify-between items-start">
                                                        <h4 className="card-title text-lg">
                                                            {submission.type === 'vulnerability' ? 'Vulnerability' : 'OFC'} Submission
                                                        </h4>
                                                        <span className={`badge ${submission.status === 'pending_review' ? 'bg-warning' :
                                                            submission.status === 'approved' ? 'bg-success' :
                                                                submission.status === 'rejected' ? 'bg-danger' :
                                                                    'bg-secondary'
                                                            } text-white text-xs`}>
                                                            {submission.status === 'pending_review' ? 'Pending Review' :
                                                                submission.status === 'approved' ? 'Approved' :
                                                                    submission.status === 'rejected' ? 'Returned' :
                                                                        submission.status}
                                                        </span>
                                                    </div>
                                                </div>
                                                <div className="card-body">
                                                    <div className="mb-3">
                                                        <h5 className="font-medium mb-2 text-sm">
                                                            {submission.type === 'vulnerability' ? 'Vulnerability:' : 'OFC:'}
                                                        </h5>
                                                        <p className="text-sm text-secondary">
                                                            {submission.type === 'vulnerability' ? data.vulnerability : data.option_text}
                                                        </p>
                                                    </div>

                                                    <div className="text-xs text-secondary space-y-1">
                                                        <div>Discipline: {data.discipline}</div>
                                                        <div>Source: {data.source || 'N/A'}</div>
                                                        <div>Submitted: {new Date(submission.created_at).toLocaleDateString()}</div>
                                                        {submission.comments && (
                                                            <div className="mt-2 p-2 bg-gray-50 rounded">
                                                                <strong>Review Comments:</strong> {submission.comments}
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Returned Submissions Tab */}
                    {activeTab === 'returned' && (
                        <div>
                            {returnedSubmissions.length === 0 ? (
                                <div className="text-center py-8 text-secondary">
                                    <p>No returned submissions</p>
                                    <p className="text-sm">All your submissions have been approved or are pending review</p>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    {returnedSubmissions.map((submission) => {
                                        const data = typeof submission.data === 'string'
                                            ? JSON.parse(submission.data)
                                            : submission.data;

                                        return (
                                            <div key={submission.id} className="card border-danger">
                                                <div className="card-header bg-danger text-white">
                                                    <div className="flex justify-between items-start">
                                                        <h4 className="card-title text-lg text-white">
                                                            {submission.type === 'vulnerability' ? 'Vulnerability' : 'OFC'} Submission
                                                        </h4>
                                                        <span className="badge bg-white text-danger">
                                                            Returned
                                                        </span>
                                                    </div>
                                                </div>
                                                <div className="card-body">
                                                    <div className="mb-3">
                                                        <h5 className="font-medium mb-2 text-sm">
                                                            {submission.type === 'vulnerability' ? 'Vulnerability:' : 'OFC:'}
                                                        </h5>
                                                        <p className="text-sm text-secondary">
                                                            {submission.type === 'vulnerability' ? data.vulnerability : data.option_text}
                                                        </p>
                                                    </div>

                                                    {submission.rejection_reason && (
                                                        <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded">
                                                            <h6 className="font-medium text-red-800 mb-1">Rejection Reason:</h6>
                                                            <p className="text-sm text-red-700">{submission.rejection_reason}</p>
                                                        </div>
                                                    )}

                                                    <div className="text-xs text-secondary space-y-1 mb-3">
                                                        <div>Discipline: {data.discipline}</div>
                                                        <div>Source: {data.source || 'N/A'}</div>
                                                        <div>Submitted: {new Date(submission.created_at).toLocaleDateString()}</div>
                                                        <div>Rejected: {new Date(submission.rejected_at).toLocaleDateString()}</div>
                                                        {submission.resubmitted_at && (
                                                            <div>Resubmitted: {new Date(submission.resubmitted_at).toLocaleDateString()}</div>
                                                        )}
                                                    </div>

                                                    <div className="flex space-x-2">
                                                        <button
                                                            onClick={() => handleResubmit(submission.id)}
                                                            className="btn btn-warning btn-sm"
                                                        >
                                                            Resubmit for Review
                                                        </button>
                                                        <button
                                                            onClick={() => handleDeleteSubmission(submission.id)}
                                                            className="btn btn-danger btn-sm"
                                                        >
                                                            Delete
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
