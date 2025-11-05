'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser, logout } from '../lib/auth';
import { supabase } from '@/app/lib/supabase-client.js';
import { trackVOFCEvent } from '../../components/AnalyticsProvider';
// import SessionTimeoutWarning from '../../components/SessionTimeoutWarning';
import '@/styles/cisa.css';

export default function SplashPage() {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const router = useRouter();

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const currentUser = await getCurrentUser();
      if (currentUser) {
        setUser(currentUser);
        // Redirect to dashboard if already logged in
        router.push('/');
        return;
      }
    } catch (error) {
      // This is expected when no user is logged in
      console.log('No user logged in - showing login form');
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const email = formData.get('email');
    const password = formData.get('password');

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      });

      const result = await response.json();

      if (result.success) {
        // Hydrate client session to prevent redirect loops
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
        // small delay to ensure session is ready, then refresh
        await new Promise(r => setTimeout(r, 150));
        try { router.refresh(); } catch {}
        // Track successful login
        trackVOFCEvent.login(result.user?.role || 'unknown');
        // Redirect to dashboard - no localStorage needed
        router.push('/');
      } else {
        // Track failed login
        trackVOFCEvent.error('login_failed', { email, error: result.error });
        alert('Login failed: ' + result.error);
      }
    } catch (error) {
      console.error('Login error:', error);
      alert('Login failed. Please try again.');
    }
  };

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'var(--cisa-gray-lighter)',
        fontFamily: 'var(--font-family)'
      }}>
        <div className="text-center">
          <div style={{
            width: '48px',
            height: '48px',
            border: '4px solid var(--cisa-gray-light)',
            borderTop: '4px solid var(--cisa-blue)',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 16px'
          }}></div>
          <p style={{ color: 'var(--cisa-gray)', fontSize: 'var(--font-size-base)' }}>Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, var(--cisa-blue-lightest) 0%, var(--cisa-white) 50%, var(--cisa-blue-lightest) 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '48px 16px',
      fontFamily: 'var(--font-family)'
    }}>
      {/* <SessionTimeoutWarning /> */}
      <div style={{ maxWidth: '500px', width: '100%' }}>
        {/* Header Section */}
        <div className="text-center" style={{ marginBottom: '32px' }}>
          {/* Official CISA Logo */}
          <div style={{ marginBottom: '32px' }}>
            <img
              src="/images/cisa-logo.png"
              alt="CISA Logo"
              style={{ height: '96px', width: 'auto', margin: '0 auto' }}
            />
          </div>

          <h1 style={{
            fontSize: 'var(--font-size-xxl)',
            fontWeight: '700',
            color: 'var(--cisa-blue)',
            marginBottom: '8px'
          }}>
            VOFC System
          </h1>
          <p style={{
            fontSize: 'var(--font-size-lg)',
            color: 'var(--cisa-gray)',
            marginBottom: '8px',
            fontWeight: '500'
          }}>
            Vulnerabilities and Options for Consideration
          </p>
          <p style={{
            fontSize: 'var(--font-size-sm)',
            color: 'var(--cisa-gray)',
            marginBottom: '16px'
          }}>
            Cybersecurity and Infrastructure Security Agency
          </p>
          <p style={{
            fontSize: 'var(--font-size-xs)',
            color: 'var(--cisa-gray)',
            opacity: '0.8'
          }}>
            Department of Homeland Security
          </p>
        </div>

        {/* Login Card */}
        <div className="card" style={{
          padding: '40px 32px',
          boxShadow: 'var(--shadow-lg)',
          border: '1px solid var(--cisa-gray-light)'
        }}>
          <div className="text-center" style={{ marginBottom: '24px' }}>
            <h2 style={{
              fontSize: 'var(--font-size-xl)',
              fontWeight: '600',
              color: 'var(--cisa-blue)',
              marginBottom: '8px'
            }}>
              Sign In
            </h2>
            <p style={{
              fontSize: 'var(--font-size-sm)',
              color: 'var(--cisa-gray)'
            }}>
              Access the VOFC System
            </p>
          </div>

          <form onSubmit={handleLogin} style={{ marginBottom: '32px' }}>
            <div className="form-group">
              <label htmlFor="email" className="form-label">
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                required
                autoComplete="email"
                className="form-input"
                placeholder="Enter your email"
                style={{
                  width: '100%',
                  padding: 'var(--spacing-md)',
                  border: '2px solid var(--cisa-gray-light)',
                  borderRadius: 'var(--border-radius)',
                  fontSize: 'var(--font-size-base)',
                  fontFamily: 'var(--font-family)',
                  transition: 'border-color 0.3s ease'
                }}
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
                required
                autoComplete="current-password"
                className="form-input"
                placeholder="Enter your password"
                style={{
                  width: '100%',
                  padding: 'var(--spacing-md)',
                  border: '2px solid var(--cisa-gray-light)',
                  borderRadius: 'var(--border-radius)',
                  fontSize: 'var(--font-size-base)',
                  fontFamily: 'var(--font-family)',
                  transition: 'border-color 0.3s ease'
                }}
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{
                width: '100%',
                padding: 'var(--spacing-md) var(--spacing-lg)',
                fontSize: 'var(--font-size-base)',
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 'var(--spacing-sm)'
              }}
            >
              <svg style={{ width: '20px', height: '20px' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
              </svg>
              Sign In
            </button>
          </form>

          <div className="text-center">
            <p style={{
              fontSize: 'var(--font-size-sm)',
              color: 'var(--cisa-gray)',
              marginBottom: '8px'
            }}>
              Need access? Contact your system administrator.
            </p>
            <p style={{
              fontSize: 'var(--font-size-xs)',
              color: 'var(--cisa-gray)',
              opacity: '0.8'
            }}>
              Sessions timeout after 5 minutes of inactivity
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center" style={{
          fontSize: 'var(--font-size-xs)',
          color: 'var(--cisa-gray)',
          opacity: '0.8',
          marginTop: '32px'
        }}>
          <p style={{ fontWeight: '600', marginBottom: '4px' }}>
            Cybersecurity and Infrastructure Security Agency
          </p>
          <p style={{ marginBottom: '16px' }}>
            Department of Homeland Security
          </p>
          <div style={{
            marginTop: '16px',
            paddingTop: '16px',
            borderTop: '1px solid var(--cisa-gray-light)'
          }}>
            <p style={{ color: 'var(--cisa-gray)', opacity: '0.6' }}>
              Official Government System
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
