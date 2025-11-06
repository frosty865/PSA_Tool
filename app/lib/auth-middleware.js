// Auth middleware for API routes
import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { supabaseAdmin } from '@/app/lib/supabase-admin.js';

/**
 * Middleware to require admin authentication
 * Returns { user, error: null } on success, { user: null, error: string } on failure
 */
export async function requireAdmin(request) {
  try {
    if (!supabaseAdmin) {
      return { user: null, error: 'Server configuration error: Supabase admin client not available' };
    }

    // Get token from Authorization header
    const authHeader = request.headers.get('authorization');
    let accessToken = null;
    
    if (authHeader && authHeader.toLowerCase().startsWith('bearer ')) {
      accessToken = authHeader.slice(7).trim();
    }

    // Fallback to cookies
    if (!accessToken) {
      try {
        const cookieStore = cookies();
        const sbAccessToken = cookieStore.get('sb-access-token');
        if (sbAccessToken) {
          accessToken = sbAccessToken.value;
        }
      } catch (cookieError) {
        // Cookies might not be available in some contexts
      }
    }

    if (!accessToken) {
      return { user: null, error: 'No authentication token provided' };
    }

    // Verify token and get user
    const { data: { user }, error: userError } = await supabaseAdmin.auth.getUser(accessToken);
    
    if (userError || !user) {
      return { user: null, error: 'Invalid authentication token' };
    }

    // Get user profile to check role
    let { data: profile } = await supabaseAdmin
      .from('users_profiles')
      .select('role')
      .eq('user_id', user.id)
      .maybeSingle();
    
    if (!profile) {
      const resp = await supabaseAdmin
        .from('users_profiles')
        .select('role')
        .eq('id', user.id)
        .maybeSingle();
      profile = resp.data || null;
    }

    const derivedRole = String(
      profile?.role || user.user_metadata?.role || 'user'
    ).toLowerCase();

    // Check admin status
    const allowlist = (process.env.ADMIN_EMAILS || '').toLowerCase().split(',').map(s => s.trim()).filter(Boolean);
    const isEmailAdmin = allowlist.includes(String(user.email).toLowerCase());
    const isMetadataAdmin = user.user_metadata?.is_admin || false;
    const isRoleAdmin = ['admin', 'spsa'].includes(derivedRole);

    if (!isEmailAdmin && !isMetadataAdmin && !isRoleAdmin) {
      return { user: null, error: 'Admin access required' };
    }

    return {
      user: {
        id: user.id,
        email: user.email,
        role: derivedRole,
        is_admin: true
      },
      error: null
    };
  } catch (error) {
    console.error('[Auth Middleware] Error:', error);
    return { user: null, error: `Authentication failed: ${error.message}` };
  }
}

