import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/app/lib/supabase-admin.js';
import { cookies } from 'next/headers';

// Admin vulnerabilities management with multi-agency RLS
export async function GET(request) {
  try {
    // Auth check
    const cookieStore = cookies();
    
    // First try: sb-access-token (set by login route)
    let accessToken = null;
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

    if (!accessToken || !supabaseAdmin) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 });
    }

    const { data: { user }, error: userError } = await supabaseAdmin.auth.getUser(accessToken);
    if (userError || !user) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 });
    }

    const { data: profile } = await supabaseAdmin
      .from('users_profiles')
      .select('role')
      .eq('id', user.id)
      .single();

    if (!profile || !['admin', 'spsa', 'psa', 'analyst'].includes(profile.role)) {
      return NextResponse.json({ success: false, error: 'Forbidden' }, { status: 403 });
    }

    // Get current admin's agency for RLS filtering
    const { data: adminAgency } = await supabaseAdmin
      .from('user_agency_relationships')
      .select('agency_id, role_id')
      .eq('user_id', user.id)
      .single();

    // Get vulnerabilities with their relationships
    const { data: vulnerabilities, error: vulnerabilitiesError } = await supabaseAdmin
      .from('vulnerabilities')
      .select(`
        id,
        vulnerability_name,
        description,
        discipline,
        sector_id,
        subsector_id,
        created_at,
        updated_at,
        vulnerability_ofc_links(
          ofc_id,
          link_type,
          confidence_score,
          options_for_consideration(
            id,
            option_text,
            discipline
          )
        )
      `)
      .order('created_at', { ascending: false });

    if (vulnerabilitiesError) throw vulnerabilitiesError;

    // Filter by admin's agency if not super admin
    const filteredVulnerabilities = vulnerabilities?.filter(vuln => {
      // For now, all vulnerabilities are visible to all agencies
      // In the future, this could be filtered by agency-specific data classification
      return true;
    }) || [];

    return NextResponse.json({
      success: true,
      vulnerabilities: filteredVulnerabilities,
      admin_agency: adminAgency?.agencies?.name || 'Unknown'
    });

  } catch (error) {
    console.error('Error fetching vulnerabilities:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to load vulnerabilities' },
      { status: 500 }
    );
  }
}

// Create new vulnerability
export async function POST(request) {
  try {
    // Auth check (same as GET)
    const cookieStore = cookies();
    
    // First try: sb-access-token (set by login route)
    let accessToken = null;
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

    if (!accessToken || !supabaseAdmin) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 });
    }

    const { data: { user }, error: userError } = await supabaseAdmin.auth.getUser(accessToken);
    if (userError || !user) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 });
    }

    const { data: profile } = await supabaseAdmin
      .from('users_profiles')
      .select('role')
      .eq('id', user.id)
      .single();

    if (!profile || !['admin', 'spsa', 'psa', 'analyst'].includes(profile.role)) {
      return NextResponse.json({ success: false, error: 'Forbidden' }, { status: 403 });
    }
    const { vulnerability_name, description, discipline, sector_id, subsector_id } = await request.json();
    
    if (!vulnerability_name || !description || !discipline) {
      return NextResponse.json(
        { success: false, error: 'Vulnerability name, description, and discipline are required' },
        { status: 400 }
      );
    }

    // Use supabaseAdmin (already imported)

    // Get current admin's agency for audit trail
    const { data: adminAgency } = await supabaseAdmin
      .from('user_agency_relationships')
      .select('agency_id, role_id')
      .eq('user_id', user.id)
      .single();

    // Create vulnerability
    const { data: vulnerability, error: vulnerabilityError } = await supabaseAdmin
      .from('vulnerabilities')
      .insert({
        vulnerability_name,
        description,
        discipline,
        sector_id,
        subsector_id,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      })
      .select()
      .single();

    if (vulnerabilityError) throw vulnerabilityError;

    // Log security audit trail
    await supabaseAdmin
      .from('security_audit_trail')
      .insert({
        user_id: user.id,
        agency_id: adminAgency?.agency_id,
        action: 'vulnerability_created',
        resource_type: 'vulnerability',
        resource_id: vulnerability.id,
        details: {
          vulnerability_name,
          discipline,
          sector_id,
          subsector_id
        },
        created_at: new Date().toISOString()
      });

    return NextResponse.json({
      success: true,
      message: 'Vulnerability created successfully',
      vulnerability
    });

  } catch (error) {
    console.error('Error creating vulnerability:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to create vulnerability' },
      { status: 500 }
    );
  }
}

