// Admin stats API - uses service role key to bypass RLS
import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { supabaseAdmin } from '@/app/lib/supabase-admin.js';

export async function GET(request) {
  try {
    // Get all cookies and find Supabase session
    const cookieStore = cookies();
    const allCookies = cookieStore.getAll();
    
    // Find Supabase auth token cookie (format: sb-{project-ref}-auth-token)
    let accessToken = null;
    for (const cookie of allCookies) {
      if (cookie.name.includes('auth-token') || cookie.name.includes('access-token')) {
        try {
          // Supabase stores tokens in JSON format in cookies
          const tokenData = JSON.parse(cookie.value);
          accessToken = tokenData.access_token || tokenData;
          break;
        } catch {
          // If not JSON, use directly
          accessToken = cookie.value;
          break;
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

    // Verify token and get user using admin client
    const { data: { user }, error: userError } = await supabaseAdmin.auth.getUser(accessToken);
    
    if (userError || !user) {
      return NextResponse.json(
        { error: 'Unauthorized - Invalid session' },
        { status: 401 }
      );
    }

    // Check if user is admin by fetching their profile using admin client
    const { data: profile, error: profileError } = await supabaseAdmin
      .from('user_profiles')
      .select('role')
      .eq('id', user.id)
      .single();

    if (profileError || !profile || !['admin', 'spsa', 'psa', 'analyst'].includes(profile.role)) {
      return NextResponse.json(
        { error: 'Unauthorized - Admin access required' },
        { status: 403 }
      );
    }

    // Fetch stats using admin client (bypasses RLS)
    const [vulnerabilitiesResult, ofcsResult, usersResult] = await Promise.all([
      supabaseAdmin
        .from('vulnerabilities')
        .select('*', { count: 'exact', head: true })
        .catch(err => ({ data: null, error: err, count: 0 })),
      supabaseAdmin
        .from('options_for_consideration')
        .select('*', { count: 'exact', head: true })
        .catch(err => ({ data: null, error: err, count: 0 })),
      supabaseAdmin
        .from('user_profiles')
        .select('*', { count: 'exact' })
        .catch(err => ({ data: [], error: err, count: 0 }))
    ]);

    const stats = {
      vulnerabilities: vulnerabilitiesResult.count || 0,
      ofcs: ofcsResult.count || 0,
      users: usersResult.count || usersResult.data?.length || 0,
      pendingVulnerabilities: 0,
      pendingOFCs: 0,
      errors: {
        vulnerabilities: vulnerabilitiesResult.error?.message,
        ofcs: ofcsResult.error?.message,
        users: usersResult.error?.message
      }
    };

    return NextResponse.json({ success: true, stats });
  } catch (error) {
    console.error('Error fetching admin stats:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error.message },
      { status: 500 }
    );
  }
}

