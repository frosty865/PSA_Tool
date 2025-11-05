import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

// Use service role for admin operations
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

export async function POST(request) {
  try {
    console.log('🔧 Disabling RLS on submissions table...');
    
    // Disable RLS on submissions table
    const { error } = await supabase.rpc('exec', {
      sql: 'ALTER TABLE submissions DISABLE ROW LEVEL SECURITY;'
    });
    
    if (error) {
      console.log('⚠️  Error disabling RLS:', error.message);
      return NextResponse.json({ 
        success: false, 
        error: error.message 
      }, { status: 500 });
    }

    // Test access to submissions
    console.log('🧪 Testing access to submissions...');
    const { data: submissions, error: testError } = await supabase
      .from('submissions')
      .select('*')
      .limit(5);
    
    if (testError) {
      console.log('❌ Still can\'t access submissions:', testError.message);
      return NextResponse.json({ 
        success: false, 
        error: 'Still cannot access submissions after disabling RLS' 
      }, { status: 500 });
    }

    console.log('✅ Successfully accessed submissions:', submissions?.length || 0, 'found');
    
    return NextResponse.json({
      success: true,
      message: 'RLS disabled on submissions table',
      submissionsFound: submissions?.length || 0,
      sampleSubmission: submissions?.[0]
    });

  } catch (error) {
    console.error('❌ Error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}

