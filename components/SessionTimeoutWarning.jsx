'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/app/lib/supabase-client';

/**
 * SessionTimeoutWarning Component
 * Warns users when their session is about to expire
 * and handles automatic logout on session expiration
 */
export default function SessionTimeoutWarning() {
  const [showWarning, setShowWarning] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState(null);
  const router = useRouter();

  useEffect(() => {
    // Only run on client side
    if (typeof window === 'undefined') return;

    // Check session periodically
    const checkSession = async () => {
      try {
        if (!supabase || !supabase.auth) return;

        const { data: { session }, error } = await supabase.auth.getSession();
        
        if (error || !session) {
          // Session expired or invalid
          setShowWarning(false);
          return;
        }

        // Check if token is about to expire (within 5 minutes)
        const expiresAt = session.expires_at;
        if (expiresAt) {
          const expiresIn = expiresAt - Math.floor(Date.now() / 1000);
          
          if (expiresIn < 0) {
            // Already expired
            await supabase.auth.signOut();
            router.push('/splash');
            return;
          }
          
          if (expiresIn < 300) { // 5 minutes
            setShowWarning(true);
            setTimeRemaining(Math.floor(expiresIn / 60)); // minutes
          } else {
            setShowWarning(false);
          }
        }
      } catch (err) {
        console.error('[SessionTimeoutWarning] Error:', err);
      }
    };

    // Check immediately
    checkSession();
    
    // Check every minute
    const interval = setInterval(checkSession, 60000);
    
    return () => clearInterval(interval);
  }, [router]);

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
        Your session will expire in {timeRemaining} minute{timeRemaining !== 1 ? 's' : ''}.
        Your work is being saved automatically.
      </p>
    </div>
  );
}

