'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/app/lib/supabase-client.js'

/**
 * RoleGate Component
 * Wraps admin pages and allows access only to users with the required role.
 * Supports 'admin', 'spsa', 'psa', or custom roles.
 * 
 * @param {React.ReactNode} children - Content to render if authorized
 * @param {string} requiredRole - Required role to access (default: 'admin')
 */
export default function RoleGate({ children, requiredRole = 'admin' }) {
  const [authorized, setAuthorized] = useState(false)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    let isMounted = true

    async function checkRole() {
      try {
        const {
          data: { session },
          error: sessionError
        } = await supabase.auth.getSession()

        if (sessionError || !session) {
          if (sessionError) {
            console.error('[RoleGate] Session error:', sessionError.message)
          } else {
            console.warn('[RoleGate] No session → redirecting to /login')
          }
          if (isMounted) {
            setLoading(false)
            router.replace('/login')
          }
          return
        }

        const userId = session.user.id

        // Try user_profiles table first (your schema), fallback to profiles
        let profile = null
        let profileError = null

        // Try user_profiles first
        const { data: userProfile, error: userProfileError } = await supabase
          .from('user_profiles')
          .select('role')
          .eq('user_id', userId)
          .maybeSingle()

        if (!userProfileError && userProfile) {
          profile = userProfile
        } else {
          // Fallback to profiles table
          const { data: profilesData, error: profilesError } = await supabase
            .from('profiles')
            .select('role')
            .eq('id', userId)
            .maybeSingle()

          if (!profilesError && profilesData) {
            profile = profilesData
          } else {
            profileError = profilesError || userProfileError
          }
        }

        if (profileError || !profile) {
          console.error('[RoleGate] Profile lookup failed:', profileError?.message || 'Profile not found')
          if (isMounted) {
            setLoading(false)
            router.replace('/login')
          }
          return
        }

        const userRole = String(profile?.role || 'user').toLowerCase()
        const normalizedRequiredRole = String(requiredRole).toLowerCase()

        // Support multiple role checks: admin/spsa for admin access, or exact match
        if (normalizedRequiredRole === 'admin') {
          // For admin, allow both 'admin' and 'spsa' roles
          if (['admin', 'spsa'].includes(userRole)) {
            if (isMounted) {
              setAuthorized(true)
              setLoading(false)
            }
          } else {
            console.warn(`[RoleGate] User not ${requiredRole} (has: ${userRole}) → redirecting`)
            if (isMounted) {
              setLoading(false)
              router.replace('/')
            }
          }
        } else {
          // For other roles, require exact match
          if (userRole === normalizedRequiredRole) {
            if (isMounted) {
              setAuthorized(true)
              setLoading(false)
            }
          } else {
            console.warn(`[RoleGate] User not ${requiredRole} (has: ${userRole}) → redirecting`)
            if (isMounted) {
              setLoading(false)
              router.replace('/')
            }
          }
        }
      } catch (err) {
        console.error('[RoleGate] Error:', err)
        if (isMounted) {
          setLoading(false)
          router.replace('/login')
        }
      }
    }

    checkRole()

    return () => {
      isMounted = false
    }
  }, [router, requiredRole])

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#555' }}>
        Checking permissions…
      </div>
    )
  }

  if (!authorized) return null

  return <>{children}</>
}

/**
 * Helper for role checks elsewhere
 */
export function hasAdminAccess(role) {
  return ['admin', 'spsa'].includes((role || '').toLowerCase())
}


