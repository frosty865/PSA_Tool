// Auth functions using Supabase authentication with server verification endpoint
import { supabase } from './supabase-client.js';

export const getCurrentUser = async () => {
  try {
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;
    // If no session, treat as unauthenticated without calling server
    if (!token) return null;
    const res = await fetch('/api/auth/verify', {
      method: 'GET',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      credentials: 'include'
    });
    if (!res.ok) return null;
    const result = await res.json();
    if (!result.success || !result.user) return null;
    return {
      id: result.user.id,
      email: result.user.email,
      role: result.user.role,
      name: result.user.name,
      full_name: result.user.name
    };
  } catch (error) {
    console.error('Error getting current user:', error);
    return null;
  }
};

export const getUserProfile = async (userId = null) => {
  // For now, mirror getCurrentUser via server verification; ignore other IDs client-side
  return await getCurrentUser();
};

export const canAccessAdmin = async () => {
  try {
    const user = await getCurrentUser();
    if (!user) return false;
    
    return ['admin', 'spsa', 'analyst', 'psa'].includes(user.role);
  } catch (error) {
    console.error('Error checking admin access:', error);
    return false;
  }
};

export const canSubmitVOFC = async () => {
  try {
    const user = await getCurrentUser();
    // Allow any authenticated user to submit documents (RLS will enforce specifics)
    return !!user;
  } catch (error) {
    console.error('Error checking submit access:', error);
    return false;
  }
};

export const logout = async () => {
  try {
    const { error } = await supabase.auth.signOut();

    if (error) {
      console.error('Logout error:', error);
    } else {
      window.location.href = '/splash';
    }
  } catch (error) {
    console.error('Logout error:', error);
  }
};

// User role constants and utilities
export const USER_ROLES = {
  ADMIN: 'admin',
  SPSA: 'spsa',
  PSA: 'psa',
  ANALYST: 'analyst',
  VALIDATOR: 'validator'
};

export const getRoleDisplayName = (role) => {
  const roleNames = {
    'admin': 'Administrator',
    'spsa': 'Senior PSA',
    'psa': 'PSA',
    'analyst': 'Analyst',
    'validator': 'Validator'
  };
  return roleNames[role] || role;
};

export const getRoleBadgeColor = (role) => {
  const colors = {
    'admin': 'bg-red-100 text-red-800',
    'spsa': 'bg-purple-100 text-purple-800',
    'psa': 'bg-blue-100 text-blue-800',
    'analyst': 'bg-green-100 text-green-800',
    'validator': 'bg-yellow-100 text-yellow-800'
  };
  return colors[role] || 'bg-gray-100 text-gray-800';
};