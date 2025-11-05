import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase-client.js';

// User registration with multi-agency support
export async function POST(request) {
  try {
    const { email, password, full_name, agency_id, role_id, security_clearance_level } = await request.json();
    
    if (!email || !password || !full_name || !agency_id || !role_id) {
      return NextResponse.json(
        { success: false, error: 'Email, password, full name, agency, and role are required' },
        { status: 400 }
      );
    }

    const supabaseServer = supabaseAdmin;
    if (!supabaseServer) {
      return NextResponse.json(
        { success: false, error: 'Database connection failed' },
        { status: 500 }
      );
    }

    // Verify agency exists
    const { data: agency, error: agencyError } = await supabaseServer
      .from('agencies')
      .select('id, name, code')
      .eq('id', agency_id)
      .single();

    if (agencyError || !agency) {
      return NextResponse.json(
        { success: false, error: 'Invalid agency specified' },
        { status: 400 }
      );
    }

    // Verify role exists
    const { data: role, error: roleError } = await supabaseServer
      .from('user_roles')
      .select('id, name, permissions')
      .eq('id', role_id)
      .single();

    if (roleError || !role) {
      return NextResponse.json(
        { success: false, error: 'Invalid role specified' },
        { status: 400 }
      );
    }

    // Create user in auth.users
    const { data: authUser, error: authError } = await supabaseServer.auth.admin.createUser({
      email,
      password,
      email_confirm: true,
      user_metadata: {
        full_name,
        security_clearance_level: security_clearance_level || 'public'
      }
    });

    if (authError) {
      return NextResponse.json(
        { success: false, error: `Registration failed: ${authError.message}` },
        { status: 400 }
      );
    }

    // Create user-agency relationship
    const { data: userAgency, error: relationshipError } = await supabaseServer
      .from('user_agency_relationships')
      .insert({
        user_id: authUser.user.id,
        agency_id,
        role_id,
        security_clearance_level: security_clearance_level || 'public',
        created_at: new Date().toISOString()
      })
      .select()
      .single();

    if (relationshipError) {
      // Clean up auth user if relationship creation fails
      await supabaseServer.auth.admin.deleteUser(authUser.user.id);
      return NextResponse.json(
        { success: false, error: `Failed to create user relationship: ${relationshipError.message}` },
        { status: 500 }
      );
    }

    // Log security audit trail
    await supabaseServer
      .from('security_audit_trail')
      .insert({
        user_id: authUser.user.id,
        agency_id,
        action: 'user_registered',
        resource_type: 'user',
        resource_id: authUser.user.id,
        details: {
          user_email: email,
          user_agency: agency.name,
          user_role: role.name,
          security_clearance: security_clearance_level || 'public'
        },
        created_at: new Date().toISOString()
      });

    return NextResponse.json({
      success: true,
      message: 'User registered successfully',
      user: {
        id: authUser.user.id,
        email: authUser.user.email,
        full_name,
        agency: agency.name,
        role: role.name,
        security_clearance_level: security_clearance_level || 'public'
      }
    });

  } catch (error) {
    console.error('Registration error:', error);
    return NextResponse.json(
      { success: false, error: 'Registration failed' },
      { status: 500 }
    );
  }
}
