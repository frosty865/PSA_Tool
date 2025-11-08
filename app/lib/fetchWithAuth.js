import { supabase } from './supabase-client.js'

/**
 * Authenticated fetch wrapper for PSA Tool frontend.
 * - Automatically attaches Supabase session token
 * - Refreshes expired sessions when possible
 * - Handles 401/403/500 errors gracefully
 * - Constructs proper URLs for local dev and production
 */
export async function fetchWithAuth(path, options = {}) {
  // Ensure absolute URL for local dev and production
  // In development, always use current origin (localhost:3000)
  // In production, use NEXT_PUBLIC_SITE_URL if set, otherwise current origin
  const baseUrl =
    (typeof window !== 'undefined'
      ? window.location.origin
      : process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000')

  const url = path.startsWith('http')
    ? path
    : `${baseUrl.replace(/\/$/, '')}${path.startsWith('/') ? '' : '/'}${path}`

  // Get current session or refresh silently
  try {
    let {
      data: { session },
      error: sessionError,
    } = await supabase.auth.getSession()

    if (sessionError) {
      console.warn('[fetchWithAuth] session error:', sessionError.message)
    }

    // If session is expired or missing, try to refresh it
    if (!session || (session.expires_at && session.expires_at * 1000 < Date.now() + 60000)) {
      // Refresh if expired or expiring within 1 minute
      console.log('[fetchWithAuth] Session expired or expiring soon, attempting refresh...')
      try {
        const { data: { session: refreshedSession }, error: refreshError } = await supabase.auth.refreshSession()
        if (!refreshError && refreshedSession) {
          session = refreshedSession
          console.log('[fetchWithAuth] Session refreshed successfully')
        } else {
          console.warn('[fetchWithAuth] Failed to refresh session:', refreshError?.message)
          // If refresh fails and we have no session, redirect immediately
          if (!session && typeof window !== 'undefined') {
            console.log('[fetchWithAuth] No valid session, redirecting to login...')
            window.location.href = '/splash'
            return new Response(null, { status: 401 })
          }
        }
      } catch (refreshErr) {
        console.error('[fetchWithAuth] Error during session refresh:', refreshErr)
        if (!session && typeof window !== 'undefined') {
          window.location.href = '/splash'
          return new Response(null, { status: 401 })
        }
      }
    }

    const token = session?.access_token

    // Don't set Content-Type for FormData - let fetch set it automatically with boundary
    const isFormData = options.body instanceof FormData
    
    const headers = {
      // Only set Content-Type if not FormData
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...(options.headers || {}),
      ...(token
        ? { Authorization: `Bearer ${token}` }
        : {
            apikey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
            Authorization: `Bearer ${process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY}`,
          }),
    }
    
    // Remove Content-Type from headers if it was set and we're using FormData
    if (isFormData && headers['Content-Type']) {
      delete headers['Content-Type']
    }

    const res = await fetch(url, {
      ...options,
      headers,
      credentials: 'include'
    })

    // Auto-handle 401/403 to trigger re-auth
    if (res.status === 401 || res.status === 403) {
      console.warn(`[fetchWithAuth] ${res.status} for ${url}`)
      if (typeof window !== 'undefined') {
        window.location.href = '/splash'
      }
    }

    return res
  } catch (err) {
    console.error('[fetchWithAuth] network error:', err)
    throw err
  }
}

