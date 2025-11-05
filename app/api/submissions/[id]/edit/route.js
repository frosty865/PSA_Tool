import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

// Use service role for admin operations to bypass RLS
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

export async function POST(request, { params }) {
  try {
    const { id } = params;
    const body = await request.json();
    const { data, editedBy } = body;

    if (!data || !editedBy) {
      return NextResponse.json(
        { error: 'Missing required fields: data and editedBy' },
        { status: 400 }
      );
    }

    // Update the submission data
    const { data: updatedSubmission, error } = await supabase
      .from('submissions')
      .update({
        data: JSON.stringify(data),
        updated_at: new Date().toISOString()
      })
      .eq('id', id)
      .select()
      .single();

    if (error) {
      console.error('Database error:', error);
      return NextResponse.json(
        { error: 'Failed to update submission' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      submission: updatedSubmission,
      message: 'Submission updated successfully'
    });

  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

