'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/app/lib/supabase-client.js';
import '@/styles/cisa.css';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [isSignUp, setIsSignUp] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isSignUp) {
        // For signup, we'll use username@vofc.gov as email
        const email = `${username}@vofc.gov`;
        const { error } = await supabase.auth.signUp({
          email,
          password,
        });
        if (error) throw error;
        alert('Check your email for the confirmation link!');
      } else {
        // For login, use our custom JWT authentication API
        // Allow full email or construct from username
        const email = username.includes('@') ? username : `${username}@vofc.gov`;
        
        console.log('Attempting login with:', { email: email.includes('@') ? email.substring(0, email.indexOf('@') + 5) + '...' : email.substring(0, 5) + '...', password: '***' });
        
        const response = await fetch('/api/auth/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify({ email, password }),
        });
        
        if (!response.ok) {
          const errorText = await response.text();
          let errorData;
          try {
            errorData = JSON.parse(errorText);
          } catch {
            errorData = { error: errorText || 'Login failed' };
          }
          console.error('Login API error:', { status: response.status, error: errorData });
          throw new Error(errorData.error || `Login failed (${response.status})`);
        }
        
        const result = await response.json();
        
        console.log('Login response:', { success: result.success, email: result.user?.email });
        
        if (!result.success) {
          throw new Error(result.error || 'Login failed');
        }
        
        console.log('Login successful:', result);

        // If API returned a Supabase session, hydrate client session to avoid redirect loops
        if (result.session?.access_token && result.session?.refresh_token) {
          try {
            await supabase.auth.setSession({
              access_token: result.session.access_token,
              refresh_token: result.session.refresh_token
            });
          } catch (e) {
            console.warn('Failed to set client session:', e);
          }
        }

        // Small delay to ensure session availability, then refresh and navigate
        await new Promise(resolve => setTimeout(resolve, 150));
        try { router.refresh(); } catch {}
        console.log('Redirecting to home page...');
        router.push('/');
      }
    } catch (error) {
      console.error('Login error:', error);
      alert('Error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--cisa-gray-lighter)'}}>
      <div style={{maxWidth: '448px', width: '100%'}}>
        <div className="card">
          <div className="card-header">
            <h1 className="card-title" style={{textAlign: 'center'}}>VOFC Viewer</h1>
            <p style={{textAlign: 'center', color: 'var(--cisa-gray)'}}>Sign in to access the system</p>
          </div>
          
          <div className="card-body">
            <form onSubmit={handleSubmit} style={{display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)'}}>
              <div className="form-group">
                <label className="form-label">Email or Username</label>
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="form-input"
                  placeholder="Enter your email or username"
                  autoComplete="username email"
                />
                <small style={{display: 'block', marginTop: 'var(--spacing-xs)', fontSize: 'var(--font-size-xs)', color: 'var(--cisa-gray)'}}>
                  If username, will use username@vofc.gov
                </small>
              </div>
              
              <div className="form-group">
                <label className="form-label">Password</label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="form-input"
                  placeholder="Enter your password"
                  autoComplete="current-password"
                />
              </div>
              
              <button
                type="submit"
                disabled={loading}
                className="btn btn-primary"
                style={{width: '100%'}}
              >
                {loading ? 'Loading...' : (isSignUp ? 'Sign Up' : 'Sign In')}
              </button>
            </form>
            
            <div style={{textAlign: 'center', marginTop: 'var(--spacing-md)'}}>
              <button
                type="button"
                onClick={() => setIsSignUp(!isSignUp)}
                className="btn btn-link"
              >
                {isSignUp ? 'Already have an account? Sign in' : "Don't have an account? Sign up"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
