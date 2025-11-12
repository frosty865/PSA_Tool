import { NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

export const dynamic = 'force-dynamic'

// Use service role for admin operations
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
)

/**
 * PATCH /api/submissions/[id]/ofcs/[ofcId]
 * Update an OFC in a submission
 */
export async function PATCH(request, { params }) {
  try {
    const { id: submissionId, ofcId } = await params
    const body = await request.json()
    
    const { option_text, discipline, sector, subsector, confidence_score } = body
    
    if (!supabase) {
      return NextResponse.json(
        { error: 'Server configuration error' },
        { status: 500 }
      )
    }
    
    // Build update object
    const updates = {}
    if (option_text !== undefined) updates.option_text = option_text
    if (discipline !== undefined) updates.discipline = discipline
    if (sector !== undefined) updates.sector = sector
    if (subsector !== undefined) updates.subsector = subsector
    if (confidence_score !== undefined) updates.confidence_score = confidence_score
    
    const { data, error } = await supabase
      .from('submission_options_for_consideration')
      .update(updates)
      .eq('id', ofcId)
      .eq('submission_id', submissionId)
      .select()
      .single()
    
    if (error) {
      console.error('Error updating OFC:', error)
      return NextResponse.json(
        { error: error.message || 'Failed to update OFC' },
        { status: 500 }
      )
    }
    
    return NextResponse.json({ success: true, data })
  } catch (err) {
    console.error('Error in PATCH OFC:', err)
    return NextResponse.json(
      { error: err.message || 'Internal server error' },
      { status: 500 }
    )
  }
}

