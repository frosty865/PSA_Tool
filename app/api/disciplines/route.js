import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/app/lib/supabase-admin.js';
import { applyCacheHeaders, CacheStrategies } from '../middleware/cache.js';

// Disciplines rarely change - cache for 1 hour with ISR
export const revalidate = 3600; // 1 hour

// Get all disciplines
export async function GET(request) {
  try {
    // Check if supabaseAdmin is available
    if (!supabaseAdmin) {
      console.error('Supabase admin client not available');
      return NextResponse.json(
        { success: false, error: 'Database connection not available', disciplines: [] },
        { status: 503 }
      );
    }

    const { searchParams } = new URL(request.url);
    const category = searchParams.get('category');
    const active = searchParams.get('active');

    // Try nested query first (includes subtypes)
    let query = supabaseAdmin
      .from('disciplines')
      .select('*, discipline_subtypes(id, name, description, code, is_active)')
      .order('category, name');

    // Filter by category if provided
    if (category) {
      query = query.eq('category', category);
    }

    // Filter by active status if provided
    if (active !== null) {
      query = query.eq('is_active', active === 'true');
    }

    let { data, error } = await query;

    // If nested query fails, try fetching disciplines and subtypes separately
    if (error) {
      console.warn('Nested query failed, trying separate queries:', error.message);
      
      // Fetch disciplines separately
      let disciplinesQuery = supabaseAdmin
        .from('disciplines')
        .select('*')
        .order('category, name');

      if (category) {
        disciplinesQuery = disciplinesQuery.eq('category', category);
      }

      if (active !== null) {
        disciplinesQuery = disciplinesQuery.eq('is_active', active === 'true');
      }

      const { data: disciplinesData, error: disciplinesError } = await disciplinesQuery;

      if (disciplinesError) {
        throw disciplinesError;
      }

      // Fetch subtypes separately and attach to disciplines
      const { data: subtypesData, error: subtypesError } = await supabaseAdmin
        .from('discipline_subtypes')
        .select('*')
        .eq('is_active', true);

      if (!subtypesError && subtypesData) {
        // Group subtypes by discipline_id
        const subtypesByDiscipline = {};
        subtypesData.forEach(subtype => {
          if (!subtypesByDiscipline[subtype.discipline_id]) {
            subtypesByDiscipline[subtype.discipline_id] = [];
          }
          subtypesByDiscipline[subtype.discipline_id].push({
            id: subtype.id,
            name: subtype.name,
            description: subtype.description,
            code: subtype.code,
            is_active: subtype.is_active
          });
        });

        // Attach subtypes to each discipline
        data = (disciplinesData || []).map(discipline => ({
          ...discipline,
          discipline_subtypes: subtypesByDiscipline[discipline.id] || []
        }));
      } else {
        // If subtypes query fails, just return disciplines without subtypes
        data = disciplinesData || [];
      }
    }

    const response = NextResponse.json({
      success: true,
      disciplines: data || []
    });
    // Cache for 1 hour (disciplines rarely change)
    return applyCacheHeaders(response, CacheStrategies.LONG);

  } catch (error) {
    console.error('Error fetching disciplines:', error);
    // Always return valid JSON, even on error
    return NextResponse.json(
      { 
        success: false, 
        error: error.message || 'Failed to fetch disciplines',
        disciplines: []
      },
      { status: 500 }
    );
  }
}

// Create a new discipline
export async function POST(request) {
  try {
    const { name, description, category, is_active = true } = await request.json();

    if (!name) {
      return NextResponse.json(
        { success: false, error: 'Discipline name is required' },
        { status: 400 }
      );
    }

    const { data, error } = await supabaseAdmin
      .from('disciplines')
      .insert({
        name,
        description,
        category,
        is_active
      })
      .select()
      .single();

    if (error) {
      throw error;
    }

    return NextResponse.json({
      success: true,
      discipline: data
    });

  } catch (error) {
    console.error('Error creating discipline:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to create discipline' },
      { status: 500 }
    );
  }
}
