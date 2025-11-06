import { NextResponse } from 'next/server'
import { supabaseAdmin } from '@/app/lib/supabase-admin.js'
import { applyCacheHeaders, CacheStrategies } from '../middleware/cache.js'

// Sectors rarely change - cache for 1 hour with ISR
export const revalidate = 3600 // 1 hour

export async function GET(request) {
  try {
    if (!supabaseAdmin) {
      console.error('[API /api/sectors] supabaseAdmin is null - check environment variables')
      return NextResponse.json(
        { error: 'Server configuration error: Supabase admin client not available', sectors: [] },
        { status: 500 }
      )
    }

    // Fetch sectors using admin client (bypasses RLS)
    const { data, error } = await supabaseAdmin
      .from('sectors')
      .select('*')
      .order('id')

    if (error) {
      console.error('[API /api/sectors] Supabase error:', error)
      // Return empty array instead of 500 to prevent page crashes
      return NextResponse.json(
        { error: error.message, sectors: [] },
        { status: 200 }
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
    // Return empty array instead of 500 to prevent page crashes
    return NextResponse.json(
      { error: err.message, sectors: [] },
      { status: 200 }
    )
  }
}

