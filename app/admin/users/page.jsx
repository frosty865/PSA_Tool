'use client';
// Admin User Management Page
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser, USER_ROLES, getRoleDisplayName, getRoleBadgeColor } from '../../lib/auth';
import { fetchWithAuth } from '../../lib/fetchWithAuth';
import '@/styles/cisa.css';

export default function UserManagement() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState(null);
  const [userRole, setUserRole] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    organization: '',
    phone: '',
    role: 'psa'
  });
  const [editFormData, setEditFormData] = useState({
    user_id: '',
    username: '',
    full_name: '',
    role: '',
    agency: '',
    password: '',
    force_password_change: false,
    is_active: true
  });
  const router = useRouter();

  useEffect(() => {
    checkAuth();
    loadUsers();
  }, []);

  const checkAuth = async () => {
    try {
      const user = await getCurrentUser();
      if (!user) {
        router.push('/splash');
        return;
      }

      setCurrentUser(user);
      setUserRole(user.role);

      // Admin and SPSA can manage users
      if (!['admin', 'spsa'].includes(user.role)) {
        router.push('/');
        return;
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      router.push('/splash');
    }
  };

  const loadUsers = async () => {
    try {
      const response = await fetchWithAuth('/api/admin/users', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to load users');
      }

      const result = await response.json();
      if (result.success) {
        // Map API response to match frontend expectations
        const mappedUsers = (result.users || []).map(user => ({
          user_id: user.id || user.user_id,
          username: user.email?.split('@')[0] || user.username || user.email,
          email: user.email,
          full_name: user.full_name || user.name || '',
          role: user.role || 'user',
          agency: user.agency || user.organization || 'CISA',
          is_active: user.is_active ?? true,
          force_password_change: user.force_password_change || false,
          last_login: user.last_sign_in_at || user.last_login
        }));
        setUsers(mappedUsers);
      } else {
        throw new Error(result.error || 'Failed to load users');
      }
    } catch (error) {
      console.error('Error loading users:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      const response = await fetchWithAuth('/api/admin/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: formData.email, // API expects 'email', not 'username'
          password: formData.password,
          role: formData.role,
          first_name: formData.first_name || '',
          last_name: formData.last_name || '',
          agency: formData.organization || 'CISA'
        }),
      });

      const result = await response.json();

      if (result.success) {
        // Reset form and reload users
        setFormData({
          username: '',
          email: '',
          password: '',
          first_name: '',
          last_name: '',
          organization: '',
          phone: '',
          role: 'psa'
        });
        setShowCreateForm(false);
        loadUsers();
        alert('User created successfully!');
      } else {
        throw new Error(result.error || 'Failed to create user');
      }
    } catch (error) {
      console.error('Error creating user:', error);
      alert('Error creating user: ' + error.message);
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!confirm('Are you sure you want to delete this user?')) return;

    try {
      const response = await fetchWithAuth(`/api/admin/users?user_id=${userId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const result = await response.json();

      if (result.success) {
        loadUsers();
        alert('User deleted successfully!');
      } else {
        throw new Error(result.error || 'Failed to delete user');
      }
    } catch (error) {
      console.error('Error deleting user:', error);
      alert('Error deleting user: ' + error.message);
    }
  };

  const handleToggleActive = async (userId, isActive) => {
    try {
      const response = await fetchWithAuth('/api/admin/users', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          is_active: !isActive
        }),
      });

      const result = await response.json();

      if (result.success) {
        loadUsers();
        alert(`User ${!isActive ? 'activated' : 'deactivated'} successfully!`);
      } else {
        throw new Error(result.error || 'Failed to update user');
      }
    } catch (error) {
      console.error('Error updating user:', error);
      alert('Error updating user: ' + error.message);
    }
  };

  const handleEditUser = (user) => {
    console.log('🔧 Edit user clicked:', user);
    setEditingUser(user);
    // Split full_name into first_name and last_name if needed
    const nameParts = (user.full_name || '').trim().split(/\s+/);
    const first_name = nameParts[0] || '';
    const last_name = nameParts.slice(1).join(' ') || '';
    
    setEditFormData({
      user_id: user.user_id || user.id,
      username: user.username || user.email?.split('@')[0] || '',
      full_name: user.full_name || '',
      first_name: user.first_name || first_name,
      last_name: user.last_name || last_name,
      role: user.role || 'user',
      agency: user.agency || user.organization || '',
      password: '',
      force_password_change: user.force_password_change || false,
      is_active: user.is_active ?? true
    });
    setShowEditForm(true);
    console.log('🔧 Edit form opened, form data:', editFormData);
  };

  const handleUpdateUser = async (e) => {
    e.preventDefault();
    try {
      // Split full_name into first_name and last_name for API
      const nameParts = (editFormData.full_name || '').trim().split(/\s+/);
      const first_name = editFormData.first_name || nameParts[0] || '';
      const last_name = editFormData.last_name || nameParts.slice(1).join(' ') || '';
      
      // Prepare update payload with fields the API expects
      const updatePayload = {
        user_id: editFormData.user_id,
        role: editFormData.role,
        is_active: editFormData.is_active,
        first_name: first_name,
        last_name: last_name,
        organization: editFormData.agency || 'CISA'
      };
      
      // Only include password if provided
      if (editFormData.password && editFormData.password.trim()) {
        updatePayload.password = editFormData.password;
      }
      
      console.log('📤 Sending update request:', updatePayload);
      
      const response = await fetchWithAuth('/api/admin/users', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updatePayload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        setShowEditForm(false);
        setEditingUser(null);
        // Reset form data
        setEditFormData({
          user_id: '',
          username: '',
          full_name: '',
          role: '',
          agency: '',
          password: '',
          force_password_change: false,
          is_active: true
        });
        loadUsers();
        alert('User updated successfully!');
      } else {
        throw new Error(result.error || 'Failed to update user');
      }
    } catch (error) {
      console.error('Error updating user:', error);
      alert('Error updating user: ' + error.message);
    }
  };

  const handleChangePassword = async (userId) => {
    const newPassword = prompt('Enter new password for user:');
    if (!newPassword) return;

    try {
      const response = await fetchWithAuth('/api/admin/users', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          password: newPassword
        }),
      });

      const result = await response.json();

      if (result.success) {
        loadUsers();
        alert('Password changed successfully!');
      } else {
        throw new Error(result.error || 'Failed to change password');
      }
    } catch (error) {
      console.error('Error changing password:', error);
      alert('Error changing password: ' + error.message);
    }
  };

  const handleForcePasswordChange = async (userId, forceChange) => {
    try {
      const response = await fetchWithAuth('/api/admin/users', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          force_password_change: forceChange
        }),
      });

      const result = await response.json();

      if (result.success) {
        loadUsers();
        alert(`Password change ${forceChange ? 'required' : 'not required'} at next login!`);
      } else {
        throw new Error(result.error || 'Failed to update password change requirement');
      }
    } catch (error) {
      console.error('Error updating password change requirement:', error);
      alert('Error updating password change requirement: ' + error.message);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-lg">Loading user management...</div>
      </div>
    );
  }

  return (
    <div className="w-full px-4">
      <div className="card mb-6">
        <div className="card-header">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <h1 className="card-title">User Management</h1>
            <button
              onClick={() => setShowCreateForm(!showCreateForm)}
              className="btn btn-primary w-full sm:w-auto"
            >
              {showCreateForm ? 'Cancel' : 'Create New User'}
            </button>
          </div>
        </div>

        {showCreateForm && (
          <div className="card-body border-t">
            <form onSubmit={handleCreateUser} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="form-group">
                  <label className="form-label">Username *</label>
                  <input
                    type="text"
                    required
                    value={formData.username}
                    onChange={(e) => setFormData({...formData, username: e.target.value})}
                    className="form-input w-full"
                    placeholder="e.g., admin, spsa_user"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Email *</label>
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                    className="form-input w-full"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Password *</label>
                  <input
                    type="password"
                    required
                    value={formData.password}
                    onChange={(e) => setFormData({...formData, password: e.target.value})}
                    className="form-input w-full"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="form-group">
                  <label className="form-label">First Name</label>
                  <input
                    type="text"
                    value={formData.first_name}
                    onChange={(e) => setFormData({...formData, first_name: e.target.value})}
                    className="form-input w-full"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Last Name</label>
                  <input
                    type="text"
                    value={formData.last_name}
                    onChange={(e) => setFormData({...formData, last_name: e.target.value})}
                    className="form-input w-full"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="form-group">
                  <label className="form-label">Organization</label>
                  <input
                    type="text"
                    value={formData.organization}
                    onChange={(e) => setFormData({...formData, organization: e.target.value})}
                    className="form-input w-full"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Phone</label>
                  <input
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => setFormData({...formData, phone: e.target.value})}
                    className="form-input w-full"
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Role (User Group) *</label>
                <select
                  required
                  value={formData.role}
                  onChange={(e) => setFormData({...formData, role: e.target.value})}
                  className="form-select w-full"
                >
                  <optgroup label="Administrative Roles (Full Access)">
                    <option value="admin">Administrator - Full system access</option>
                    <option value="spsa">SPSA (Supervisory PSA) - Full system access</option>
                  </optgroup>
                  <optgroup label="Standard User Role">
                    <option value="psa">PSA (Protective Security Advisor) - Standard user</option>
                  </optgroup>
                </select>
                <div className="mt-2 p-3 rounded-md" style={{
                  backgroundColor: (formData.role === 'admin' || formData.role === 'spsa') ? '#e6f6ea' : '#e3f2fd',
                  border: `2px solid ${(formData.role === 'admin' || formData.role === 'spsa') ? '#00a651' : '#2196f3'}`
                }}>
                  {formData.role === 'admin' || formData.role === 'spsa' ? (
                    <div>
                      <div className="text-sm font-semibold text-green-800 mb-1">✓ Full Admin Access</div>
                      <ul className="text-xs text-green-700 space-y-1 list-disc list-inside">
                        <li>User management (create, edit, delete users)</li>
                        <li>Submission review and approval</li>
                        <li>Admin panel access</li>
                        <li>Audit trail access</li>
                        <li>System monitoring and controls</li>
                        <li>Learning metrics dashboard</li>
                      </ul>
                    </div>
                  ) : (
                    <div>
                      <div className="text-sm font-semibold text-blue-800 mb-1">Standard User Access</div>
                      <ul className="text-xs text-blue-700 space-y-1 list-disc list-inside">
                        <li>Submit documents and vulnerabilities</li>
                        <li>View approved production data</li>
                        <li>View own submissions</li>
                        <li>No admin panel access</li>
                        <li>No user management</li>
                      </ul>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex flex-col sm:flex-row gap-2">
                <button type="submit" className="btn btn-primary w-full sm:w-auto">
                  Create User
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="btn btn-secondary w-full sm:w-auto"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}
      </div>

      {/* Edit User Sidebar */}
      {showEditForm && editingUser && (
        <div className="fixed inset-0 bg-black bg-opacity-30 z-50">
          <div className="absolute right-0 top-0 h-full w-full max-w-md bg-white shadow-2xl border-l-2 border-gray-300 overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6 pb-4 border-b border-gray-200">
                <h3 className="text-xl font-bold text-gray-800">Edit User</h3>
                <button
                  onClick={() => {
                    setShowEditForm(false);
                    setEditingUser(null);
                  }}
                  className="text-gray-500 hover:text-gray-700 text-xl"
                >
                  <i className="fas fa-times"></i>
                </button>
              </div>
              
              <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-sm text-blue-800">
                  <strong>User ID:</strong> {editingUser.user_id || editingUser.id}
                </p>
                <p className="text-sm text-blue-800">
                  <strong>Email:</strong> {editingUser.email || editingUser.username}@cisa.dhs.gov
                </p>
                <p className="text-sm text-blue-600">
                  <strong>Current Role:</strong> {getRoleDisplayName(editingUser.role)}
                </p>
              </div>

              <form onSubmit={handleUpdateUser} className="space-y-6">
                {/* Basic Information Section */}
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="text-lg font-semibold text-gray-800 mb-4">Basic Information</h4>
                  <div className="space-y-4">
                    <div className="form-group">
                      <label className="block text-sm font-medium text-gray-700 mb-2">Username</label>
                      <input
                        type="text"
                        value={editFormData.username}
                        onChange={(e) => setEditFormData({...editFormData, username: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label className="block text-sm font-medium text-gray-700 mb-2">Full Name</label>
                      <input
                        type="text"
                        value={editFormData.full_name}
                        onChange={(e) => setEditFormData({...editFormData, full_name: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label className="block text-sm font-medium text-gray-700 mb-2">Agency</label>
                      <input
                        type="text"
                        value={editFormData.agency}
                        onChange={(e) => setEditFormData({...editFormData, agency: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="e.g., CISA, DHS"
                      />
                    </div>
                  </div>
                </div>

                {/* Role and Permissions Section */}
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="text-lg font-semibold text-gray-800 mb-4">Role & Permissions</h4>
                  <div className="space-y-4">
                    <div className="form-group">
                      <label className="block text-sm font-medium text-gray-700 mb-2">Role (User Group)</label>
                      <select
                        value={editFormData.role}
                        onChange={(e) => setEditFormData({...editFormData, role: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                      >
                        <optgroup label="Administrative Roles (Full Access)">
                          <option value="admin">Administrator - Full system access</option>
                          <option value="spsa">SPSA (Supervisory PSA) - Full system access</option>
                        </optgroup>
                        <optgroup label="Standard User Role">
                          <option value="psa">PSA (Protective Security Advisor) - Standard user</option>
                        </optgroup>
                      </select>
                      <div className="mt-2 p-3 rounded-md" style={{
                        backgroundColor: (['admin', 'spsa'].includes(editFormData.role)) ? '#e6f6ea' : '#e3f2fd',
                        border: `2px solid ${(['admin', 'spsa'].includes(editFormData.role)) ? '#00a651' : '#2196f3'}`
                      }}>
                        <div className="text-sm font-semibold mb-2" style={{
                          color: (['admin', 'spsa'].includes(editFormData.role)) ? '#007a3d' : '#1565c0'
                        }}>
                          Permissions for this role:
                        </div>
                        {['admin', 'spsa'].includes(editFormData.role) ? (
                          <ul className="text-sm text-green-700 space-y-1 list-disc list-inside">
                            <li>Full admin panel access</li>
                            <li>User management (create, edit, delete users)</li>
                            <li>Submission review and approval</li>
                            <li>Audit trail access</li>
                            <li>System monitoring and controls</li>
                            <li>Learning metrics dashboard</li>
                            <li>All administrative functions</li>
                          </ul>
                        ) : (
                          <ul className="text-sm text-blue-700 space-y-1 list-disc list-inside">
                            <li>Submit documents and vulnerabilities</li>
                            <li>View approved production data</li>
                            <li>View own submissions</li>
                            <li>No admin panel access</li>
                            <li>No user management</li>
                            <li>No system controls</li>
                          </ul>
                        )}
                      </div>
                    </div>

                    <div className="form-group">
                      <label className="flex items-center p-3 bg-white border border-gray-300 rounded-md hover:bg-gray-50 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={editFormData.is_active}
                          onChange={(e) => setEditFormData({...editFormData, is_active: e.target.checked})}
                          className="mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                        <span className="text-sm font-medium text-gray-700">User is Active</span>
                      </label>
                    </div>
                  </div>
                </div>

                {/* Security Section */}
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="text-lg font-semibold text-gray-800 mb-4">Security Settings</h4>
                  <div className="space-y-4">
                    <div className="form-group">
                      <label className="block text-sm font-medium text-gray-700 mb-2">New Password (optional)</label>
                      <input
                        type="password"
                        value={editFormData.password}
                        onChange={(e) => setEditFormData({...editFormData, password: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Leave blank to keep current password"
                        autoComplete="new-password"
                      />
                    </div>

                    <div className="form-group">
                      <label className="flex items-center p-3 bg-white border border-gray-300 rounded-md hover:bg-gray-50 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={editFormData.force_password_change}
                          onChange={(e) => setEditFormData({...editFormData, force_password_change: e.target.checked})}
                          className="mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                        <span className="text-sm font-medium text-gray-700">Force password change at next login</span>
                      </label>
                    </div>
                  </div>
                </div>

                <div className="flex gap-3 pt-6 border-t border-gray-200">
                  <button 
                    type="submit" 
                    className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
                  >
                    <i className="fas fa-save mr-2"></i>
                    Update User
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowEditForm(false);
                      setEditingUser(null);
                    }}
                    className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 font-medium"
                  >
                    <i className="fas fa-times mr-2"></i>
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Role Groups Summary */}
      <div className="card mb-6">
        <div className="card-header">
          <h2 className="card-title">Role Groups & Permissions</h2>
        </div>
        <div className="card-body">
          <div className="grid md:grid-cols-2 gap-4">
            {/* Admin Group */}
            <div className="border-2 border-green-500 rounded-lg p-4 bg-green-50">
              <h3 className="text-lg font-bold text-green-800 mb-3">Administrative Roles (Full Access)</h3>
              <div className="space-y-3">
                <div>
                  <div className="font-semibold text-green-900">Administrator</div>
                  <div className="text-sm text-green-700">Full system access, all administrative permissions</div>
                </div>
                <div>
                  <div className="font-semibold text-green-900">SPSA (Supervisory PSA)</div>
                  <div className="text-sm text-green-700">Full system access, all administrative permissions</div>
                </div>
              </div>
              <div className="mt-3 pt-3 border-t border-green-300">
                <div className="text-xs font-semibold text-green-800 mb-1">Full Admin Permissions:</div>
                <ul className="text-xs text-green-700 space-y-1 list-disc list-inside">
                  <li>Admin panel access</li>
                  <li>User management (create, edit, delete)</li>
                  <li>Submission review and approval</li>
                  <li>Audit trail access</li>
                  <li>System monitoring and controls</li>
                  <li>Learning metrics dashboard</li>
                  <li>All administrative functions</li>
                </ul>
              </div>
            </div>

            {/* User Group */}
            <div className="border-2 border-blue-500 rounded-lg p-4 bg-blue-50">
              <h3 className="text-lg font-bold text-blue-800 mb-3">Standard User Role</h3>
              <div className="space-y-3">
                <div>
                  <div className="font-semibold text-blue-900">PSA (Protective Security Advisor)</div>
                  <div className="text-sm text-blue-700">Standard user, can submit documents and view data</div>
                </div>
              </div>
              <div className="mt-3 pt-3 border-t border-blue-300">
                <div className="text-xs font-semibold text-blue-800 mb-1">Standard User Permissions:</div>
                <ul className="text-xs text-blue-700 space-y-1 list-disc list-inside">
                  <li>Submit documents and vulnerabilities</li>
                  <li>View approved production data</li>
                  <li>View own submissions</li>
                  <li>No admin panel access</li>
                  <li>No user management</li>
                  <li>No system controls</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">All Users ({users.length})</h2>
        </div>
        <div className="card-body">
          {/* Desktop Table View */}
          <div className="hidden lg:block overflow-x-auto">
            <table className="table w-full">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Organization</th>
                  <th>Status</th>
                  <th>Last Sign In</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.user_id}>
                    <td>
                      <strong>{user.username}</strong>
                    </td>
                    <td>
                      {user.full_name}
                    </td>
                    <td>{user.username}@cisa.dhs.gov</td>
                    <td>
                      <span className={`badge ${getRoleBadgeColor(user.role)} text-white`}>
                        {getRoleDisplayName(user.role)}
                      </span>
                      {['admin', 'spsa'].includes(user.role) && (
                        <span className="ml-2 text-xs text-green-600 font-semibold">(Admin)</span>
                      )}
                    </td>
                    <td>{user.agency}</td>
                    <td>
                      <span className={`badge ${user.is_active ? 'bg-success' : 'bg-danger'} text-white`}>
                        {user.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>
                      {user.last_login 
                        ? new Date(user.last_login).toLocaleDateString()
                        : 'Never'
                      }
                    </td>
                    <td>
                      <div className="flex flex-wrap gap-1">
                        <button
                          onClick={() => {
                            console.log('🔧 Edit button clicked for user:', user);
                            handleEditUser(user);
                          }}
                          className="btn btn-sm btn-info"
                          title="Edit User"
                        >
                          <i className="fas fa-edit"></i>
                        </button>
                        <button
                          onClick={() => handleChangePassword(user.user_id)}
                          className="btn btn-sm btn-warning"
                          title="Change Password"
                        >
                          <i className="fas fa-key"></i>
                        </button>
                        <button
                          onClick={() => handleForcePasswordChange(user.user_id, !user.force_password_change)}
                          className={`btn btn-sm ${user.force_password_change ? 'btn-danger' : 'btn-secondary'}`}
                          title={user.force_password_change ? 'Remove Force Password Change' : 'Force Password Change at Next Login'}
                        >
                          <i className={`fas ${user.force_password_change ? 'fa-unlock' : 'fa-lock'}`}></i>
                        </button>
                        <button
                          onClick={() => handleToggleActive(user.user_id, user.is_active)}
                          className={`btn btn-sm ${user.is_active ? 'btn-warning' : 'btn-success'}`}
                          title={user.is_active ? 'Deactivate User' : 'Activate User'}
                        >
                          <i className={`fas ${user.is_active ? 'fa-user-slash' : 'fa-user-check'}`}></i>
                        </button>
                        <button
                          onClick={() => handleDeleteUser(user.user_id)}
                          className="btn btn-sm btn-danger"
                          title="Delete User"
                        >
                          <i className="fas fa-trash"></i>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile Card View */}
          <div className="lg:hidden space-y-4">
            {users.map((user) => (
              <div key={user.user_id} className="border rounded-lg p-4 bg-gray-50">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h3 className="font-semibold text-lg">{user.full_name}</h3>
                    <p className="text-gray-600">@{user.username}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`badge ${getRoleBadgeColor(user.role)} text-white`}>
                      {getRoleDisplayName(user.role)}
                    </span>
                    {['admin', 'spsa'].includes(user.role) && (
                      <span className="text-xs text-green-600 font-semibold">(Admin)</span>
                    )}
                  </div>
                </div>
                
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
                  <div>
                    <p className="text-sm text-gray-500">Email</p>
                    <p className="text-sm">{user.username}@cisa.dhs.gov</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Organization</p>
                    <p className="text-sm">{user.agency || 'CISA'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Status</p>
                    <span className={`badge ${user.is_active ? 'bg-success' : 'bg-danger'} text-white`}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Last Sign In</p>
                    <p className="text-sm">
                      {user.last_login 
                        ? new Date(user.last_login).toLocaleDateString()
                        : 'Never'
                      }
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-1">
                  <button
                    onClick={() => handleEditUser(user)}
                    className="btn btn-sm btn-info"
                    title="Edit User"
                  >
                    <i className="fas fa-edit"></i>
                  </button>
                  <button
                    onClick={() => handleChangePassword(user.user_id)}
                    className="btn btn-sm btn-warning"
                    title="Change Password"
                  >
                    <i className="fas fa-key"></i>
                  </button>
                  <button
                    onClick={() => handleForcePasswordChange(user.user_id, !user.force_password_change)}
                    className={`btn btn-sm ${user.force_password_change ? 'btn-danger' : 'btn-secondary'}`}
                    title={user.force_password_change ? 'Remove Force Password Change' : 'Force Password Change at Next Login'}
                  >
                    <i className={`fas ${user.force_password_change ? 'fa-unlock' : 'fa-lock'}`}></i>
                  </button>
                  <button
                    onClick={() => handleToggleActive(user.user_id, user.is_active)}
                    className={`btn btn-sm ${user.is_active ? 'btn-warning' : 'btn-success'}`}
                    title={user.is_active ? 'Deactivate User' : 'Activate User'}
                  >
                    <i className={`fas ${user.is_active ? 'fa-user-slash' : 'fa-user-check'}`}></i>
                  </button>
                  <button
                    onClick={() => handleDeleteUser(user.user_id)}
                    className="btn btn-sm btn-danger"
                    title="Delete User"
                  >
                    <i className="fas fa-trash"></i>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
