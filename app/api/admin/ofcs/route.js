import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/app/lib/supabase-admin.js';
import { AuthService } from '../../../lib/auth-server';

// Get all OFCs (admin only)
export async function GET(request) {
  try {
    // Verify authentication
    const token = request.cookies.get('auth-token')?.value;
    if (!token) {
      return NextResponse.json(
        { success: false, error: 'Authentication required' },
        { status: 401 }
      );
    }

    const authResult = await AuthService.verifyToken(token);
    if (!authResult.success) {
      return NextResponse.json(
        { success: false, error: authResult.error },
        { status: 401 }
      );
    }

    // Check if user has admin access (admin or spsa only)
    if (!['admin', 'spsa'].includes(authResult.user.role)) {
      return NextResponse.json(
        { success: false, error: 'Admin access required' },
        { status: 403 }
      );
    }

    // Get all OFCs
    if (!supabaseAdmin) {
      return NextResponse.json(
        { success: false, error: 'Database connection failed' },
        { status: 500 }
      );
    }
    
    const { data: options_for_consideration, error } = await supabaseAdmin
      .from('options_for_consideration')
      .select('*')
      .order('option_text');

    if (error) {
      throw error;
    }

    return NextResponse.json({
      success: true,
      options_for_consideration: options_for_consideration || []
    });

  } catch (error) {
    console.error('Error fetching OFCs:', error);
    return NextResponse.json(
      { success: false, error: `Failed to fetch OFCs: ${error.message}` },
      { status: 500 }
    );
  }
}

// Update OFC (admin only)
export async function PUT(request) {
  try {
    // Verify authentication
    const token = request.cookies.get('auth-token')?.value;
    if (!token) {
      return NextResponse.json(
        { success: false, error: 'Authentication required' },
        { status: 401 }
      );
    }

    const authResult = await AuthService.verifyToken(token);
    if (!authResult.success) {
      return NextResponse.json(
        { success: false, error: authResult.error },
        { status: 401 }
      );
    }

    // Check if user has admin access (admin or spsa only)
    if (!['admin', 'spsa'].includes(authResult.user.role)) {
      return NextResponse.json(
        { success: false, error: 'Admin access required' },
        { status: 403 }
      );
    }

    const body = await request.json();
    const { 
      id, 
      option_text, 
      discipline, 
      source
    } = body;

    if (!id) {
      return NextResponse.json(
        { success: false, error: 'OFC ID is required' },
        { status: 400 }
      );
    }

    // Update OFC
    if (!supabaseAdmin) {
      return NextResponse.json(
        { success: false, error: 'Database connection failed' },
        { status: 500 }
      );
    }
    
    const { data: ofc, error } = await supabaseAdmin
      .from('options_for_consideration')
      .update({
        option_text,
        discipline,
        source,
        updated_at: new Date().toISOString()
      })
      .eq('id', id)
      .select()
      .single();

    if (error) {
      console.error('Database update error:', error);
      return NextResponse.json(
        { success: false, error: `Database update failed: ${error.message}` },
        { status: 500 }
      );
    }

    if (!ofc) {
      return NextResponse.json(
        { success: false, error: 'OFC not found' },
        { status: 404 }
      );
    }

    return NextResponse.json({
      success: true,
      ofc: ofc
    });

  } catch (error) {
    console.error('Error updating OFC:', error);
    return NextResponse.json(
      { success: false, error: `Update failed: ${error.message}` },
      { status: 500 }
    );
  }
}

// Delete OFC (admin only)
export async function DELETE(request) {
  try {
    // Verify authentication
    const token = request.cookies.get('auth-token')?.value;
    if (!token) {
      return NextResponse.json(
        { success: false, error: 'Authentication required' },
        { status: 401 }
      );
    }

    const authResult = await AuthService.verifyToken(token);
    if (!authResult.success) {
      return NextResponse.json(
        { success: false, error: authResult.error },
        { status: 401 }
      );
    }

    // Check if user has admin access (admin or spsa only)
    if (!['admin', 'spsa'].includes(authResult.user.role)) {
      return NextResponse.json(
        { success: false, error: 'Admin access required' },
        { status: 403 }
      );
    }

    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');

    if (!id) {
      return NextResponse.json(
        { success: false, error: 'OFC ID is required' },
        { status: 400 }
      );
    }

    // Delete OFC
    if (!supabaseAdmin) {
      return NextResponse.json(
        { success: false, error: 'Database connection failed' },
        { status: 500 }
      );
    }
    
    const { error } = await supabaseAdmin
      .from('options_for_consideration')
      .delete()
      .eq('id', id);

    if (error) {
      console.error('Database delete error:', error);
      return NextResponse.json(
        { success: false, error: `Database delete failed: ${error.message}` },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      message: 'OFC deleted successfully'
    });

  } catch (error) {
    console.error('Error deleting OFC:', error);
    return NextResponse.json(
      { success: false, error: `Delete failed: ${error.message}` },
      { status: 500 }
    );
  }
}
