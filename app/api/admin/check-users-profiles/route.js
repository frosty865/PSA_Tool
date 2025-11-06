/**
 * Diagnostic endpoint to check users_profiles table structure and data
 * Admin only - helps debug profile lookup issues
 */

import { NextResponse } from 'next/server';
import { requireAdmin } from '@/app/lib/auth-middleware';
import { supabaseAdmin } from '@/app/lib/supabase-admin.js';

export async function GET(request) {
  const { user, error } = await requireAdmin(request);
  if (error) {
    return NextResponse.json(
      { success: false, error },
      { status: 401 }
    );
  }

  try {
    // Get current user's profile to test lookup
    const { data: currentProfile, error: currentProfileError } = await supabaseAdmin
      .from('users_profiles')
      .select('*')
      .eq('user_id', user.id)
      .maybeSingle();

    // Also try by id column
    let profileById = null;
    if (!currentProfile) {
      const { data: profileData } = await supabaseAdmin
        .from('users_profiles')
        .select('*')
        .eq('id', user.id)
        .maybeSingle();
      profileById = profileData;
    }

    // Get all profiles to see structure
    const { data: allProfiles, error: allProfilesError } = await supabaseAdmin
      .from('users_profiles')
      .select('*')
      .limit(10);

    // Get auth user info
    const { data: { user: authUser }, error: authUserError } = await supabaseAdmin.auth.getUser(user.id);

    return NextResponse.json({
      success: true,
      currentUser: {
        id: user.id,
        email: user.email,
        role: user.role
      },
      authUser: authUser ? {
        id: authUser.id,
        email: authUser.email,
        user_metadata: authUser.user_metadata
      } : null,
      profileLookup: {
        by_user_id: {
          found: !!currentProfile,
          data: currentProfile,
          error: currentProfileError?.message || null
        },
        by_id: {
          found: !!profileById,
          data: profileById
        }
      },
      sampleProfiles: allProfiles?.slice(0, 5) || [],
      totalProfiles: allProfiles?.length || 0,
      errors: {
        allProfiles: allProfilesError?.message || null,
        authUser: authUserError?.message || null
      },
      tableInfo: {
        name: 'users_profiles',
        note: 'Check if table exists and has correct columns (user_id, id, role, etc.)'
      }
    });
  } catch (error) {
    console.error('[Check Users Profiles] Error:', error);
    return NextResponse.json(
      {
        success: false,
        error: error.message,
        stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
      },
      { status: 500 }
    );
  }
}

