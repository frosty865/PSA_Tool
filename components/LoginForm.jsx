'use client';

import { useState } from 'react';
import { supabase } from '@/app/lib/supabase-client.js';

export default function LoginForm() {
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
  const [loading, setLoading] = useState(false);
  const [user, setUser] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // Convert username to email if needed, or use email directly
      const email = formData.username.includes('@') 
        ? formData.username 
        : `${formData.username}@vofc.gov`;

      // Use Supabase authentication
      const { data, error: authError } = await supabase.auth.signInWithPassword({
        email: email,
        password: formData.password
      });

      if (authError) {
        setError(authError.message || 'Login failed');
        return;
      }

      if (data?.user) {
        // Get user profile to check role
        const { data: profile } = await supabase
          .from('user_profiles')
          .select('*')
          .eq('id', data.user.id)
          .single();

        const userRole = profile?.role || data.user.user_metadata?.role || 'user';
        const userName = profile?.full_name || data.user.user_metadata?.name || data.user.email;

        setUser({
          id: data.user.id,
          email: data.user.email,
          role: userRole,
          name: userName,
          full_name: userName
        });

        // Redirect based on role
        if (['admin', 'spsa', 'psa', 'analyst'].includes(userRole)) {
          window.location.href = '/admin';
        } else {
          window.location.href = '/';
        }
      }
    } catch (error) {
      setError(`Login failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await supabase.auth.signOut();
      localStorage.removeItem('user');
      setUser(null);
      setFormData({ username: '', password: '' });
      window.location.href = '/splash';
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  if (user) {
    return (
      <div className="card">
        <div className="card-header">
          <h5 className="card-title">Welcome, {user.full_name}!</h5>
        </div>
        <div className="card-body">
          <div className="alert alert-success">
            <p><strong>Role:</strong> {user.role}</p>
            <p><strong>Agency:</strong> {user.agency || 'N/A'}</p>
            <p><strong>Username:</strong> {user.username}</p>
          </div>
          <button onClick={handleLogout} className="btn btn-secondary">
            Logout
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">
        <h5 className="card-title">VOFC User Login</h5>
      </div>
      <div className="card-body">
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username" className="form-label">
              Username
            </label>
            <input
              id="username"
              name="username"
              type="text"
              value={formData.username}
              onChange={handleChange}
              className="form-input"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password" className="form-label">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              value={formData.password}
              onChange={handleChange}
              className="form-input"
              required
            />
          </div>

          {error && (
            <div className="alert alert-danger">
              {error}
            </div>
          )}

          <div className="text-center">
            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary"
            >
              {loading ? 'Logging in...' : 'Login'}
            </button>
          </div>
        </form>

        <div className="alert alert-info mt-3">
          <h6>Available Users:</h6>
          <ul className="mb-0">
            <li><strong>admin</strong> or <strong>admin@vofc.gov</strong> - Administrator (Password: Admin123!)</li>
            <li><strong>spsa</strong> or <strong>spsa@vofc.gov</strong> - Senior PSA (Password: Admin123!)</li>
            <li><strong>psa</strong> or <strong>psa@vofc.gov</strong> - PSA (Password: Admin123!)</li>
            <li><strong>analyst</strong> or <strong>analyst@vofc.gov</strong> - Analyst (Password: Admin123!)</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
