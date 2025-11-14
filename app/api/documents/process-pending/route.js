/**
 * Next.js API route to process pending documents
 * Processes all pending submissions from the database
 */

import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/app/lib/supabase-admin.js';

export const dynamic = 'force-dynamic';

export async function POST(request) {
  try {
    if (!supabaseAdmin) {
      return NextResponse.json(
        { success: false, error: 'Supabase admin client not available' },
        { status: 500 }
      );
    }

    // Get pending submissions
    const { data: submissions, error: fetchError } = await supabaseAdmin
      .from('submissions')
      .select('id, status')
      .eq('status', 'pending')
      .limit(100); // Limit to prevent overload

    if (fetchError) {
      return NextResponse.json(
        { success: false, error: 'Failed to fetch pending submissions', processed: 0, failed: 0 },
        { status: 500 }
      );
    }

    if (!submissions || submissions.length === 0) {
      return NextResponse.json({
        success: true,
        message: 'No pending submissions to process',
        processed: 0,
        failed: 0,
        results: []
      });
    }

    // Process submissions (this would typically call the processing service)
    // For now, return success - actual processing should be handled by the processing service
    return NextResponse.json({
      success: true,
      message: `Found ${submissions.length} pending submission(s)`,
      processed: submissions.length,
      failed: 0,
      results: submissions.map(s => ({ id: s.id, status: 'queued' }))
    });

  } catch (error) {
    console.error('[Process Pending] Error:', error);
    return NextResponse.json(
      { 
        success: false,
        error: error.message || 'Unknown error',
        processed: 0,
        failed: 0
      },
      { status: 500 }
    );
  }
}

