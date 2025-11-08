import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

// Use service role for API submissions to bypass RLS
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

export async function POST(request) {
  try {
    const body = await request.json().catch(() => ({}));
    const { 
      olderThanDays = null, // Optional: only delete rejections older than X days
      dryRun = false // If true, just return count without deleting
    } = body;

    // Build query for rejected submissions
    let query = supabase
      .from('submissions')
      .select('id, status, created_at, updated_at')
      .eq('status', 'rejected');

    // If olderThanDays is specified, filter by date
    if (olderThanDays && typeof olderThanDays === 'number' && olderThanDays > 0) {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - olderThanDays);
      query = query.lte('updated_at', cutoffDate.toISOString());
    }

    const { data: rejectedSubmissions, error: fetchError } = await query;

    if (fetchError) {
      console.error('Error fetching rejected submissions:', fetchError);
      return NextResponse.json(
        { error: 'Failed to fetch rejected submissions', details: fetchError.message },
        { status: 500 }
      );
    }

    if (!rejectedSubmissions || rejectedSubmissions.length === 0) {
      return NextResponse.json({
        success: true,
        message: 'No rejected submissions found',
        deleted_count: 0,
        dry_run: dryRun
      });
    }

    if (dryRun) {
      return NextResponse.json({
        success: true,
        message: `Found ${rejectedSubmissions.length} rejected submission(s) that would be deleted`,
        deleted_count: rejectedSubmissions.length,
        dry_run: true,
        submissions: rejectedSubmissions.map(s => ({
          id: s.id,
          created_at: s.created_at,
          updated_at: s.updated_at
        }))
      });
    }

    // Delete all rejected submissions and their related data
    let deletedCount = 0;
    let errorCount = 0;
    const errors = [];

    for (const submission of rejectedSubmissions) {
      try {
        const submissionId = submission.id;

        // Delete from submission mirror tables first (due to foreign key constraints)
        // Delete submission_vulnerability_ofc_links
        await supabase
          .from('submission_vulnerability_ofc_links')
          .delete()
          .eq('submission_id', submissionId);

        // Delete submission_ofc_sources
        await supabase
          .from('submission_ofc_sources')
          .delete()
          .eq('submission_id', submissionId);

        // Delete submission_options_for_consideration
        await supabase
          .from('submission_options_for_consideration')
          .delete()
          .eq('submission_id', submissionId);

        // Delete submission_vulnerabilities
        await supabase
          .from('submission_vulnerabilities')
          .delete()
          .eq('submission_id', submissionId);

        // Delete submission_sources
        await supabase
          .from('submission_sources')
          .delete()
          .eq('submission_id', submissionId);

        // Finally, delete the main submission
        const { error: deleteError } = await supabase
          .from('submissions')
          .delete()
          .eq('id', submissionId);

        if (deleteError) {
          errorCount++;
          errors.push({
            submission_id: submissionId,
            error: deleteError.message
          });
          console.error(`Failed to delete submission ${submissionId}:`, deleteError);
        } else {
          deletedCount++;
        }
      } catch (err) {
        errorCount++;
        errors.push({
          submission_id: submission.id,
          error: err.message
        });
        console.error(`Error deleting submission ${submission.id}:`, err);
      }
    }

    return NextResponse.json({
      success: true,
      message: `Cleanup complete: ${deletedCount} rejected submission(s) deleted`,
      deleted_count: deletedCount,
      error_count: errorCount,
      total_found: rejectedSubmissions.length,
      errors: errors.length > 0 ? errors : undefined,
      dry_run: false
    });

  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error.message },
      { status: 500 }
    );
  }
}

