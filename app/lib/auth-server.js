// Server-side auth service for API routes
import { cookies } from 'next/headers';
import { supabaseAdmin } from '@/app/lib/supabase-admin.js';

export const AuthService = {
  /**
   * Verify a token and return user info
   */
  async verifyToken(token) {
    try {
      if (!supabaseAdmin) {
        return { success: false, error: 'Server configuration error' };
      }

      const { data: { user }, error: userError } = await supabaseAdmin.auth.getUser(token);
      
      if (userError || !user) {
        return { success: false, error: 'Invalid token' };
      }

      // Get user profile
      let { data: profile } = await supabaseAdmin
        .from('users_profiles')
        .select('role')
        .eq('user_id', user.id)
        .maybeSingle();
      
      if (!profile) {
        const resp = await supabaseAdmin
          .from('users_profiles')
          .select('role')
          .eq('id', user.id)
          .maybeSingle();
        profile = resp.data || null;
      }

      const derivedRole = String(
        profile?.role || user.user_metadata?.role || 'user'
      ).toLowerCase();

      return {
        success: true,
        user: {
          id: user.id,
          email: user.email,
          role: derivedRole
        }
      };
    } catch (error) {
      console.error('[AuthService] Error:', error);
      return { success: false, error: error.message };
    }
  },

  /**
   * Get token from request (header or cookies)
   */
  getTokenFromRequest(request) {
    // Try Authorization header first
    const authHeader = request.headers.get('authorization');
    if (authHeader && authHeader.toLowerCase().startsWith('bearer ')) {
      return authHeader.slice(7).trim();
    }

    // Fallback to cookies
    try {
      const cookieStore = cookies();
      const sbAccessToken = cookieStore.get('sb-access-token');
      if (sbAccessToken) {
        return sbAccessToken.value;
      }
    } catch (cookieError) {
      // Cookies might not be available
    }

    return null;
  },

  /**
   * Get user permissions based on role
   */
  getUserPermissions(role) {
    const roleLower = String(role || 'user').toLowerCase();
    const permissions = {
      canViewDashboard: true,
      canSubmitVOFC: true,
      canReviewSubmissions: ['admin', 'spsa', 'psa', 'analyst'].includes(roleLower),
      canManageUsers: ['admin', 'spsa'].includes(roleLower),
      canManageOFCs: ['admin', 'spsa'].includes(roleLower),
      canManageVulnerabilities: ['admin', 'spsa', 'psa'].includes(roleLower),
      canAccessAdmin: ['admin', 'spsa', 'psa', 'analyst'].includes(roleLower)
    };
    return permissions;
  }
};

