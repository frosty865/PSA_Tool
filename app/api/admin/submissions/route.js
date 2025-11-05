import { NextResponse } from 'next/server'
import { supabaseAdmin } from '@/app/lib/supabase-admin.js'

export const dynamic = 'force-dynamic'

export async function GET(request) {
  // Check admin authentication using Supabase token
  try {
    // Get token from Authorization header
    const authHeader = request.headers.get('authorization')
    let accessToken = null
    
    if (authHeader && authHeader.toLowerCase().startsWith('bearer ')) {
      accessToken = authHeader.slice(7).trim()
    }
    
    if (!accessToken) {
      return NextResponse.json(
        { error: 'No authentication token provided' },
        { status: 401 }
      )
    }
    
    // Verify token and check admin role
    if (!supabaseAdmin) {
      return NextResponse.json(
        { error: 'Server configuration error: Supabase admin client not available' },
        { status: 500 }
      )
    }
    
    const { data: { user }, error: userError } = await supabaseAdmin.auth.getUser(accessToken)
    
    if (userError || !user) {
      return NextResponse.json(
        { error: 'Invalid authentication token' },
        { status: 401 }
      )
    }
    
    // Check user role
    const { data: profile } = await supabaseAdmin
      .from('user_profiles')
      .select('role')
      .eq('user_id', user.id)
      .maybeSingle()
    
    const derivedRole = String(
      profile?.role || user.user_metadata?.role || 'user'
    ).toLowerCase()
    
    // Check if admin via role or email allowlist
    const isAdmin = ['admin', 'spsa'].includes(derivedRole)
    const allowlist = (process.env.ADMIN_EMAILS || '').toLowerCase().split(',').map(s => s.trim()).filter(Boolean)
    const isEmailAdmin = allowlist.includes(String(user.email).toLowerCase())
    
    if (!isAdmin && !isEmailAdmin) {
      return NextResponse.json(
        { error: 'Admin access required' },
        { status: 403 }
      )
    }
  } catch (authException) {
    console.error('Auth check error:', authException)
    return NextResponse.json(
      { error: 'Authentication failed' },
      { status: 401 }
    )
  }

  try {
    if (!supabaseAdmin) {
      return NextResponse.json({ error: 'Missing Supabase configuration' }, { status: 500 })
    }

    const supabase = supabaseAdmin

    const url = new URL(request.url)
    const status = url.searchParams.get('status') || 'pending_review'
    const source = url.searchParams.get('source') // Optional source filter

    let query = supabase
      .from('submissions')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(100)

    if (status) {
      query = query.eq('status', status)
    }
    
    // Include file_processing source submissions (processed folder files)
    // Don't filter by source unless explicitly requested
    if (source) {
      query = query.eq('source', source)
    }

    const { data, error: dbError } = await query

    if (dbError) {
      console.error('Database error:', dbError)
      return NextResponse.json({ error: dbError.message }, { status: 500 })
    }

    console.log(`[Admin Submissions API] Found ${data?.length || 0} submissions with status="${status}"${source ? ` and source="${source}"` : ''}`)
    
    // Return in expected format for SubmissionReview component
    return NextResponse.json({
      success: true,
      allSubmissions: Array.isArray(data) ? data : [],
      submissions: Array.isArray(data) ? data : []
    })
  } catch (e) {
    console.error('Admin submissions API error:', e)
    return NextResponse.json({ error: e.message }, { status: 500 })
  }
}
