import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/app/lib/supabase-admin.js';
import { applyCacheHeaders, CacheStrategies } from '../../middleware/cache.js';

// Discipline subtypes rarely change - cache for 1 hour with ISR
export const revalidate = 3600; // 1 hour

// Get all discipline subtypes, optionally filtered by discipline_id
export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const disciplineId = searchParams.get('discipline_id');
    const active = searchParams.get('active');

    let query = supabaseAdmin
      .from('discipline_subtypes')
      .select('*, disciplines(id, name, code, category)')
      .order('name');

    // Filter by discipline_id if provided
    if (disciplineId) {
      query = query.eq('discipline_id', disciplineId);
    }

    // Filter by active status if provided
    if (active !== null) {
      query = query.eq('is_active', active === 'true');
    }

    const { data, error } = await query;

    if (error) {
      throw error;
    }

    const response = NextResponse.json({
      success: true,
      subtypes: data || []
    });
    // Cache for 1 hour (subtypes rarely change)
    return applyCacheHeaders(response, CacheStrategies.LONG);

  } catch (error) {
    console.error('Error fetching discipline subtypes:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to fetch discipline subtypes' },
      { status: 500 }
    );
  }
}

