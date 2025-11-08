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

    // Get the correct processed_by value (convert email to UUID if needed)
    const validProcessedBy = await getProcessedByValue(processedBy);
    
    // Build rejection note for audit log
    let rejectionNote = comments || `Rejected by: ${processedBy || 'admin'}`;
    if (processedBy && processedBy.includes('@') && !validProcessedBy) {
      rejectionNote = `${rejectionNote}\nRejected by: ${processedBy}`;
    }
    
    // --- Log Audit Event BEFORE deletion ---
    // Get reviewer ID from auth token
    let reviewerId = null;
    try {
      reviewerId = await getReviewerId(request) || validProcessedBy || null;
    } catch (authError) {
      console.warn('Could not get reviewer from token:', authError);
    }

    // Log audit event before deletion (non-blocking)
    try {
      await logAuditEvent(
        id,
        reviewerId,
        'rejected',
        [],
        [],
        comments || rejectionNote || null
      );
    } catch (auditError) {
      console.warn('⚠️ Error logging audit event (non-fatal):', auditError);
    }

    // --- Delete submission and all related records ---
    console.log('🗑️ Deleting rejected submission and related records...');
    
    // Delete from submission mirror tables first (due to foreign key constraints)
    // Delete submission_vulnerability_ofc_links
    const { error: linksError } = await supabase
      .from('submission_vulnerability_ofc_links')
      .delete()
      .eq('submission_id', id);
    
    if (linksError) {
      console.warn('Warning deleting links:', linksError);
    }

    // Delete submission_ofc_sources
    const { error: ofcSourcesError } = await supabase
      .from('submission_ofc_sources')
      .delete()
      .eq('submission_id', id);
    
    if (ofcSourcesError) {
      console.warn('Warning deleting OFC sources:', ofcSourcesError);
    }

    // Delete submission_options_for_consideration
    const { error: ofcsError } = await supabase
      .from('submission_options_for_consideration')
      .delete()
      .eq('submission_id', id);
    
    if (ofcsError) {
      console.warn('Warning deleting OFCs:', ofcsError);
    }

    // Delete submission_vulnerabilities
    const { error: vulnsError } = await supabase
      .from('submission_vulnerabilities')
      .delete()
      .eq('submission_id', id);
    
    if (vulnsError) {
      console.warn('Warning deleting vulnerabilities:', vulnsError);
    }

    // Delete submission_sources
    const { error: sourcesError } = await supabase
      .from('submission_sources')
      .delete()
      .eq('submission_id', id);
    
    if (sourcesError) {
      console.warn('Warning deleting sources:', sourcesError);
    }

    // Finally, delete the main submission
    const { error: deleteError } = await supabase
      .from('submissions')
      .delete()
      .eq('id', id);

    if (deleteError) {
      console.error('[REJECT] Database error deleting submission:', JSON.stringify(deleteError, null, 2));
      return NextResponse.json(
        { 
          error: 'Failed to delete rejected submission', 
          details: deleteError.message,
          code: deleteError.code
        },
        { status: 500 }
      );
    }

    console.log('✅ Rejected submission deleted successfully');

    return NextResponse.json({
      success: true,
      message: 'Submission rejected and deleted successfully',
      deleted_submission_id: id
    });

  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
