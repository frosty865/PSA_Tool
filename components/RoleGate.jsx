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
        // First, try to get session from Supabase client (localStorage)
        let session = null
        let sessionError = null
        
        try {
          const sessionResult = await supabase.auth.getSession()
          session = sessionResult.data?.session
          sessionError = sessionResult.error
        } catch (err) {
          sessionError = err
        }

        // If no session from Supabase client, try to verify via API (cookies are httpOnly)
        if (!session && typeof window !== 'undefined') {
          try {
            console.log('[RoleGate] No session in localStorage, checking via API...')
            // Try to verify session via API endpoint (which can read httpOnly cookies)
            const verifyRes = await fetch('/api/auth/verify', {
              method: 'GET',
              credentials: 'include',
              headers: {
                'Accept': 'application/json'
              }
            })
            
            if (verifyRes.ok) {
              const verifyData = await verifyRes.json()
              if (verifyData.success && verifyData.session?.access_token) {
                console.log('[RoleGate] Found session via API, setting in client...')
                // Set the session in Supabase client using the token from API
                const { data: { session: apiSession }, error: setError } = await supabase.auth.setSession({
                  access_token: verifyData.session.access_token,
                  refresh_token: verifyData.session.refresh_token || ''
                })
                
                if (!setError && apiSession) {
                  session = apiSession
                  console.log('[RoleGate] Session restored from API')
                } else if (setError) {
                  console.warn('[RoleGate] Error setting session from API:', setError.message)
                }
              }
            }
          } catch (apiError) {
            console.warn('[RoleGate] Error checking session via API:', apiError)
          }
        }

        if (sessionError || !session) {
          if (sessionError) {
            console.error('[RoleGate] Session error:', sessionError.message)
          } else {
            console.warn('[RoleGate] No session found (checked localStorage and cookies) → redirecting to /splash')
          }
          if (isMounted) {
            setLoading(false)
            router.replace('/splash')
          }
          return
        }

        const userId = session.user.id
        console.log('[RoleGate] User ID:', userId)

        // Try to get user info from verify endpoint first (more reliable)
        let userRole = null
        let profile = null
        
        try {
          const verifyRes = await fetch('/api/auth/verify', {
            method: 'GET',
            credentials: 'include',
            headers: {
              'Accept': 'application/json',
              'Authorization': `Bearer ${session.access_token}`
            }
          })
          
          if (verifyRes.ok) {
            const verifyData = await verifyRes.json()
            if (verifyData.success && verifyData.user) {
              userRole = String(verifyData.user.role || 'user').toLowerCase()
              console.log('[RoleGate] Got role from verify endpoint:', userRole)
            }
          }
        } catch (verifyErr) {
          console.warn('[RoleGate] Verify endpoint failed, falling back to direct lookup:', verifyErr)
        }

        // Fallback: Try users_profiles table directly if verify endpoint didn't work
        if (!userRole) {
          let profileError = null

          // Try users_profiles first (by user_id)
          const { data: userProfile, error: userProfileError } = await supabase
            .from('users_profiles')
            .select('role')
            .eq('user_id', userId)
            .maybeSingle()

          if (!userProfileError && userProfile) {
            profile = userProfile
            userRole = String(userProfile.role || 'user').toLowerCase()
            console.log('[RoleGate] Got role from users_profiles (user_id):', userRole)
          } else {
            // Try users_profiles by id
            const { data: userProfileById, error: userProfileByIdError } = await supabase
              .from('users_profiles')
              .select('role')
              .eq('id', userId)
              .maybeSingle()

            if (!userProfileByIdError && userProfileById) {
              profile = userProfileById
              userRole = String(userProfileById.role || 'user').toLowerCase()
              console.log('[RoleGate] Got role from users_profiles (id):', userRole)
            } else {
              // Fallback to profiles table
              const { data: profilesData, error: profilesError } = await supabase
                .from('profiles')
                .select('role')
                .eq('id', userId)
                .maybeSingle()

              if (!profilesError && profilesData) {
                profile = profilesData
                userRole = String(profilesData.role || 'user').toLowerCase()
                console.log('[RoleGate] Got role from profiles:', userRole)
              } else {
                profileError = profilesError || userProfileByIdError || userProfileError
                console.error('[RoleGate] All profile lookups failed:', {
                  userProfileError: userProfileError?.message,
                  userProfileByIdError: userProfileByIdError?.message,
                  profilesError: profilesError?.message
                })
              }
            }
          }

          if (!userRole) {
            console.error('[RoleGate] Could not determine user role')
            if (isMounted) {
              setLoading(false)
              router.replace('/splash')
            }
            return
          }
        }

        const normalizedRequiredRole = String(requiredRole).toLowerCase()
        console.log('[RoleGate] Role check:', { userRole, requiredRole: normalizedRequiredRole })

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
          router.replace('/splash')
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


