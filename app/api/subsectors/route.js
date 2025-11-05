import { NextResponse } from 'next/server'
import { supabaseAdmin } from '@/app/lib/supabase-admin.js'

export const dynamic = 'force-dynamic'

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url)
    const sectorId = searchParams.get('sectorId')

    if (!sectorId) {
      return NextResponse.json(
        { error: 'sectorId parameter is required', subsectors: [] },
        { status: 400 }
      )
    }

    if (!supabaseAdmin) {
      return NextResponse.json(
        { error: 'Server configuration error: Supabase admin client not available' },
        { status: 500 }
      )
    }

    // Fetch subsectors by sector ID using admin client (bypasses RLS)
    const { data, error } = await supabaseAdmin
      .from('subsectors')
      .select('id, name, sector_id, description')
      .eq('sector_id', sectorId)
      .order('name')

    if (error) {
      console.error('[API /api/subsectors] Error:', error)
      return NextResponse.json(
        { error: error.message, subsectors: [] },
        { status: 500 }
      )
    }

    console.log(`[API /api/subsectors] Fetched ${data?.length || 0} subsectors for sectorId: ${sectorId}`)
    
    return NextResponse.json({ subsectors: data || [] })
  } catch (err) {
    console.error('[API /api/subsectors] Exception:', err)
    return NextResponse.json(
      { error: err.message, subsectors: [] },
      { status: 500 }
    )
  }
}

