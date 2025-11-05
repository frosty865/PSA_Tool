import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

// Use service role key for API submissions to bypass RLS
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
);

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const submissionId = searchParams.get('submission_id');
    
    if (!submissionId) {
      return NextResponse.json(
        { error: 'Missing submission_id parameter' },
        { status: 400 }
      );
    }
    
    // Get structured submission data
    const { data: submission, error: submissionError } = await supabase
      .from('submissions')
      .select('*')
      .eq('id', submissionId)
      .single();
    
    if (submissionError) {
      return NextResponse.json(
        { error: 'Submission not found' },
        { status: 404 }
      );
    }
    
    // Get submission vulnerabilities
    const { data: vulnerabilities, error: vulnError } = await supabase
      .from('submission_vulnerabilities')
      .select('*')
      .eq('submission_id', submissionId);
    
    if (vulnError) {
      console.error('Error fetching vulnerabilities:', vulnError);
    }
    
    // Get submission OFCs
    const { data: ofcs, error: ofcError } = await supabase
      .from('submission_options_for_consideration')
      .select('*')
      .eq('submission_id', submissionId);
    
    if (ofcError) {
      console.error('Error fetching OFCs:', ofcError);
    }
    
    // Get submission sources
    const { data: sources, error: sourceError } = await supabase
      .from('submission_sources')
      .select('*')
      .eq('submission_id', submissionId);
    
    if (sourceError) {
      console.error('Error fetching sources:', sourceError);
    }
    
    // Get vulnerability-OFC links
    const { data: links, error: linkError } = await supabase
      .from('submission_vulnerability_ofc_links')
      .select('*')
      .eq('submission_id', submissionId);
    
    if (linkError) {
      console.error('Error fetching links:', linkError);
    }
    
    return NextResponse.json({
      success: true,
      submission: {
        id: submission.id,
        type: submission.type,
        status: submission.status,
        source: submission.source,
        submitter_email: submission.submitter_email,
        created_at: submission.created_at,
        updated_at: submission.updated_at
      },
      structured_data: {
        vulnerabilities: vulnerabilities || [],
        options_for_consideration: ofcs || [],
        sources: sources || [],
        vulnerability_ofc_links: links || []
      },
      summary: {
        vulnerability_count: vulnerabilities?.length || 0,
        ofc_count: ofcs?.length || 0,
        source_count: sources?.length || 0,
        link_count: links?.length || 0
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

export async function POST(request) {
  try {
    const body = await request.json();
    const { submission_id, enhanced_extraction } = body;
    
    if (!submission_id || !enhanced_extraction) {
      return NextResponse.json(
        { error: 'Missing required fields: submission_id and enhanced_extraction' },
        { status: 400 }
      );
    }
    
    // Get the submission
    const { data: submission, error: submissionError } = await supabase
      .from('submissions')
      .select('*')
      .eq('id', submission_id)
      .single();
    
    if (submissionError) {
      return NextResponse.json(
        { error: 'Submission not found' },
        { status: 404 }
      );
    }
    
    const data = typeof submission.data === 'string' ? JSON.parse(submission.data) : submission.data;
    
    // Create submission vulnerability
    const { data: vulnData, error: vulnError } = await supabase
      .from('submission_vulnerabilities')
      .insert([{
        submission_id: submission_id,
        vulnerability: data.vulnerability || 'Extracted from document',
        discipline: data.discipline || 'General',
        source: data.sources || data.source_url || 'Document Analysis',
        source_title: data.source_title || 'Unknown Document',
        source_url: data.source_url,
        ofc_count: data.ofc_count || 0,
        vulnerability_count: data.vulnerability_count || 0,
        enhanced_extraction: enhanced_extraction,
        parsed_at: data.parsed_at,
        parser_version: data.parser_version,
        extraction_stats: data.extraction_stats
      }])
      .select()
      .single();
    
    if (vulnError) {
      console.error('Error creating submission vulnerability:', vulnError);
      return NextResponse.json(
        { error: 'Failed to create submission vulnerability' },
        { status: 500 }
      );
    }
    
    // Process enhanced extraction data
    let ofcCount = 0;
    let sourceCount = 0;
    
    for (const record of enhanced_extraction) {
      if (record.content && Array.isArray(record.content)) {
        for (const entry of record.content) {
          if (entry.type === 'ofc') {
            // Create submission OFC
            const { data: ofcData, error: ofcError } = await supabase
              .from('submission_options_for_consideration')
              .insert([{
                submission_id: submission_id,
                option_text: entry.text,
                discipline: record.source_title?.includes('security') ? 'Physical Security' : 'General',
                vulnerability_id: vulnData.id,
                source: record.source_url || 'Document Analysis',
                source_title: record.source_title,
                source_url: record.source_url,
                confidence_score: entry.confidence || 0.8,
                pattern_matched: entry.pattern_matched,
                context: entry.context,
                citations: entry.citations || []
              }])
              .select()
              .single();
            
            if (!ofcError) {
              ofcCount++;
            }
          }
        }
      }
      
      // Create submission source if not exists
      if (record.source_url && !record.source_url.includes('temp')) {
        const { data: sourceData, error: sourceError } = await supabase
          .from('submission_sources')
          .insert([{
            submission_id: submission_id,
            source_text: record.source_title || 'Document Source',
            reference_number: `REF-${Date.now()}`,
            source_title: record.source_title,
            source_url: record.source_url,
            author_org: record.author_org,
            publication_year: record.publication_year,
            content_restriction: record.content_restriction || 'public'
          }])
          .select()
          .single();
        
        if (!sourceError) {
          sourceCount++;
        }
      }
    }
    
    return NextResponse.json({
      success: true,
      message: 'Structured submission data created successfully',
      data: {
        submission_id: submission_id,
        vulnerability_id: vulnData.id,
        ofc_count: ofcCount,
        source_count: sourceCount
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
