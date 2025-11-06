/**
 * Audit Logger Utility
 * Logs all admin review actions to the audit_log table
 */

import { supabaseAdmin } from './supabase-admin.js';

/**
 * Log an audit event for admin review actions
 * 
 * @param {string} submissionId - UUID of the submission
 * @param {string} reviewerId - UUID of the reviewer (from auth token)
 * @param {string} action - "approved" | "rejected" | "edited"
 * @param {Array} vulnIds - Array of vulnerability IDs that were affected
 * @param {Array} ofcIds - Array of OFC IDs that were affected
 * @param {string} notes - Optional reviewer comments/notes
 * @returns {Promise<Object|null>} The inserted audit log entry or null on error
 */
export async function logAuditEvent(submissionId, reviewerId, action, vulnIds = [], ofcIds = [], notes = null) {
  try {
    if (!supabaseAdmin) {
      console.error('[Audit Logger] Supabase admin client not available');
      return null;
    }

    // Validate action
    const validActions = ['approved', 'rejected', 'edited'];
    if (!validActions.includes(action)) {
      console.error(`[Audit Logger] Invalid action: ${action}`);
      return null;
    }

    const payload = {
      submission_id: submissionId,
      reviewer_id: reviewerId || null, // Allow null for system actions
      action: action,
      affected_vuln_ids: Array.isArray(vulnIds) ? vulnIds : [],
      affected_ofc_ids: Array.isArray(ofcIds) ? ofcIds : [],
      notes: notes || null,
      timestamp: new Date().toISOString()
    };

    const { data, error } = await supabaseAdmin
      .from('audit_log')
      .insert(payload)
      .select()
      .single();

    if (error) {
      // If table doesn't exist, log warning but don't fail
      if (error.code === '42P01' || error.message?.includes('does not exist')) {
        console.warn('[Audit Logger] audit_log table does not exist. Please create it in Supabase.');
        return null;
      }
      console.error('[Audit Logger] Error inserting audit log:', error);
      return null;
    }

    console.log(`[Audit Logger] Logged ${action} action for submission ${submissionId} by reviewer ${reviewerId}`);
    return data;
  } catch (err) {
    console.error('[Audit Logger] Exception logging audit event:', err);
    return null;
  }
}

/**
 * Get reviewer ID from authorization header
 * 
 * @param {Request} request - Next.js request object
 * @returns {Promise<string|null>} Reviewer user ID or null
 */
export async function getReviewerId(request) {
  try {
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.toLowerCase().startsWith('bearer ')) {
      return null;
    }

    const accessToken = authHeader.slice(7).trim();
    if (!supabaseAdmin) {
      return null;
    }

    const { data: { user }, error } = await supabaseAdmin.auth.getUser(accessToken);
    if (error || !user) {
      return null;
    }

    return user.id;
  } catch (err) {
    console.warn('[Audit Logger] Could not get reviewer ID:', err);
    return null;
  }
}

