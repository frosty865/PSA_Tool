import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';
import { supabaseAdmin } from '@/app/lib/supabase-admin';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function OPTIONS(request) {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}

export async function POST(request) {
  try {
    const formData = await request.formData();
    const file = formData.get('file');
    const source_title = formData.get('source_title') || '';
    const source_type = formData.get('source_type') || 'unknown';
    const source_url = formData.get('source_url') || '';
    const author_org = formData.get('author_org') || '';
    const publication_year = formData.get('publication_year') || new Date().getFullYear();
    const content_restriction = formData.get('content_restriction') || 'public';

    if (!file) {
      return NextResponse.json(
        { success: false, error: 'No file provided' },
        { status: 400 }
      );
    }

    if (!source_title.trim()) {
      return NextResponse.json(
        { success: false, error: 'Source title is required' },
        { status: 400 }
      );
    }

    // Get Flask URL
    const flaskUrl = getFlaskUrl();

    // Step 1: Save file to Flask incoming directory and process it
    const flaskFormData = new FormData();
    flaskFormData.append('file', file);

    let fileSaved = false;
    let savedFilename = file.name;
    let processingStarted = false;

    try {
      const saveResponse = await fetch(`${flaskUrl}/api/process`, {
        method: 'POST',
        body: flaskFormData,
      });

      if (saveResponse.ok) {
        fileSaved = true;
        processingStarted = true;
        const saveResult = await saveResponse.json();
        if (saveResult.file) {
          savedFilename = saveResult.file;
        } else if (saveResult.filename) {
          savedFilename = saveResult.filename;
        }
        console.log('[documents/submit] File saved and processing started:', savedFilename);
      } else {
        const errorText = await saveResponse.text();
        console.warn('[documents/submit] Flask save failed:', saveResponse.status, errorText);
      }
    } catch (error) {
      console.error('[documents/submit] Flask save error:', error);
      // Continue - create submission anyway, file might be saved
    }

    // Step 2: Create submission record in Supabase
    const submissionData = {
      type: 'document',
      data: JSON.stringify({
        source_title,
        source_type,
        source_url,
        author_org,
        publication_year: parseInt(publication_year) || new Date().getFullYear(),
        content_restriction,
        filename: savedFilename,
        file_size: file.size,
        file_type: file.type || file.name.split('.').pop(),
      }),
      status: 'processing',
      source: 'document_upload',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    const { data: submission, error: submissionError } = await supabaseAdmin
      .from('submissions')
      .insert([submissionData])
      .select()
      .single();

    if (submissionError) {
      console.error('[documents/submit] Submission creation error:', submissionError);
      return NextResponse.json(
        { success: false, error: 'Failed to create submission record' },
        { status: 500 }
      );
    }

    console.log('[documents/submit] Submission created:', submission.id);

    return NextResponse.json({
      success: true,
      submission_id: submission.id,
      message: 'Document submitted successfully',
      filename: savedFilename,
      file_saved: fileSaved,
      processing_started: processingStarted,
    });
  } catch (error) {
    console.error('[documents/submit] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to submit document' },
      { status: 500 }
    );
  }
}

