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
    const {
      data: { session },
      error: sessionError,
    } = await supabase.auth.getSession()

    if (sessionError) {
      console.warn('[fetchWithAuth] session error:', sessionError.message)
    }

    const token = session?.access_token

    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
      ...(token
        ? { Authorization: `Bearer ${token}` }
        : {
            apikey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
            Authorization: `Bearer ${process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY}`,
          }),
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
        window.location.href = '/login'
      }
    }

    return res
  } catch (err) {
    console.error('[fetchWithAuth] network error:', err)
    throw err
  }
}

