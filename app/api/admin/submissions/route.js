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
      .from('users_profiles')
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

    // Fetch submissions with related vulnerabilities, OFCs, sources, and OFC-source links
    let query = supabase
      .from('submissions')
      .select(`
        *,
        submission_vulnerabilities (
          id,
          vulnerability,
          discipline,
          sector,
          subsector,
          audit_status,
          source,
          source_title
        ),
        submission_options_for_consideration (
          id,
          option_text,
          discipline,
          confidence_score,
          audit_status,
          source,
          source_title
        ),
        submission_sources (
          id,
          source_text,
          source_title,
          source_url,
          author_org,
          publication_year
        ),
        submission_ofc_sources (
          id,
          ofc_id,
          source_id
        )
      `)
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
      console.error('[Admin Submissions API] Database error:', JSON.stringify(dbError, null, 2))
      console.error('[Admin Submissions API] Query status:', status)
      console.error('[Admin Submissions API] Query source:', source)
      return NextResponse.json({ 
        error: dbError.message,
        code: dbError.code,
        hint: dbError.hint,
        details: dbError.details
      }, { status: 500 })
    }

    console.log(`[Admin Submissions API] Found ${data?.length || 0} submissions with status="${status}"${source ? ` and source="${source}"` : ''}`)
    
    // Enrich submissions with counts, extract source_file from data JSONB, and link OFCs to sources
    const enriched = (Array.isArray(data) ? data : []).map(sub => {
      // Extract source_file from data JSONB
      let sourceFile = null
      let documentName = null
      try {
        const parsedData = typeof sub.data === 'string' ? JSON.parse(sub.data) : sub.data
        sourceFile = parsedData?.source_file || parsedData?.sourceFile || null
        documentName = parsedData?.document_name || parsedData?.documentName || sourceFile || null
      } catch (e) {
        // Ignore parse errors
      }
      
      // Link OFCs to their sources using submission_ofc_sources junction table
      const ofcSourceLinks = sub.submission_ofc_sources || []
      const sources = sub.submission_sources || []
      const ofcs = (sub.submission_options_for_consideration || []).map(ofc => {
        // Find all source links for this OFC
        const links = ofcSourceLinks.filter(link => link.ofc_id === ofc.id)
        const ofcSources = links.map(link => {
          return sources.find(s => s.id === link.source_id)
        }).filter(Boolean) // Remove undefined entries
        
        // If no sources linked via junction table, check if OFC has source info directly
        if (ofcSources.length === 0 && (ofc.source || ofc.source_title || ofc.source_url)) {
          // Create a source object from OFC's own source fields
          ofcSources.push({
            id: null,
            source_title: ofc.source_title || ofc.source || 'Source',
            source_url: ofc.source_url || null,
            source_text: ofc.source || null,
            author_org: null,
            publication_year: null
          })
        }
        
        return {
          ...ofc,
          sources: ofcSources
        }
      })
      
      return {
        ...sub,
        source_file: sourceFile,
        document_name: documentName || sub.document_name || `Submission ${sub.id.slice(0, 8)}`,
        vulnerability_count: sub.submission_vulnerabilities?.length || 0,
        ofc_count: sub.submission_options_for_consideration?.length || 0,
        source_count: sub.submission_sources?.length || 0,
        submission_options_for_consideration: ofcs // Replace with enriched OFCs that have sources
      }
    })
    
    // Return in expected format for SubmissionReview component
    return NextResponse.json({
      success: true,
      allSubmissions: enriched,
      submissions: enriched
    })
  } catch (e) {
    console.error('[Admin Submissions API] Unexpected error:', e)
    console.error('[Admin Submissions API] Error stack:', e.stack)
    return NextResponse.json({ 
      error: e.message || 'Internal server error',
      details: e.toString()
    }, { status: 500 })
  }
}
