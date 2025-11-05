import { NextResponse } from 'next/server';
import { supabase } from '../../lib/supabaseClient';
import { applyCacheHeaders, CacheStrategies } from '@/app/api/middleware/cache.js';

// Disciplines rarely change - cache for 1 hour with ISR
export const revalidate = 3600; // 1 hour

// Get all disciplines
export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const category = searchParams.get('category');
    const active = searchParams.get('active');

    let query = supabase
      .from('disciplines')
      .select('*')
      .order('category, name');

    // Filter by category if provided
    if (category) {
      query = query.eq('category', category);
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
      disciplines: data || []
    });
    // Cache for 1 hour (disciplines rarely change)
    return applyCacheHeaders(response, CacheStrategies.LONG);

  } catch (error) {
    console.error('Error fetching disciplines:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to fetch disciplines' },
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

    const { data, error } = await supabase
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
