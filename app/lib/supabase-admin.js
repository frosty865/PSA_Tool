// Server-side Supabase client (service role)
// Use this ONLY in API routes and server components
// NEVER use this in client components - it bypasses RLS

import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY

if (!supabaseUrl || !supabaseServiceKey) {
  if (typeof window === 'undefined') {
    console.error('❌ Missing Supabase environment variables for admin client:')
    console.error('   NEXT_PUBLIC_SUPABASE_URL:', !!supabaseUrl)
    console.error('   SUPABASE_SERVICE_ROLE_KEY:', !!supabaseServiceKey)
  }
}

// Singleton admin client instance
let supabaseAdminInstance = null

function createSupabaseAdmin() {
  if (supabaseAdminInstance) {
    return supabaseAdminInstance
  }

  // Only create on server-side - return null on client to prevent errors
  if (typeof window !== 'undefined') {
    console.warn('supabaseAdmin can only be used on the server-side. Use supabase-client for client components.')
    return null
  }

  if (!supabaseUrl || !supabaseServiceKey) {
    console.error('Cannot create Supabase admin client: missing environment variables')
    return null
  }

  supabaseAdminInstance = createClient(supabaseUrl, supabaseServiceKey, {
    auth: {
      persistSession: false,
      autoRefreshToken: false
    }
  })

  return supabaseAdminInstance
}

export const supabaseAdmin = createSupabaseAdmin()
export default supabaseAdmin

