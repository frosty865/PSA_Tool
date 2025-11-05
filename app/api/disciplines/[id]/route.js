import { NextResponse } from 'next/server';
import { supabase } from '../../../lib/supabaseClient';

// Get a specific discipline
export async function GET(request, { params }) {
  try {
    const { id } = params;

    const { data, error } = await supabase
      .from('disciplines')
      .select('*')
      .eq('id', id)
      .single();

    if (error) {
      throw error;
    }

    return NextResponse.json({
      success: true,
      discipline: data
    });

  } catch (error) {
    console.error('Error fetching discipline:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to fetch discipline' },
      { status: 500 }
    );
  }
}

// Update a discipline
export async function PUT(request, { params }) {
  try {
    const { id } = params;
    const { name, description, category, is_active } = await request.json();

    if (!name) {
      return NextResponse.json(
        { success: false, error: 'Discipline name is required' },
        { status: 400 }
      );
    }

    const { data, error } = await supabase
      .from('disciplines')
      .update({
        name,
        description,
        category,
        is_active,
        updated_at: new Date().toISOString()
      })
      .eq('id', id)
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
    console.error('Error updating discipline:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to update discipline' },
      { status: 500 }
    );
  }
}

// Delete a discipline
export async function DELETE(request, { params }) {
  try {
    const { id } = params;

    // Check if discipline is being used by vulnerabilities or OFCs
    const { data: vulnCount } = await supabase
      .from('vulnerabilities')
      .select('id', { count: 'exact' })
      .eq('discipline_id', id);

    const { data: ofcCount } = await supabase
      .from('options_for_consideration')
      .select('id', { count: 'exact' })
      .eq('discipline_id', id);

    if (vulnCount?.length > 0 || ofcCount?.length > 0) {
      return NextResponse.json(
        { 
          success: false, 
          error: 'Cannot delete discipline that is being used by vulnerabilities or OFCs' 
        },
        { status: 400 }
      );
    }

    const { error } = await supabase
      .from('disciplines')
      .delete()
      .eq('id', id);

    if (error) {
      throw error;
    }

    return NextResponse.json({
      success: true,
      message: 'Discipline deleted successfully'
    });

  } catch (error) {
    console.error('Error deleting discipline:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to delete discipline' },
      { status: 500 }
    );
  }
}
