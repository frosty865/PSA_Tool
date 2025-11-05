// Client-side Supabase client (browser)
// Use this for client components and pages

import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  if (typeof window !== 'undefined') {
    console.error('❌ Missing Supabase environment variables (NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY)')
  }
}

// Singleton client instance
let supabaseInstance = null

function createSupabaseClient() {
  if (supabaseInstance) {
    return supabaseInstance
  }

  // Client-side: use window object to ensure single instance
  if (typeof window !== 'undefined') {
    if (window.__supabaseClientInstance) {
      return window.__supabaseClientInstance
    }

    const clientOptions = {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
        flowType: 'pkce',
        storage: window.localStorage,
        storageKey: 'sb-auth-token'
      }
    }

    supabaseInstance = createClient(supabaseUrl, supabaseAnonKey, clientOptions)
    window.__supabaseClientInstance = supabaseInstance
    return supabaseInstance
  }

  // Server-side: return null (use supabase-admin for server)
  return null
}

export const supabase = createSupabaseClient()
export default supabase

