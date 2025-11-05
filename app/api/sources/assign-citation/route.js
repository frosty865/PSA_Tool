import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

// Use service role for API submissions to bypass RLS
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

export async function POST(request) {
  try {
    const { sourceText } = await request.json();

    if (!sourceText || sourceText.trim() === '') {
      return NextResponse.json(
        { success: false, error: 'Source text is required' },
        { status: 400 }
      );
    }

    // Check if source already exists
    const { data: existingSource, error: searchError } = await supabase
      .from('sources')
      .select('"reference number", source')
      .eq('source', sourceText.trim())
      .single();

    if (searchError && searchError.code !== 'PGRST116') {
      console.error('Error searching for source:', searchError);
      return NextResponse.json(
        { success: false, error: 'Database error' },
        { status: 500 }
      );
    }

    // If source exists, return its citation number
    if (existingSource) {
      return NextResponse.json({
        success: true,
        citationNumber: existingSource['reference number'],
        citation: `[cite: ${existingSource['reference number']}]`,
        isNew: false
      });
    }

    // Source doesn't exist, create new one
    // Get the next reference number
    const { data: maxRef, error: maxError } = await supabase
      .from('sources')
      .select('"reference number"')
      .order('"reference number"', { ascending: false })
      .limit(1)
      .single();

    const nextRefNumber = maxRef ? maxRef['reference number'] + 1 : 1;

    // Create new source
    const { data: newSource, error: createError } = await supabase
      .from('sources')
      .insert([{
        'reference number': nextRefNumber,
        source: sourceText.trim()
      }])
      .select()
      .single();

    if (createError) {
      console.error('Error creating source:', createError);
      return NextResponse.json(
        { success: false, error: 'Failed to create source' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      citationNumber: newSource['reference number'],
      citation: `[cite: ${newSource['reference number']}]`,
      isNew: true
    });

  } catch (error) {
    console.error('Citation assignment error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}

