import { NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

export const dynamic = 'force-dynamic'

// Use service role for admin operations
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
)

/**
 * PATCH /api/submissions/[id]/vulnerabilities/[vulnId]
 * Update a vulnerability in a submission
 */
export async function PATCH(request, { params }) {
  try {
    const { id: submissionId, vulnId } = await params
    const body = await request.json()
    
    const { vulnerability_name, description, discipline, sector, subsector, severity_level } = body
    
    if (!supabase) {
      return NextResponse.json(
        { error: 'Server configuration error' },
        { status: 500 }
      )
    }
    
    // Build update object
    const updates = {}
    if (vulnerability_name !== undefined) updates.vulnerability_name = vulnerability_name
    if (description !== undefined) updates.description = description
    if (discipline !== undefined) updates.discipline = discipline
    if (sector !== undefined) updates.sector = sector
    if (subsector !== undefined) updates.subsector = subsector
    if (severity_level !== undefined) updates.severity_level = severity_level
    
    // Also update the legacy "vulnerability" field for backward compatibility
    if (vulnerability_name !== undefined) {
      updates.vulnerability = vulnerability_name
    }
    
    const { data, error } = await supabase
      .from('submission_vulnerabilities')
      .update(updates)
      .eq('id', vulnId)
      .eq('submission_id', submissionId)
      .select()
      .single()
    
    if (error) {
      console.error('Error updating vulnerability:', error)
      return NextResponse.json(
        { error: error.message || 'Failed to update vulnerability' },
        { status: 500 }
      )
    }
    
    return NextResponse.json({ success: true, data })
  } catch (err) {
    console.error('Error in PATCH vulnerability:', err)
    return NextResponse.json(
      { error: err.message || 'Internal server error' },
      { status: 500 }
    )
  }
}

