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
    const updateData = {
      status: 'rejected',
      processed_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    
    // Get the correct processed_by value (convert email to UUID if needed)
    const validProcessedBy = await getProcessedByValue(processedBy);
    if (validProcessedBy) {
      updateData.processed_by = validProcessedBy;
    } else if (processedBy && processedBy.includes('@')) {
      // If we can't convert email to UUID, store it in comments
      updateData.comments = `Rejected by: ${processedBy}`;
    }
    
    // Add rejection comments if provided
    if (comments) {
      updateData.comments = updateData.comments 
        ? `${updateData.comments}\nRejection reason: ${comments}`
        : `Rejection reason: ${comments}`;
    }
    
    const { data: updatedSubmission, error: updateError } = await supabase
      .from('submissions')
      .update(updateData)
      .eq('id', id)
      .select()
      .single();

    if (updateError) {
      console.error('Database error:', updateError);
      console.error('Update data:', updateData);
      console.error('Submission ID:', id);
      console.error('Submission current status:', submission?.status);
      
      // Provide more detailed error information
      const errorDetails = {
        message: updateError.message,
        code: updateError.code,
        details: updateError.details,
        hint: updateError.hint
      };
      
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
      submission: updatedSubmission,
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
