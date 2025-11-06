import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/app/lib/supabase-admin.js';

export const dynamic = 'force-dynamic';

export async function GET(request) {
  // Check admin authentication
  try {
    const authHeader = request.headers.get('authorization');
    let accessToken = null;
    
    if (authHeader && authHeader.toLowerCase().startsWith('bearer ')) {
      accessToken = authHeader.slice(7).trim();
    }
    
    if (!accessToken) {
      return NextResponse.json(
        { error: 'No authentication token provided' },
        { status: 401 }
      );
    }
    
    if (!supabaseAdmin) {
      return NextResponse.json(
        { error: 'Server configuration error: Supabase admin client not available' },
        { status: 500 }
      );
    }
    
    // Verify token and check admin role
    const { data: { user }, error: userError } = await supabaseAdmin.auth.getUser(accessToken);
    
    if (userError || !user) {
      return NextResponse.json(
        { error: 'Invalid authentication token' },
        { status: 401 }
      );
    }
    
    // Check user role
    const { data: profile } = await supabaseAdmin
      .from('users_profiles')
      .select('role')
      .eq('user_id', user.id)
      .maybeSingle();
    
    const derivedRole = String(
      profile?.role || user.user_metadata?.role || 'user'
    ).toLowerCase();
    
    const isAdmin = ['admin', 'spsa'].includes(derivedRole);
    const allowlist = (process.env.ADMIN_EMAILS || '').toLowerCase().split(',').map(s => s.trim()).filter(Boolean);
    const isEmailAdmin = allowlist.includes(String(user.email).toLowerCase());
    
    if (!isAdmin && !isEmailAdmin) {
      return NextResponse.json(
        { error: 'Admin access required' },
        { status: 403 }
      );
    }
  } catch (authException) {
    console.error('Auth check error:', authException);
    return NextResponse.json(
      { error: 'Authentication failed' },
      { status: 401 }
    );
  }

  try {
    if (!supabaseAdmin) {
      return NextResponse.json({ error: 'Missing Supabase configuration' }, { status: 500 });
    }

    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get('limit') || '100', 10);
    const action = url.searchParams.get('action'); // Optional filter by action
    const submissionId = url.searchParams.get('submission_id'); // Optional filter by submission

    let query = supabaseAdmin
      .from('audit_log')
      .select('*')
      .order('timestamp', { ascending: false })
      .limit(limit);

    // Apply filters if provided
    if (action) {
      query = query.eq('action', action);
    }
    
    if (submissionId) {
      query = query.eq('submission_id', submissionId);
    }

    const { data, error: dbError } = await query;

    if (dbError) {
      // If table doesn't exist, return empty array with warning
      if (dbError.code === '42P01' || dbError.message?.includes('does not exist')) {
        console.warn('[Audit API] audit_log table does not exist. Please create it in Supabase.');
        return NextResponse.json({
          logs: [],
          warning: 'audit_log table does not exist. Please create it in Supabase.'
        });
      }
      
      console.error('Database error:', dbError);
      return NextResponse.json({ error: dbError.message }, { status: 500 });
    }

    return NextResponse.json({
      logs: Array.isArray(data) ? data : [],
      count: Array.isArray(data) ? data.length : 0
    });
  } catch (e) {
    console.error('Admin audit API error:', e);
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}

