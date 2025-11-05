import { NextResponse } from 'next/server'
import { supabaseAdmin } from '@/app/lib/supabase-admin.js'
import { applyCacheHeaders, CacheStrategies } from '@/app/api/middleware/cache.js'

// Sectors rarely change - cache for 1 hour with ISR
export const revalidate = 3600 // 1 hour

export async function GET(request) {
  try {
    if (!supabaseAdmin) {
      return NextResponse.json(
        { error: 'Server configuration error: Supabase admin client not available' },
        { status: 500 }
      )
    }

    // Fetch sectors using admin client (bypasses RLS)
    const { data, error } = await supabaseAdmin
      .from('sectors')
      .select('*')
      .order('id')

    if (error) {
      console.error('[API /api/sectors] Error:', error)
      return NextResponse.json(
        { error: error.message, sectors: [] },
        { status: 500 }
      )
    }

    // Normalize sector_name - use sector_name if it exists, otherwise name
    const normalizedSectors = (data || []).map(s => ({
      ...s,
      sector_name: s.sector_name || s.name || `Sector ${s.id}`
    }))

    console.log(`[API /api/sectors] Fetched ${normalizedSectors.length} sectors`)
    
    const response = NextResponse.json({ sectors: normalizedSectors })
    // Cache for 1 hour (sectors rarely change)
    return applyCacheHeaders(response, CacheStrategies.LONG)
  } catch (err) {
    console.error('[API /api/sectors] Exception:', err)
    return NextResponse.json(
      { error: err.message, sectors: [] },
      { status: 500 }
    )
  }
}

