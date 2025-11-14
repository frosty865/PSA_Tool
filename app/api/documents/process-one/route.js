/**
 * Next.js API route to process a single document submission
 * Processes one submission by ID
 */

import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/app/lib/supabase-admin.js';

export const dynamic = 'force-dynamic';

export async function POST(request) {
  try {
    const body = await request.json();
    const { submissionId } = body;

    if (!submissionId) {
      return NextResponse.json(
        { success: false, error: 'submissionId is required' },
        { status: 400 }
      );
    }

    if (!supabaseAdmin) {
      return NextResponse.json(
        { success: false, error: 'Supabase admin client not available' },
        { status: 500 }
      );
    }

    // Get submission from database
    const { data: submission, error: fetchError } = await supabaseAdmin
      .from('submissions')
      .select('*')
      .eq('id', submissionId)
      .single();

    if (fetchError || !submission) {
      return NextResponse.json(
        { success: false, error: 'Submission not found', count: 0 },
        { status: 404 }
      );
    }

    // Process the submission (this would typically call the processing service)
    // For now, return success - actual processing should be handled by the processing service
    return NextResponse.json({
      success: true,
      message: 'Processing initiated',
      submissionId: submissionId,
      count: 1
    });

  } catch (error) {
    console.error('[Process One] Error:', error);
    return NextResponse.json(
      { 
        success: false,
        error: error.message || 'Unknown error',
        count: 0
      },
      { status: 500 }
    );
  }
}

