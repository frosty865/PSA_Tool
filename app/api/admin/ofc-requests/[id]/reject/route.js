import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

export async function POST(request, { params }) {
  try {
    const { id } = params;
    const body = await request.json();
    const { supervisor_notes, approved_by } = body;

    // Update the OFC request status to rejected
    const { data, error } = await supabase
      .from('ofc_requests')
      .update({
        status: 'rejected',
        supervisor_notes: supervisor_notes || null,
        approved_by: approved_by || 'admin@vofc.gov',
        updated_at: new Date().toISOString()
      })
      .eq('id', id)
      .select();

    if (error) {
      console.error('Error rejecting OFC request:', error);
      return NextResponse.json(
        { success: false, error: 'Failed to reject OFC request' },
        { status: 500 }
      );
    }

    if (!data || data.length === 0) {
      return NextResponse.json(
        { success: false, error: 'OFC request not found' },
        { status: 404 }
      );
    }

    // Log the rejection
    console.log(`❌ OFC Request rejected:`, {
      id,
      approved_by,
      supervisor_notes: supervisor_notes?.substring(0, 100) + '...',
      timestamp: new Date().toISOString()
    });

    return NextResponse.json({
      success: true,
      message: 'OFC request rejected successfully',
      ofc_request: data[0]
    });

  } catch (error) {
    console.error('Error in reject OFC request API:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}
