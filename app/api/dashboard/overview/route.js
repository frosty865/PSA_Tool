/**
 * Admin Dashboard Overview API
 * Returns statistics and softmatch data for the admin dashboard
 */

import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { supabaseAdmin } from '@/app/lib/supabase-admin.js';

export async function GET(request) {
  try {
    // Get all cookies and find Supabase session
    const cookieStore = cookies();
    
    // Find Supabase auth token cookie - check for the cookie names set by login route
    let accessToken = null;
    
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

    // If no token found, return unauthorized
    if (!accessToken) {
      return NextResponse.json(
        { error: 'Unauthorized - No session found' },
        { status: 401 }
      );
    }

    // Verify token and get user
    if (!supabaseAdmin) {
      return NextResponse.json(
        { error: 'Server configuration error' },
        { status: 500 }
      );
    }

    const { data: { user }, error: userError } = await supabaseAdmin.auth.getUser(accessToken);
    
    if (userError || !user) {
      return NextResponse.json(
        { error: 'Unauthorized - Invalid session' },
        { status: 401 }
      );
    }

    // Check if user is admin
    const { data: profile, error: profileError } = await supabaseAdmin
      .from('users_profiles')
      .select('role')
      .eq('id', user.id)
      .single();

    // Enhanced error logging for debugging
    if (profileError) {
      console.error('[Dashboard Overview] Profile error:', profileError);
    }
    
    if (!profile) {
      console.error('[Dashboard Overview] No profile found for user:', user.id);
      return NextResponse.json(
        { error: 'Unauthorized - User profile not found' },
        { status: 403 }
      );
    }
    
    console.log('[Dashboard Overview] User role:', profile.role);
    
    if (!['admin', 'spsa', 'psa', 'analyst'].includes(profile.role)) {
      console.error('[Dashboard Overview] Insufficient role. User role:', profile.role, 'Required: admin, spsa, psa, or analyst');
      return NextResponse.json(
        { error: 'Unauthorized - Admin access required', userRole: profile.role },
        { status: 403 }
      );
    }

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

