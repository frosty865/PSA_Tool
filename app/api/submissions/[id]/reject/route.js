import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { getProcessedByValue } from '@/app/utils/get-user-id.js';
import { logAuditEvent, getReviewerId } from '@/app/lib/audit-logger.js';

// Use service role for API submissions to bypass RLS
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

export async function POST(request, { params }) {
  try {
    const { id } = await params;
    const body = await request.json();
    const { comments, processedBy } = body;

    if (!id) {
      return NextResponse.json(
        { error: 'Missing submission ID' },
        { status: 400 }
      );
    }

    // Get the submission first
    const { data: submission, error: fetchError } = await supabase
      .from('submissions')
      .select('*')
      .eq('id', id)
      .single();

    if (fetchError) {
      return NextResponse.json(
        { error: 'Submission not found' },
        { status: 404 }
      );
    }

    if (submission.status !== 'pending_review') {
      return NextResponse.json(
        { error: 'Submission has already been processed' },
        { status: 400 }
      );
    }

    // Update submission status to rejected
    // Start with minimal update - don't try rejection_reason column (it may not exist)
    const updateData = {
      status: 'rejected',
      processed_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    
    // Get the correct processed_by value (convert email to UUID if needed)
    const validProcessedBy = await getProcessedByValue(processedBy);
    if (validProcessedBy) {
      updateData.processed_by = validProcessedBy;
    }
    
    // Store rejection reason in data JSONB (don't try rejection_reason column)
    // This is safer since we know data JSONB exists
    let currentData = submission.data || {};
    if (typeof currentData === 'string') {
      try {
        currentData = JSON.parse(currentData);
      } catch (e) {
        console.warn('[REJECT] Failed to parse existing data as JSON:', e);
        currentData = {};
      }
    }
    
    // Ensure currentData is an object
    if (!currentData || typeof currentData !== 'object' || Array.isArray(currentData)) {
      currentData = {};
    }
    
    // Build rejection note
    let rejectionNote = comments || `Rejected by: ${processedBy || 'admin'}`;
    if (processedBy && processedBy.includes('@') && !validProcessedBy) {
      rejectionNote = `${rejectionNote}\nRejected by: ${processedBy}`;
    }
    
    // Merge rejection data into existing data JSONB
    updateData.data = {
      ...currentData,
      rejection_reason: rejectionNote,
      rejected_at: new Date().toISOString()
    };
    
    const { data: updatedSubmission, error: updateError } = await supabase
      .from('submissions')
      .update(updateData)
      .eq('id', id)
      .select()
      .single();

    if (updateError) {
      console.error('[REJECT] Database error:', JSON.stringify(updateError, null, 2));
      console.error('[REJECT] Update data keys:', Object.keys(updateData));
      console.error('[REJECT] Submission ID:', id);
      console.error('[REJECT] Submission current status:', submission?.status);
      console.error('[REJECT] Submission data type:', typeof submission?.data);
      
      // Return detailed error
      return NextResponse.json(
        { 
          error: 'Failed to reject submission', 
          details: updateError.message,
          code: updateError.code,
          hint: updateError.hint || 'Check if status constraint allows "rejected"',
          currentStatus: submission?.status
        },
        { status: 500 }
      );
    }

    // --- Log Audit Event ---
    // Get reviewer ID from auth token
    let reviewerId = null;
    try {
      reviewerId = await getReviewerId(request) || validProcessedBy || null;
    } catch (authError) {
      console.warn('Could not get reviewer from token:', authError);
    }

    // Log audit event (non-blocking - don't fail rejection if audit logging fails)
    try {
      await logAuditEvent(
        id,
        reviewerId,
        'rejected',
        [],
        [],
        comments || null
      );
    } catch (auditError) {
      console.warn('⚠️ Error logging audit event (non-fatal):', auditError);
    }

    return NextResponse.json({
      success: true,
      submission: updatedSubmission || submission,
      message: 'Submission rejected successfully'
    });

  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
