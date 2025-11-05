import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase-client.js';

export async function POST(request) {
  try {
    const body = await request.json();
    const { vulnerability_id, ofc_text, submitter, vulnerability_text, discipline } = body;

    // Validate required fields
    if (!vulnerability_id || !ofc_text || !submitter) {
      return NextResponse.json(
        { success: false, error: 'Missing required fields' },
        { status: 400 }
      );
    }

    // Create OFC request record
    const ofcRequest = {
      vulnerability_id,
      ofc_text: ofc_text.trim(),
      submitter,
      vulnerability_text: vulnerability_text || 'Unknown',
      discipline: discipline || 'General',
      status: 'pending_review',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    // Insert into database
    const { data, error } = await supabaseAdmin
      .from('ofc_requests')
      .insert([ofcRequest])
      .select();

    if (error) {
      console.error('Error creating OFC request:', error);
      return NextResponse.json(
        { success: false, error: 'Failed to create OFC request' },
        { status: 500 }
      );
    }

    // Log the submission for audit trail
    console.log(`📝 OFC Request submitted:`, {
      id: data[0].id,
      vulnerability_id,
      submitter,
      ofc_text: ofc_text.substring(0, 100) + '...',
      timestamp: new Date().toISOString()
    });

    // TODO: Send notification to supervisor
    // This could be an email, Slack message, or database notification
    console.log(`🔔 Supervisor notification needed for OFC request ${data[0].id}`);

    return NextResponse.json({
      success: true,
      message: 'OFC request submitted for supervisor review',
      ofc_request_id: data[0].id
    });

  } catch (error) {
    console.error('Error in OFC request API:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}
