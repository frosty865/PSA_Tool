import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase-client.js';

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

    // Create service role client for authentication
    const serviceSupabase = supabaseAdmin;

    // Use service role for authentication
    const { data, error } = await serviceSupabase.auth.signInWithPassword({
      email,
      password
    });

    if (error) {
      console.error('Supabase auth error:', error);
      return NextResponse.json(
        { success: false, error: 'Invalid credentials' },
        { status: 401 }
      );
    }

    if (!data.user) {
      return NextResponse.json(
        { success: false, error: 'Authentication failed' },
        { status: 401 }
      );
    }

    // Get user profile from user_profiles table using the same service role client
    let profile = null;
    let profileError = null;
    // Try by canonical id first
    {
      const res = await serviceSupabase
        .from('user_profiles')
        .select('role, first_name, last_name, organization, is_active, username')
        .eq('id', data.user.id)
        .single();
      profile = res.data;
      profileError = res.error;
    }
    // Fallback: some databases may still use user_id column
    if ((!profile || profileError) && profileError?.code === 'PGRST116') {
      const resFallback = await serviceSupabase
        .from('user_profiles')
        .select('role, first_name, last_name, organization, is_active, username')
        .eq('user_id', data.user.id)
        .single();
      profile = resFallback.data;
      profileError = resFallback.error;
    }

    // Auto-create minimal active profile on first login if missing
    if (!profile) {
      const firstName = data.user.user_metadata?.first_name || '';
      const lastName = data.user.user_metadata?.last_name || '';
      const newProfile = {
        id: data.user.id,
        role: data.user.user_metadata?.role || 'user',
        first_name: firstName,
        last_name: lastName,
        organization: data.user.user_metadata?.organization || null,
        is_active: true,
        username: data.user.user_metadata?.username || data.user.email
      };
      const { data: inserted, error: insertError } = await serviceSupabase
        .from('user_profiles')
        .upsert(newProfile, { onConflict: 'id' })
        .select('role, first_name, last_name, organization, is_active, username')
        .single();
      if (insertError) {
        console.error('Profile create error:', insertError);
        return NextResponse.json(
          { success: false, error: 'User profile not found' },
          { status: 401 }
        );
      }
      profile = inserted;
    }

    if (!profile.is_active) {
      return NextResponse.json(
        { success: false, error: 'Account is inactive' },
        { status: 401 }
      );
    }

    // Set the Supabase session cookies
    const response = NextResponse.json({
      success: true,
      user: {
        id: data.user.id,
        email: data.user.email,
        role: profile.role,
        name: `${profile.first_name} ${profile.last_name}`,
        organization: profile.organization,
        username: profile.username
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