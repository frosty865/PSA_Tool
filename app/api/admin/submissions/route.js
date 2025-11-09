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
    const countOnly = url.searchParams.get('count_only') === 'true' // If true, just return count

    // If count_only is requested, return just the count from database
    if (countOnly) {
      let countQuery = supabase
        .from('submissions')
        .select('*', { count: 'exact', head: true })
      
      if (status) {
        countQuery = countQuery.eq('status', status)
      }
      
      if (source) {
        countQuery = countQuery.eq('source', source)
      }
      
      const { count, error: countError } = await countQuery
      
      if (countError) {
        console.error('[Admin Submissions API] Count query error:', countError)
        return NextResponse.json({ 
          error: countError.message || 'Failed to get count',
          code: countError.code
        }, { status: 500 })
      }
      
      return NextResponse.json({
        success: true,
        count: count || 0
      })
    }

    // Fetch submissions with related vulnerabilities, OFCs, sources, and OFC-source links
    // Use minimal select first to avoid column errors, then fetch related data separately if needed
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
          source,
          source_title
        ),
        submission_options_for_consideration (
          id,
          option_text,
          discipline,
          confidence_score,
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
      console.error('[Admin Submissions API] Error code:', dbError.code)
      console.error('[Admin Submissions API] Error message:', dbError.message)
      console.error('[Admin Submissions API] Error hint:', dbError.hint)
      console.error('[Admin Submissions API] Error details:', dbError.details)
      
      // Check for column not found errors (42883 = undefined_column, 42703 = undefined_object)
      if (dbError.code === '42883' || dbError.code === '42703' || dbError.message?.includes('column') || dbError.message?.includes('does not exist')) {
        console.error('[Admin Submissions API] Column error detected - trying fallback query without nested selects')
        
        // Fallback: fetch submissions without nested relationships
        let fallbackQuery = supabase
          .from('submissions')
          .select('*')
          .order('created_at', { ascending: false })
          .limit(100)
        
        if (status) {
          fallbackQuery = fallbackQuery.eq('status', status)
        }
        if (source) {
          fallbackQuery = fallbackQuery.eq('source', source)
        }
        
        const { data: fallbackData, error: fallbackError } = await fallbackQuery
        
        if (fallbackError) {
          return NextResponse.json({ 
            error: `Database query failed: ${fallbackError.message}`,
            code: fallbackError.code,
            hint: fallbackError.hint,
            details: fallbackError.details,
            original_error: dbError.message
          }, { status: 500 })
        }
        
        // Return submissions without nested data
        return NextResponse.json({
          success: true,
          allSubmissions: (fallbackData || []).map(sub => ({
            ...sub,
            submission_vulnerabilities: [],
            submission_options_for_consideration: [],
            submission_sources: [],
            vulnerability_count: 0,
            ofc_count: 0,
            source_count: 0
          })),
          submissions: (fallbackData || []).map(sub => ({
            ...sub,
            submission_vulnerabilities: [],
            submission_options_for_consideration: [],
            submission_sources: [],
            vulnerability_count: 0,
            ofc_count: 0,
            source_count: 0
          })),
          warning: 'Some columns may not exist in database schema. Returning submissions without nested relationships.'
        })
      }
      
      // Check for common issues
      if (dbError.code === '42P01') {
        // Table doesn't exist
        return NextResponse.json({ 
          error: `Table not found: ${dbError.message}`,
          code: dbError.code,
          hint: 'One of the referenced tables may not exist. Check database schema.',
          details: dbError.details
        }, { status: 500 })
      } else if (dbError.code === '42501') {
        // Permission denied (RLS)
        return NextResponse.json({ 
          error: 'Permission denied. Check Row Level Security policies.',
          code: dbError.code,
          hint: dbError.hint || 'The service role key may not have proper permissions.',
          details: dbError.details
        }, { status: 500 })
      }
      
      return NextResponse.json({ 
        error: dbError.message || 'Database query failed',
        code: dbError.code,
        hint: dbError.hint,
        details: dbError.details
      }, { status: 500 })
    }

    console.log(`[Admin Submissions API] Found ${data?.length || 0} submissions with status="${status}"${source ? ` and source="${source}"` : ''}`)
    
    // Fetch actual counts from database for each submission
    // Use a timeout to prevent hanging
    const submissionIds = (Array.isArray(data) ? data : []).map(sub => sub.id)
    
    // Helper function to add timeout to promises
    const withTimeout = (promise, timeoutMs = 5000) => {
      return Promise.race([
        promise,
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Query timeout')), timeoutMs)
        )
      ])
    }
    
    // Get actual counts from database by fetching all records and counting
    // Use timeout and fallback to empty object if queries fail
    let vulnCounts = {}
    let ofcCounts = {}
    let sourceCounts = {}
    
    if (submissionIds.length > 0) {
      try {
        const [vulnResult, ofcResult, sourceResult] = await Promise.allSettled([
          // Count vulnerabilities per submission
          withTimeout(
            supabase
              .from('submission_vulnerabilities')
              .select('submission_id')
              .in('submission_id', submissionIds)
              .then(result => {
                const counts = {}
                if (result.data) {
                  result.data.forEach(v => {
                    counts[v.submission_id] = (counts[v.submission_id] || 0) + 1
                  })
                }
                return counts
              }),
            5000
          ),
          
          // Count OFCs per submission
          withTimeout(
            supabase
              .from('submission_options_for_consideration')
              .select('submission_id')
              .in('submission_id', submissionIds)
              .then(result => {
                const counts = {}
                if (result.data) {
                  result.data.forEach(o => {
                    counts[o.submission_id] = (counts[o.submission_id] || 0) + 1
                  })
                }
                return counts
              }),
            5000
          ),
          
          // Count sources per submission
          withTimeout(
            supabase
              .from('submission_sources')
              .select('submission_id')
              .in('submission_id', submissionIds)
              .then(result => {
                const counts = {}
                if (result.data) {
                  result.data.forEach(s => {
                    counts[s.submission_id] = (counts[s.submission_id] || 0) + 1
                  })
                }
                return counts
              }),
            5000
          )
        ])
        
        if (vulnResult.status === 'fulfilled') {
          vulnCounts = vulnResult.value
        } else {
          console.warn('[Admin Submissions API] Failed to count vulnerabilities:', vulnResult.reason)
        }
        
        if (ofcResult.status === 'fulfilled') {
          ofcCounts = ofcResult.value
        } else {
          console.warn('[Admin Submissions API] Failed to count OFCs:', ofcResult.reason)
        }
        
        if (sourceResult.status === 'fulfilled') {
          sourceCounts = sourceResult.value
        } else {
          console.warn('[Admin Submissions API] Failed to count sources:', sourceResult.reason)
        }
      } catch (err) {
        console.error('[Admin Submissions API] Error in count queries:', err)
        // Continue with empty counts - will fall back to array lengths
      }
    }
    
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
      
      // Link OFCs to their sources
      // Note: submission_ofc_sources table may not exist, so we'll use OFC's direct source fields
      const sources = sub.submission_sources || []
      const ofcs = (sub.submission_options_for_consideration || []).map(ofc => {
        // Check if OFC has source info directly
        const ofcSources = []
        if (ofc.source || ofc.source_title || ofc.source_url) {
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
      
      // Use actual database counts instead of array lengths
      const actualVulnCount = vulnCounts[sub.id] ?? (sub.submission_vulnerabilities?.length || 0)
      const actualOfcCount = ofcCounts[sub.id] ?? (sub.submission_options_for_consideration?.length || 0)
      const actualSourceCount = sourceCounts[sub.id] ?? (sub.submission_sources?.length || 0)
      
      return {
        ...sub,
        source_file: sourceFile,
        document_name: documentName || sub.document_name || `Submission ${sub.id.slice(0, 8)}`,
        vulnerability_count: actualVulnCount,
        ofc_count: actualOfcCount,
        source_count: actualSourceCount,
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
