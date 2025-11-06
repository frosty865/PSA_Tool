import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/app/lib/supabase-admin.js';

export async function POST(request) {
  try {
    let requestData;
    try {
      requestData = await request.json();
    } catch (jsonError) {
      console.error('Login JSON parsing error:', jsonError);
      return NextResponse.json(
        { success: false, error: 'Invalid JSON in request body' },
        { status: 400 }
      );
    }
    
    const { email, password } = requestData;

    if (!email || !password) {
      return NextResponse.json(
        { success: false, error: 'Email and password are required' },
        { status: 400 }
      );
    }

    // Check if supabaseAdmin is available
    if (!supabaseAdmin) {
      console.error('[Login] supabaseAdmin is null - check SUPABASE_SERVICE_ROLE_KEY environment variable');
      return NextResponse.json(
        { success: false, error: 'Server configuration error: Supabase admin client not available. Check environment variables.' },
        { status: 500 }
      );
    }

    // Create service role client for authentication
    const serviceSupabase = supabaseAdmin;

    console.log('[Login] Attempting authentication for:', email);
    
    // Use service role for authentication
    const { data, error } = await serviceSupabase.auth.signInWithPassword({
      email,
      password
    });

    if (error) {
      console.error('[Login] Supabase auth error:', error);
      console.error('[Login] Error details:', {
        message: error.message,
        status: error.status,
        name: error.name
      });
      // Return more specific error message
      const errorMessage = error.message || 'Invalid credentials';
      return NextResponse.json(
        { success: false, error: errorMessage },
        { status: 401 }
      );
    }

    if (!data.user) {
      return NextResponse.json(
        { success: false, error: 'Authentication failed' },
        { status: 401 }
      );
    }

    // Get user profile from users_profiles table using the same service role client
    let profile = null;
    let profileError = null;
    
    // Check if user is admin via email allowlist (before profile lookup)
    const allowlist = (process.env.ADMIN_EMAILS || '').toLowerCase().split(',').map(s=>s.trim()).filter(Boolean);
    const isEmailAdmin = allowlist.includes(String(data.user.email).toLowerCase());
    const isMetadataAdmin = data.user.user_metadata?.is_admin || false;
    const metadataRole = data.user.user_metadata?.role || '';
    const isMetadataRoleAdmin = ['admin', 'spsa'].includes(String(metadataRole).toLowerCase());
    
    // Try by canonical id first
    {
      const res = await serviceSupabase
        .from('users_profiles')
        .select('role, first_name, last_name, organization, is_active, username')
        .eq('id', data.user.id)
        .maybeSingle();
      profile = res.data;
      profileError = res.error;
    }
    // Fallback: some databases may still use user_id column
    if (!profile && profileError?.code === 'PGRST116') {
      const resFallback = await serviceSupabase
        .from('users_profiles')
        .select('role, first_name, last_name, organization, is_active, username')
        .eq('user_id', data.user.id)
        .maybeSingle();
      profile = resFallback.data;
      profileError = resFallback.error;
    }
    
    // Log profile lookup for debugging
    if (profileError && profileError.code !== 'PGRST116') {
      console.warn('[Login] Profile lookup error (non-critical):', profileError);
    }
    
    // If profile not found but user is admin, create a temporary profile object
    if (!profile && (isEmailAdmin || isMetadataAdmin || isMetadataRoleAdmin)) {
      console.log('[Login] Admin user without profile, creating temporary profile:', data.user.email);
      profile = {
        role: metadataRole || 'admin',
        first_name: data.user.user_metadata?.first_name || '',
        last_name: data.user.user_metadata?.last_name || '',
        organization: data.user.user_metadata?.organization || null,
        is_active: true,
        username: data.user.user_metadata?.username || data.user.email
      };
    }

    // Auto-create minimal active profile on first login if missing
    if (!profile) {
      console.log('[Login] No profile found, attempting to create one');
      const firstName = data.user.user_metadata?.first_name || '';
      const lastName = data.user.user_metadata?.last_name || '';
      // Check if user has admin role in metadata
      const userRole = data.user.user_metadata?.role || 'user';
      const isAdminMetadata = data.user.user_metadata?.is_admin || false;
      const finalRole = (isAdminMetadata || userRole === 'admin' || userRole === 'spsa') ? userRole : 'user';
      
      const newProfile = {
        id: data.user.id,
        user_id: data.user.id, // Also set user_id for compatibility
        role: finalRole,
        first_name: firstName,
        last_name: lastName,
        organization: data.user.user_metadata?.organization || null,
        is_active: true,
        username: data.user.user_metadata?.username || data.user.email
      };
      console.log('[Login] Creating profile:', { email: data.user.email, role: finalRole });
      const { data: inserted, error: insertError } = await serviceSupabase
        .from('users_profiles')
        .upsert(newProfile, { onConflict: 'id' })
        .select('role, first_name, last_name, organization, is_active, username')
        .single();
      if (insertError) {
        console.error('[Login] Profile create error:', insertError);
        // Don't fail login if profile creation fails - allow login to proceed
        // but log the error
        console.warn('[Login] Profile creation failed, but allowing login to proceed');
      } else {
        profile = inserted;
      }
    }

    // Check if account is inactive - but allow admins to override
    if (profile && profile.is_active === false) {
      // Re-check admin status (already computed above)
      const roleIsAdmin = profile.role && ['admin', 'spsa'].includes(String(profile.role).toLowerCase());
      
      if (!isEmailAdmin && !isMetadataAdmin && !isMetadataRoleAdmin && !roleIsAdmin) {
        console.warn('[Login] Account inactive for non-admin user:', data.user.email);
        return NextResponse.json(
          { success: false, error: 'Account is inactive. Please contact an administrator.' },
          { status: 401 }
        );
      } else {
        console.log('[Login] Account inactive but user is admin, allowing login:', data.user.email);
        // Force is_active to true for admin accounts
        profile.is_active = true;
      }
    }

    // Determine final role and admin status - normalize to lowercase
    let finalRole = String(profile?.role || metadataRole || 'user').toLowerCase().trim();
    if (isEmailAdmin || isMetadataAdmin || isMetadataRoleAdmin) {
      // If user is admin via allowlist/metadata, ensure role is set correctly
      finalRole = String(metadataRole || 'admin').toLowerCase().trim();
    }
    
    // Calculate admin status
    const isAdmin = isEmailAdmin || isMetadataAdmin || isMetadataRoleAdmin || ['admin', 'spsa'].includes(finalRole);
    
    console.log('[Login] Final role determination:', {
      email: data.user.email,
      profileRole: profile?.role,
      metadataRole: metadataRole,
      finalRole: finalRole,
      isEmailAdmin,
      isMetadataAdmin,
      isMetadataRoleAdmin,
      isAdmin
    });
    
    // Set the Supabase session cookies
    const response = NextResponse.json({
      success: true,
      user: {
        id: data.user.id,
        email: data.user.email,
        role: finalRole,
        name: profile ? `${profile.first_name || ''} ${profile.last_name || ''}`.trim() || data.user.email : data.user.user_metadata?.name || data.user.email,
        organization: profile?.organization || data.user.user_metadata?.organization || null,
        username: profile?.username || data.user.user_metadata?.username || data.user.email,
        is_admin: isAdmin
      },
      session: {
        access_token: data.session?.access_token || null,
        refresh_token: data.session?.refresh_token || null,
        expires_at: data.session?.expires_at || null,
        token_type: data.session?.token_type || 'bearer'
      }
    });

    // Set the access token and refresh token as HTTP-only cookies
    const cookieDomain = (() => {
      const explicit = process.env.AUTH_COOKIE_DOMAIN;
      if (explicit) return explicit;
      const site = process.env.NEXT_PUBLIC_SITE_URL || '';
      if (site.includes('zophielgroup.com')) return '.zophielgroup.com';
      return undefined;
    })();
    if (data.session?.access_token) {
      response.cookies.set('sb-access-token', data.session.access_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        path: '/',
        domain: cookieDomain,
        maxAge: 60 * 60 * 24 * 7 // 7 days
      });
    }

    if (data.session?.refresh_token) {
      response.cookies.set('sb-refresh-token', data.session.refresh_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        path: '/',
        domain: cookieDomain,
        maxAge: 60 * 60 * 24 * 30 // 30 days
      });
    }

    return response;

  } catch (error) {
    console.error('Login error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}