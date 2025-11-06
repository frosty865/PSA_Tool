'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/app/lib/supabase-client';

/**
 * SessionTimeoutWarning Component
 * Warns users when their session is about to expire or after inactivity
 * and handles automatic logout on session expiration
 */
export default function SessionTimeoutWarning() {
  const [showWarning, setShowWarning] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState(null);
  const [warningType, setWarningType] = useState('token'); // 'token' or 'inactivity'
  const router = useRouter();
  const lastActivityRef = useRef(Date.now());
  const warningTimeoutRef = useRef(null);
  const logoutTimeoutRef = useRef(null);
  const warningTypeRef = useRef('token'); // Track warning type in ref for use in callbacks

  // Inactivity timeout: 30 minutes (configurable via env or default)
  const INACTIVITY_TIMEOUT = (process.env.NEXT_PUBLIC_INACTIVITY_TIMEOUT 
    ? parseInt(process.env.NEXT_PUBLIC_INACTIVITY_TIMEOUT, 10) 
    : 30) * 60 * 1000; // Convert to milliseconds
  
  const WARNING_BEFORE_TIMEOUT = 5 * 60 * 1000; // Show warning 5 minutes before timeout

  useEffect(() => {
    // Only run on client side
    if (typeof window === 'undefined') return;

    // Track user activity
    const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
    const updateActivity = () => {
      lastActivityRef.current = Date.now();
      // Reset inactivity warnings if user becomes active
      // We'll check this in the checkSession function instead
    };

    // Add activity listeners
    activityEvents.forEach(event => {
      window.addEventListener(event, updateActivity, { passive: true });
    });

    // Check session and inactivity periodically
    const checkSession = async () => {
      try {
        if (!supabase || !supabase.auth) return;

        const { data: { session }, error } = await supabase.auth.getSession();
        
        if (error || !session) {
          // Session expired or invalid
          setShowWarning(false);
          return;
        }

        const now = Date.now();
        const timeSinceActivity = now - lastActivityRef.current;

        // Check inactivity timeout
        if (timeSinceActivity >= INACTIVITY_TIMEOUT) {
          // User inactive - logout immediately
          await supabase.auth.signOut();
          await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => {});
          router.push('/splash');
          return;
        }

        // Check if approaching inactivity timeout
        if (timeSinceActivity >= (INACTIVITY_TIMEOUT - WARNING_BEFORE_TIMEOUT)) {
          const remainingMs = INACTIVITY_TIMEOUT - timeSinceActivity;
          warningTypeRef.current = 'inactivity';
          setWarningType('inactivity');
          setShowWarning(true);
          setTimeRemaining(Math.ceil(remainingMs / 60000)); // minutes
          
          // Set logout timeout
          if (logoutTimeoutRef.current) clearTimeout(logoutTimeoutRef.current);
          logoutTimeoutRef.current = setTimeout(async () => {
            await supabase.auth.signOut();
            await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => {});
            router.push('/splash');
          }, remainingMs);
          return;
        } else if (warningTypeRef.current === 'inactivity') {
          // User became active again - clear inactivity warning
          warningTypeRef.current = 'token';
          setShowWarning(false);
          setTimeRemaining(null);
          setWarningType('token');
          if (warningTimeoutRef.current) clearTimeout(warningTimeoutRef.current);
          if (logoutTimeoutRef.current) clearTimeout(logoutTimeoutRef.current);
        }

        // Check if token is about to expire (within 5 minutes)
        const expiresAt = session.expires_at;
        if (expiresAt) {
          const expiresIn = expiresAt - Math.floor(Date.now() / 1000);
          
          if (expiresIn < 0) {
            // Already expired
            await supabase.auth.signOut();
            await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => {});
            router.push('/splash');
            return;
          }
          
          if (expiresIn < 300 && timeSinceActivity < (INACTIVITY_TIMEOUT - WARNING_BEFORE_TIMEOUT)) {
            // Token expiring but not inactive
            warningTypeRef.current = 'token';
            setWarningType('token');
            setShowWarning(true);
            setTimeRemaining(Math.floor(expiresIn / 60)); // minutes
          } else if (expiresIn >= 300 && warningTypeRef.current === 'token') {
            setShowWarning(false);
            setTimeRemaining(null);
          }
        }
      } catch (err) {
        console.error('[SessionTimeoutWarning] Error:', err);
      }
    };

    // Check immediately
    checkSession();
    
    // Check every 30 seconds for more responsive inactivity detection
    const interval = setInterval(checkSession, 30000);
    
    return () => {
      clearInterval(interval);
      activityEvents.forEach(event => {
        window.removeEventListener(event, updateActivity);
      });
      if (warningTimeoutRef.current) clearTimeout(warningTimeoutRef.current);
      if (logoutTimeoutRef.current) clearTimeout(logoutTimeoutRef.current);
    };
  }, [router, INACTIVITY_TIMEOUT, WARNING_BEFORE_TIMEOUT]);

  // Auto-refresh session when warning shows
  useEffect(() => {
    if (showWarning && supabase && supabase.auth) {
      const refreshSession = async () => {
        try {
          const { data: { session }, error } = await supabase.auth.refreshSession();
          if (!error && session) {
            setShowWarning(false);
            setTimeRemaining(null);
          }
        } catch (err) {
          console.error('[SessionTimeoutWarning] Refresh error:', err);
        }
      };
      
      // Try to refresh session
      refreshSession();
    }
  }, [showWarning]);

  if (!showWarning || !timeRemaining) {
    return null;
  }

  return (
    <div style={{
      position: 'fixed',
      top: '20px',
      right: '20px',
      zIndex: 10000,
      backgroundColor: '#fff3cd',
      border: '2px solid #ffc107',
      borderRadius: '8px',
      padding: '16px',
      boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
      maxWidth: '300px'
    }}>
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        marginBottom: '8px'
      }}>
        <strong style={{ color: '#856404' }}>
          ⚠️ Session Expiring Soon
        </strong>
        <button
          onClick={() => setShowWarning(false)}
          style={{
            background: 'none',
            border: 'none',
            fontSize: '18px',
            cursor: 'pointer',
            color: '#856404'
          }}
        >
          ×
        </button>
      </div>
      <p style={{ 
        margin: 0, 
        fontSize: '14px', 
        color: '#856404' 
      }}>
        {warningType === 'inactivity' 
          ? `You've been inactive. Your session will expire in ${timeRemaining} minute${timeRemaining !== 1 ? 's' : ''}.`
          : `Your session will expire in ${timeRemaining} minute${timeRemaining !== 1 ? 's' : ''}.`
        }
        {warningType === 'inactivity' && (
          <span style={{ display: 'block', marginTop: '8px', fontSize: '12px' }}>
            Move your mouse or click anywhere to stay logged in.
          </span>
        )}
      </p>
    </div>
  );
}

