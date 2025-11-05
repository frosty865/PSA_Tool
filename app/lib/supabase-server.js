// DEPRECATED: Use lib/supabase-client.js instead
// This file is kept for backward compatibility
import { supabase, supabaseAdmin } from '../../lib/supabase-client.js'

export const supabaseServer = supabaseAdmin;
export const supabaseClient = supabase;
