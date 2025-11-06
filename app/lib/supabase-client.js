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
  // Server-side: return a safe dummy object to prevent SSR errors
  if (typeof window === 'undefined') {
    return {
      auth: {
        getSession: async () => ({ data: { session: null }, error: null }),
        signOut: async () => ({ error: null }),
        onAuthStateChange: () => ({ data: { subscription: null }, error: null })
      }
    }
  }

  // Client-side: use window object to ensure single instance
  if (window.__supabaseClientInstance) {
    return window.__supabaseClientInstance
  }

  if (supabaseInstance) {
    window.__supabaseClientInstance = supabaseInstance
    return supabaseInstance
  }

  // Validate environment variables
  if (!supabaseUrl || !supabaseAnonKey) {
    console.error('❌ Missing Supabase environment variables (NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY)')
    // Return dummy object even on client if env vars are missing
    return {
      auth: {
        getSession: async () => ({ data: { session: null }, error: null }),
        signOut: async () => ({ error: null }),
        onAuthStateChange: () => ({ data: { subscription: null }, error: null })
      }
    }
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

export const supabase = createSupabaseClient()
export default supabase

