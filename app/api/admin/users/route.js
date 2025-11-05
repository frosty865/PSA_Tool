// Handles admin user CRUD. All endpoints require admin authentication.
import { NextResponse } from 'next/server';
import { requireAdmin } from '../../../lib/auth-middleware';
import { supabaseAdmin } from '@/app/lib/supabase-admin.js';

if (!supabaseAdmin) {
  console.error('Missing Supabase environment variables in admin users API');
}

// Get all users (admin only)
function authErrorResponse(error) {
  const msg = String(error || 'Unauthorized');
  const status = msg.includes('Authentication') ? 401 : 403;
  return NextResponse.json({ success: false, error: msg }, { status });
}

export async function GET(request) {
  const { user, error } = await requireAdmin(request);
  if (error) return authErrorResponse(error);
  try {
    // 1) List all auth users (service role bypasses RLS)
    const { data: authList, error: listErr } = await supabaseAdmin.auth.admin.listUsers({ perPage: 1000 });
    if (listErr) throw listErr;
    const authUsers = authList?.users || [];

    // 2) Load profiles for these users
    const ids = authUsers.map(u => u.id);
    let profiles = [];
    if (ids.length > 0) {
      const { data: profData, error: profErr } = await supabaseAdmin
        .from('user_profiles')
        .select('user_id, first_name, last_name, role, is_active')
        .in('user_id', ids);
      if (profErr) throw profErr;
      profiles = profData || [];
    }

    // 3) Merge
    const profileById = new Map(profiles.map(p => [p.user_id, p]));
    const merged = authUsers.map(u => {
      const p = profileById.get(u.id) || {};
      const derivedRole = String(p.role || u.user_metadata?.role || 'user').toLowerCase();
      return {
        id: u.id,
        email: u.email,
        created_at: u.created_at,
        last_sign_in_at: u.last_sign_in_at,
        role: derivedRole,
        full_name: (p.first_name || '') + (p.last_name ? ' ' + p.last_name : '') || u.user_metadata?.name || u.email,
        is_active: p.is_active ?? true
      };
    }).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    return NextResponse.json({ success: true, users: merged });
  } catch (error) {
    console.error('Error getting users:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to load users' },
      { status: 500 }
    );
  }
}

// Create new user (admin only)
export async function POST(request) {
  const { user, error } = await requireAdmin(request);
  if (error) return authErrorResponse(error);
  try {
    const body = await request.json();
    const { email, password, role, first_name, last_name } = body;
    if (!email || !password || !role) {
      return NextResponse.json(
        { success: false, error: 'Email, password, and role are required' },
        { status: 400 }
      );
    }
    // 1) Create auth user
    const { data: created, error: createErr } = await supabaseAdmin.auth.admin.createUser({
      email,
      password,
      email_confirm: true,
      user_metadata: { role, name: [first_name, last_name].filter(Boolean).join(' ') }
    });
    if (createErr) throw createErr;
    const newUser = created?.user;
    if (!newUser) throw new Error('Auth user creation failed');

    // 2) Upsert profile - include all required fields
    const profileData = {
      user_id: newUser.id,
      username: email.split('@')[0], // Use email prefix as username
      role: role,
      first_name: first_name || null,
      last_name: last_name || null,
      organization: body.agency || 'CISA',
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    
    const { error: profErr } = await supabaseAdmin
      .from('user_profiles')
      .upsert(profileData, { onConflict: 'user_id' });
    
    if (profErr) {
      console.error('Profile creation error:', profErr);
      // Try to delete auth user if profile creation fails
      await supabaseAdmin.auth.admin.deleteUser(newUser.id).catch(() => {});
      throw new Error(`Failed to create user profile: ${profErr.message}`);
    }

    return NextResponse.json({ 
      success: true, 
      user: { 
        id: newUser.id, 
        email: newUser.email, 
        role,
        user_id: newUser.id,
        username: profileData.username,
        full_name: (first_name || '') + (last_name ? ' ' + last_name : '')
      } 
    });
  } catch (error) {
    console.error('Error creating user:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to create user' },
      { status: 500 }
    );
  }
}

// Update user (admin only)
export async function PUT(request) {
  const { user, error } = await requireAdmin(request);
  if (error) return authErrorResponse(error);
  try {
    const body = await request.json();
    const { user_id, is_active, password, role, first_name, last_name, username, organization, agency } = body;
    
    if (!user_id) {
      return NextResponse.json(
        { success: false, error: 'User ID is required' },
        { status: 400 }
      );
    }
    
    // 1) Update password in auth if provided
    if (password && password.trim()) {
      const { error: pwErr } = await supabaseAdmin.auth.admin.updateUserById(user_id, { password });
      if (pwErr) {
        console.error('Password update error:', pwErr);
        throw pwErr;
      }
    }
    
    // 2) Update user_metadata if role changed
    if (role) {
      const { data: currentUser } = await supabaseAdmin.auth.admin.getUserById(user_id);
      if (currentUser?.user) {
        const { error: metaErr } = await supabaseAdmin.auth.admin.updateUserById(user_id, {
          user_metadata: {
            ...currentUser.user.user_metadata,
            role: role
          }
        });
        if (metaErr) {
          console.warn('Metadata update error (non-fatal):', metaErr);
        }
      }
    }
    
    // 3) Update profile
    const profUpdate = {
      updated_at: new Date().toISOString()
    };
    
    if (typeof is_active !== 'undefined') profUpdate.is_active = is_active;
    if (role) profUpdate.role = role;
    if (first_name !== undefined) profUpdate.first_name = first_name || null;
    if (last_name !== undefined) profUpdate.last_name = last_name || null;
    if (organization) profUpdate.organization = organization;
    if (agency) profUpdate.organization = agency; // agency is alias for organization
    if (username) profUpdate.username = username;

    if (Object.keys(profUpdate).length > 1) { // More than just updated_at
      const { error: profErr } = await supabaseAdmin
        .from('user_profiles')
        .update(profUpdate)
        .eq('user_id', user_id);
      if (profErr) {
        console.error('Profile update error:', profErr);
        throw profErr;
      }
    }

    return NextResponse.json({ success: true, message: 'User updated successfully' });
  } catch (error) {
    console.error('Error updating user:', error);
    return NextResponse.json(
      { success: false, error: `Update failed: ${error.message}` },
      { status: 500 }
    );
  }
}

// Delete user (admin only)
export async function DELETE(request) {
  const { user, error } = await requireAdmin(request);
  if (error) return authErrorResponse(error);
  try {
    const { searchParams } = new URL(request.url);
    const user_id = searchParams.get('user_id');
    if (!user_id) {
      return NextResponse.json(
        { success: false, error: 'User ID is required' },
        { status: 400 }
      );
    }
    // Delete profile (non-fatal)
    await supabaseAdmin.from('user_profiles').delete().eq('user_id', user_id);
    // Delete auth user
    const { error: delErr } = await supabaseAdmin.auth.admin.deleteUser(user_id);
    if (delErr) throw delErr;
    return NextResponse.json({
      success: true,
      message: 'User deleted successfully'
    });
  } catch (error) {
    console.error('Error deleting user:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to delete user' },
      { status: 500 }
    );
  }
}
