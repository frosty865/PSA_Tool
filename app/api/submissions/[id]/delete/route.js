import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

// Use service role for API submissions to bypass RLS
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

export async function DELETE(request, { params }) {
  try {
    const { id } = await params;
    const body = await request.json();
    const { reason, deletedBy } = body;

    if (!id) {
      return NextResponse.json(
        { error: 'Missing submission ID' },
        { status: 400 }
      );
    }

    // Get the submission first to check its status
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

    // Only allow deletion of rejected or pending submissions
    if (submission.status === 'approved') {
      return NextResponse.json(
        { error: 'Cannot delete approved submissions' },
        { status: 400 }
      );
    }

    // Log the deletion for audit purposes
    const deletionLog = {
      submission_id: id,
      deleted_at: new Date().toISOString(),
      deleted_by: deletedBy || 'system',
      reason: reason || 'Manual deletion',
      original_status: submission.status,
      original_data: submission.data
    };

    // Delete from submission mirror tables first (due to foreign key constraints)
    console.log('🗑️ Deleting from submission mirror tables...');
    
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
      console.error('Database error:', deleteError);
      return NextResponse.json(
        { error: 'Failed to delete submission', details: deleteError.message },
        { status: 500 }
      );
    }

    // Log the deletion (optional - you might want to store this in a separate audit table)
    console.log('Submission deleted:', deletionLog);

    return NextResponse.json({
      success: true,
      message: 'Submission deleted successfully',
      deleted_submission: {
        id: submission.id,
        status: submission.status,
        deleted_at: deletionLog.deleted_at
      }
    });

  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
