// Utility to get user ID from email or UUID
import { supabaseAdmin } from '@/app/lib/supabase-admin.js';

/**
 * Get the processed_by value (UUID) from an email or UUID string
 * Returns the UUID if valid, or null if not found
 */
export async function getProcessedByValue(processedBy) {
  if (!processedBy) return null;
  
  // If it's already a UUID format, return it
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  if (uuidRegex.test(processedBy)) {
    return processedBy;
  }
  
  // If it's an email, try to find the user
  if (processedBy.includes('@')) {
    try {
      if (!supabaseAdmin) return null;
      
      // Get user by email from auth
      const { data: { users }, error } = await supabaseAdmin.auth.admin.listUsers();
      if (error) {
        console.error('[get-user-id] Error listing users:', error);
        return null;
      }
      
      const user = users?.find(u => u.email?.toLowerCase() === processedBy.toLowerCase());
      if (user) {
        return user.id;
      }
    } catch (error) {
      console.error('[get-user-id] Error getting user ID:', error);
    }
  }
  
  return null;
}

