// Updated to use Supabase authentication instead of JWT
import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { supabaseAdmin } from '@/app/lib/supabase-admin.js';

export async function GET(request) {
  try {
    // Get token from Authorization header (required - Navigation sends this)
    let accessToken = null;
    const authHeader = request.headers.get('authorization');
    
    if (authHeader && authHeader.toLowerCase().startsWith('bearer ')) {
      accessToken = authHeader.slice(7).trim();
    }

    // Fallback to cookies only if header not provided (for compatibility)
    if (!accessToken) {
      const cookieStore = cookies();
      const allCookies = cookieStore.getAll();
      for (const cookie of allCookies) {
        // Check for Supabase auth cookies
        if (cookie.name.startsWith('sb-') && cookie.name.includes('-auth-token')) {
          try {
            const tokenData = JSON.parse(cookie.value);
            accessToken = tokenData?.access_token || tokenData;
            break;
          } catch {
            accessToken = cookie.value;
            break;
          }
        }
      }
    }

    if (!accessToken) {
      console.error('[Auth Verify] No access token found in header or cookies');
      return NextResponse.json(
        { success: false, error: 'No authentication token provided' },
        { status: 401 }
      );
    }

    // Verify token and get user using admin client
    // Note: getUser() with a JWT token validates it and returns user info
    const { data: { user }, error: userError } = await supabaseAdmin.auth.getUser(accessToken);
    
    if (userError) {
      console.error('[Auth Verify] Token validation error:', userError.message);
      return NextResponse.json(
        { success: false, error: `Token validation failed: ${userError.message}` },
        { status: 401 }
      );
    }
    
    if (!user) {
      console.error('[Auth Verify] No user returned from token validation');
      return NextResponse.json(
        { success: false, error: 'Invalid token - no user found' },
        { status: 401 }
      );
    }

    // Get user profile (role only - is_admin column doesn't exist in your schema)
    // Prefer join by user_id (your schema) and fall back to id
    let { data: profile } = await supabaseAdmin
      .from('user_profiles')
      .select('role, first_name, last_name, organization, user_id')
      .eq('user_id', user.id)
      .maybeSingle();
    if (!profile) {
      const resp = await supabaseAdmin
        .from('user_profiles')
        .select('role, first_name, last_name, organization, user_id')
        .eq('id', user.id)
        .maybeSingle();
      profile = resp.data || null;
    }

    // Derive role with robust fallbacks
    let derivedRole = String(
      profile?.role || user.user_metadata?.role || 'user'
    ).toLowerCase();
    
    // Determine admin status: role-based or email allowlist (is_admin column doesn't exist)
    let isUserAdmin = false;
    
    // Final fallback: allow admin via configured email allowlist (comma-separated) or user.user_metadata.is_admin
    if (derivedRole === 'user') {
      const allowlist = (process.env.ADMIN_EMAILS || '').toLowerCase().split(',').map(s=>s.trim()).filter(Boolean);
      if (allowlist.includes(String(user.email).toLowerCase())) {
        derivedRole = 'admin';
        isUserAdmin = true;
      }
    }
    
    // Also check if role itself indicates admin
    if (['admin', 'spsa'].includes(derivedRole)) {
      isUserAdmin = true;
    }
    
    // Check user_metadata for is_admin flag
    if (user.user_metadata?.is_admin) {
      isUserAdmin = true;
      if (derivedRole === 'user') {
        derivedRole = 'admin';
      }
    }

    const userResponse = {
      success: true,
      user: {
        id: user.id,
        email: user.email,
        role: derivedRole,
        name: (profile?.first_name || '') + (profile?.last_name ? ' ' + profile?.last_name : '') || user.user_metadata?.name || user.email,
        is_admin: isUserAdmin
      }
    };
    
    console.log('[Auth Verify] Success:', { 
      email: user.email, 
      role: derivedRole, 
      is_admin: isUserAdmin,
      profileRole: profile?.role,
      userMetadataRole: user.user_metadata?.role,
      userMetadataIsAdmin: user.user_metadata?.is_admin
    });
    return NextResponse.json(userResponse);

  } catch (error) {
    console.error('[Auth Verify] Unexpected error:', error);
    return NextResponse.json(
      { success: false, error: `Token verification failed: ${error.message}` },
      { status: 401 }
    );
  }
}
