'use client'
import { useEffect, useState } from 'react'
import { supabase } from '../../lib/supabaseClient'
import { fetchWithAuth } from '../../lib/fetchWithAuth'

export default function TestAuthPage() {
  const [sessionData, setSessionData] = useState(null)
  const [verifyData, setVerifyData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    const testAuth = async () => {
      try {
        // Get session
        const { data: { session }, error: sessionError } = await supabase.auth.getSession()
        if (sessionError) throw sessionError
        
        setSessionData({
          hasSession: !!session,
          hasToken: !!session?.access_token,
          email: session?.user?.email,
          userId: session?.user?.id
        })

        if (!session?.access_token) {
          setError('No access token found')
          return
        }

        // Test verify endpoint
        const res = await fetchWithAuth('/api/auth/verify', {
          method: 'GET'
        })

        const data = await res.json()
        
        if (!res.ok) {
          setError(`Verify failed: ${res.status} - ${JSON.stringify(data, null, 2)}`)
          return
        }

        setVerifyData(data)
      } catch (err) {
        setError(err.message)
      }
    }

    testAuth()
  }, [])

  return (
    <div style={{ padding: '2rem', fontFamily: 'monospace' }}>
      <h1>Auth Test Page</h1>
      
      <section style={{ marginTop: '2rem', padding: '1rem', border: '1px solid #ccc', borderRadius: '8px' }}>
        <h2>Session Data</h2>
        <pre>{JSON.stringify(sessionData, null, 2)}</pre>
      </section>

      <section style={{ marginTop: '2rem', padding: '1rem', border: '1px solid #ccc', borderRadius: '8px' }}>
        <h2>Verify API Response</h2>
        <pre>{JSON.stringify(verifyData, null, 2)}</pre>
      </section>

      {error && (
          <section style={{ marginTop: '2rem', padding: '1rem', border: '1px solid #f00', borderRadius: '8px', backgroundColor: '#fee' }}>
          <h2>Error</h2>
          <pre>{error}</pre>
        </section>
      )}

      {verifyData?.user && (
        <section style={{ marginTop: '2rem', padding: '1rem', border: '1px solid #0a0', borderRadius: '8px', backgroundColor: '#efe' }}>
          <h2>Access Check</h2>
          <p>Role: <strong>{verifyData.user.role}</strong></p>
          <p>Is Admin: <strong>{String(verifyData.user.is_admin)}</strong></p>
          <p>Can Access Admin: <strong>{['admin', 'spsa'].includes(verifyData.user.role?.toLowerCase()) || verifyData.user.is_admin ? 'YES' : 'NO'}</strong></p>
        </section>
      )}
    </div>
  )
}

