import { NextResponse } from 'next/server';
import { requireAdmin } from '../../../lib/auth-middleware';
import { getServerClient } from '../../../lib/supabase-manager';

// Admin vulnerabilities management with multi-agency RLS
export async function GET(request) {
  const { user, error } = await requireAdmin(request);
  if (error) {
    const msg = String(error || 'Unauthorized');
    const status = msg.includes('Authentication') ? 401 : 403;
    return NextResponse.json({ success: false, error: msg }, { status });
  }
  
  try {
    const supabaseServer = getServerClient();
    if (!supabaseServer) {
      return NextResponse.json(
        { success: false, error: 'Database connection failed' },
        { status: 500 }
      );
    }

    // Get current admin's agency for RLS filtering
    const { data: adminAgency } = await supabaseServer
      .from('user_agency_relationships')
      .select('agency_id, role_id')
      .eq('user_id', user.id)
      .single();

    // Get vulnerabilities with their relationships
    const { data: vulnerabilities, error: vulnerabilitiesError } = await supabaseServer
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
  const { user, error } = await requireAdmin(request);
  if (error) {
    const msg = String(error || 'Unauthorized');
    const status = msg.includes('Authentication') ? 401 : 403;
    return NextResponse.json({ success: false, error: msg }, { status });
  }
  
  try {
    const { vulnerability_name, description, discipline, sector_id, subsector_id } = await request.json();
    
    if (!vulnerability_name || !description || !discipline) {
      return NextResponse.json(
        { success: false, error: 'Vulnerability name, description, and discipline are required' },
        { status: 400 }
      );
    }

    const supabaseServer = getServerClient();
    if (!supabaseServer) {
      return NextResponse.json(
        { success: false, error: 'Database connection failed' },
        { status: 500 }
      );
    }

    // Get current admin's agency for audit trail
    const { data: adminAgency } = await supabaseServer
      .from('user_agency_relationships')
      .select('agency_id, role_id')
      .eq('user_id', user.id)
      .single();

    // Create vulnerability
    const { data: vulnerability, error: vulnerabilityError } = await supabaseServer
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
    await supabaseServer
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
  const { user, error } = await requireAdmin(request);
  if (error) {
    const msg = String(error || 'Unauthorized');
    const status = msg.includes('Authentication') ? 401 : 403;
    return NextResponse.json({ success: false, error: msg }, { status });
  }
  
  try {
    const { id, vulnerability_name, description, discipline, sector_id, subsector_id } = await request.json();
    
    if (!id) {
      return NextResponse.json(
        { success: false, error: 'Vulnerability ID is required' },
        { status: 400 }
      );
    }

    const supabaseServer = getServerClient();
    if (!supabaseServer) {
      return NextResponse.json(
        { success: false, error: 'Database connection failed' },
        { status: 500 }
      );
    }

    // Get current admin's agency for audit trail
    const { data: adminAgency } = await supabaseServer
      .from('user_agency_relationships')
      .select('agency_id, role_id')
      .eq('user_id', user.id)
      .single();

    // Update vulnerability
    const { data: vulnerability, error: vulnerabilityError } = await supabaseServer
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
    await supabaseServer
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
  const { user, error } = await requireAdmin(request);
  if (error) {
    const msg = String(error || 'Unauthorized');
    const status = msg.includes('Authentication') ? 401 : 403;
    return NextResponse.json({ success: false, error: msg }, { status });
  }
  
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');
    
    if (!id) {
      return NextResponse.json(
        { success: false, error: 'Vulnerability ID is required' },
        { status: 400 }
      );
    }

    const supabaseServer = getServerClient();
    if (!supabaseServer) {
      return NextResponse.json(
        { success: false, error: 'Database connection failed' },
        { status: 500 }
      );
    }

    // Get current admin's agency for audit trail
    const { data: adminAgency } = await supabaseServer
      .from('user_agency_relationships')
      .select('agency_id, role_id')
      .eq('user_id', user.id)
      .single();

    // Delete vulnerability (this will cascade to related records)
    const { error: vulnerabilityError } = await supabaseServer
      .from('vulnerabilities')
      .delete()
      .eq('id', id);

    if (vulnerabilityError) throw vulnerabilityError;

    // Log security audit trail
    await supabaseServer
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