// Update vulnerability
export async function PUT(request) {
  try {
    // Auth check (same as GET)
    const cookieStore = cookies();
    
    // First try: sb-access-token (set by login route)
    let accessToken = null;
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

    if (!accessToken || !supabaseAdmin) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 });
    }

    const { data: { user }, error: userError } = await supabaseAdmin.auth.getUser(accessToken);
    if (userError || !user) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 });
    }

    const { data: profile } = await supabaseAdmin
      .from('users_profiles')
      .select('role')
      .eq('id', user.id)
      .single();

    if (!profile || !['admin', 'spsa', 'psa', 'analyst'].includes(profile.role)) {
      return NextResponse.json({ success: false, error: 'Forbidden' }, { status: 403 });
    }
    const { id, vulnerability_name, description, discipline, sector_id, subsector_id } = await request.json();
    
    if (!id) {
      return NextResponse.json(
        { success: false, error: 'Vulnerability ID is required' },
        { status: 400 }
      );
    }

    // Use supabaseAdmin (already imported)

    // Get current admin's agency for audit trail
    const { data: adminAgency } = await supabaseAdmin
      .from('user_agency_relationships')
      .select('agency_id, role_id')
      .eq('user_id', user.id)
      .single();

    // Update vulnerability
    const { data: vulnerability, error: vulnerabilityError } = await supabaseAdmin
      .from('vulnerabilities')
      .update({
        vulnerability_name,
        description,
        discipline,
        sector_id,
        subsector_id,
        updated_at: new Date().toISOString()
      })
      .eq('id', id)
      .select()
      .single();

    if (vulnerabilityError) throw vulnerabilityError;

    // Log security audit trail
    await supabaseAdmin
      .from('security_audit_trail')
      .insert({
        user_id: user.id,
        agency_id: adminAgency?.agency_id,
        action: 'vulnerability_updated',
        resource_type: 'vulnerability',
        resource_id: id,
        details: {
          updated_fields: { vulnerability_name, description, discipline, sector_id, subsector_id },
          updated_at: new Date().toISOString()
        },
        created_at: new Date().toISOString()
      });

    return NextResponse.json({
      success: true,
      message: 'Vulnerability updated successfully',
      vulnerability
    });

  } catch (error) {
    console.error('Error updating vulnerability:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to update vulnerability' },
      { status: 500 }
    );
  }
}

// Delete vulnerability
export async function DELETE(request) {
  try {
    // Auth check (same as GET)
    const cookieStore = cookies();
    
    // First try: sb-access-token (set by login route)
    let accessToken = null;
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

    if (!accessToken || !supabaseAdmin) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 });
    }

    const { data: { user }, error: userError } = await supabaseAdmin.auth.getUser(accessToken);
    if (userError || !user) {
      return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 });
    }

    const { data: profile } = await supabaseAdmin
      .from('users_profiles')
      .select('role')
      .eq('id', user.id)
      .single();

    if (!profile || !['admin', 'spsa', 'psa', 'analyst'].includes(profile.role)) {
      return NextResponse.json({ success: false, error: 'Forbidden' }, { status: 403 });
    }
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');
    
    if (!id) {
      return NextResponse.json(
        { success: false, error: 'Vulnerability ID is required' },
        { status: 400 }
      );
    }

    // Use supabaseAdmin (already imported)

    // Get current admin's agency for audit trail
    const { data: adminAgency } = await supabaseAdmin
      .from('user_agency_relationships')
      .select('agency_id, role_id')
      .eq('user_id', user.id)
      .single();

    // Delete vulnerability (this will cascade to related records)
    const { error: vulnerabilityError } = await supabaseAdmin
      .from('vulnerabilities')
      .delete()
      .eq('id', id);

    if (vulnerabilityError) throw vulnerabilityError;

    // Log security audit trail
    await supabaseAdmin
      .from('security_audit_trail')
      .insert({
        user_id: user.id,
        agency_id: adminAgency?.agency_id,
        action: 'vulnerability_deleted',
        resource_type: 'vulnerability',
        resource_id: id,
        details: {
          deleted_at: new Date().toISOString()
        },
        created_at: new Date().toISOString()
      });

    return NextResponse.json({
      success: true,
      message: 'Vulnerability deleted successfully'
    });

  } catch (error) {
    console.error('Error deleting vulnerability:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to delete vulnerability' },
      { status: 500 }
    );
  }
}
