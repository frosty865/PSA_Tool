/**
 * Admin Dashboard Overview API
 * Returns statistics and softmatch data for the admin dashboard
 */

import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { supabaseAdmin } from '@/app/lib/supabase-admin.js';

export async function GET(request) {
  try {
    if (!supabaseAdmin) {
      return NextResponse.json(
        { error: 'Server configuration error' },
        { status: 500 }
      );
    }

    // Get token from Authorization header first (preferred method)
    let accessToken = null;
    const authHeader = request.headers.get('authorization');
    
    if (authHeader && authHeader.toLowerCase().startsWith('bearer ')) {
      accessToken = authHeader.slice(7).trim();
    }

    // Fallback to cookies if no header
    if (!accessToken) {
      const cookieStore = cookies();
      
      // First try: sb-access-token (set by login route)
      const sbAccessToken = cookieStore.get('sb-access-token');
      if (sbAccessToken) {
        accessToken = sbAccessToken.value;
      }
      
      // Fallback: try other common cookie names
      if (!accessToken) {
        const allCookies = cookieStore.getAll();
        for (const cookie of allCookies) {
          if (cookie.name.includes('auth-token') || cookie.name.includes('access-token')) {
            try {
              const tokenData = JSON.parse(cookie.value);
              accessToken = tokenData.access_token || tokenData;
              break;
            } catch {
              accessToken = cookie.value;
              break;
            }
          }
        }
      }
    }

    // If no token found, return unauthorized
    if (!accessToken) {
      return NextResponse.json(
        { error: 'Unauthorized - No session found' },
        { status: 401 }
      );
    }

    // Verify token and get user
    const { data: { user }, error: userError } = await supabaseAdmin.auth.getUser(accessToken);
    
    if (userError || !user) {
      return NextResponse.json(
        { error: 'Unauthorized - Invalid session' },
        { status: 401 }
      );
    }

    // Check if user is admin - try both id and user_id columns
    let { data: profile, error: profileError } = await supabaseAdmin
      .from('users_profiles')
      .select('role, id, user_id, is_active')
      .eq('user_id', user.id)
      .maybeSingle();

    // Fallback: try id column if user_id didn't work
    if (!profile && profileError?.code === 'PGRST116') {
      const resp = await supabaseAdmin
        .from('users_profiles')
        .select('role, id, user_id, is_active')
        .eq('id', user.id)
        .maybeSingle();
      profile = resp.data || null;
      profileError = resp.error;
    }

    // Enhanced error logging for debugging
    if (profileError && profileError.code !== 'PGRST116') {
      console.error('[Dashboard Overview] Profile error:', profileError);
    }
    
    console.log('[Dashboard Overview] Profile lookup result:', {
      userId: user.id,
      userEmail: user.email,
      profileFound: !!profile,
      profileData: profile ? { role: profile.role, id: profile.id, user_id: profile.user_id, is_active: profile.is_active } : null,
      profileError: profileError?.code || profileError?.message || null
    });
    
    // Check admin status via multiple methods (like verify endpoint)
    const allowlist = (process.env.ADMIN_EMAILS || '').toLowerCase().split(',').map(s=>s.trim()).filter(Boolean);
    const isEmailAdmin = allowlist.includes(String(user.email).toLowerCase());
    const isMetadataAdmin = user.user_metadata?.is_admin || false;
    const metadataRole = String(user.user_metadata?.role || '').toLowerCase().trim();
    const isMetadataRoleAdmin = ['admin', 'spsa'].includes(metadataRole);
    
    console.log('[Dashboard Overview] Admin check:', {
      email: user.email,
      hasProfile: !!profile,
      profileRole: profile?.role,
      isEmailAdmin,
      isMetadataAdmin,
      metadataRole,
      isMetadataRoleAdmin,
      allowlist: allowlist.length > 0 ? 'configured' : 'empty'
    });
    
    // If no profile but user is admin via allowlist/metadata, allow access
    if (!profile && (isEmailAdmin || isMetadataAdmin || isMetadataRoleAdmin)) {
      console.log('[Dashboard Overview] Admin user without profile, allowing access:', user.email);
      // Set a default role for admin users without profile
      const finalRoleForAdmin = metadataRole || 'admin';
      const isAdmin = true;
      
      // Continue to return data (skip the role check below since we know they're admin)
      console.log('[Dashboard Overview] User authorized (admin via allowlist/metadata):', { email: user.email, role: finalRoleForAdmin, isAdmin });

      // Fetch stats and softmatch data
      const stats = [];
      const soft = [];

      return NextResponse.json({ 
        stats,
        soft 
      });
    } else if (!profile) {
      console.error('[Dashboard Overview] No profile found for user:', user.id, user.email);
      console.error('[Dashboard Overview] Admin check failed - not in allowlist and no metadata admin flag');
      return NextResponse.json(
        { error: 'Unauthorized - User profile not found' },
        { status: 403 }
      );
    }
    
    // Determine final role
    const finalRole = String(profile?.role || metadataRole || 'user').toLowerCase().trim();
    const isAdmin = isEmailAdmin || isMetadataAdmin || isMetadataRoleAdmin || ['admin', 'spsa', 'psa', 'analyst'].includes(finalRole);
    
    if (!isAdmin) {
      console.error('[Dashboard Overview] Insufficient role. User role:', finalRole, 'Required: admin, spsa, psa, or analyst');
      return NextResponse.json(
        { error: 'Unauthorized - Admin access required', userRole: finalRole },
        { status: 403 }
      );
    }
    
    console.log('[Dashboard Overview] User authorized:', { email: user.email, role: finalRole, isAdmin });

    // Fetch stats and softmatch data
    // For now, return empty arrays to prevent errors
    // This can be enhanced later with actual data from learning_events or processing runs
    const stats = [];
    const soft = [];

    // TODO: Populate stats from learning_events or processing runs
    // TODO: Populate soft from softmatch data

    return NextResponse.json({ 
      stats,
      soft 
    });
  } catch (error) {
    console.error('Error fetching dashboard overview:', error);
    return NextResponse.json(
      { 
        error: 'Internal server error', 
        details: error.message,
        stats: [],
        soft: []
      },
      { status: 500 }
    );
  }
}

