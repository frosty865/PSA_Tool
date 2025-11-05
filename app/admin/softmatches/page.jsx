'use client'

import { useEffect, useState } from 'react'
import { fetchWithAuth } from '../../lib/fetchWithAuth'
import '@/styles/cisa.css'

export default function SoftmatchesPage() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let isMounted = true
    const load = async () => {
      try {
        const res = await fetchWithAuth('/api/dashboard/softmatches', { cache: 'no-store' })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (isMounted) setRows(Array.isArray(data) ? data : [])
      } catch (e) {
        if (isMounted) setError(e.message)
      } finally {
        if (isMounted) setLoading(false)
      }
    }
    load()
    const id = setInterval(load, 30000)
    return () => { isMounted = false; clearInterval(id) }
  }, [])

  if (error) return (
    <div className="alert alert-danger">
      <p style={{ margin: 0 }}>Error loading soft matches: {error}</p>
    </div>
  )

  return (
    <div>
      <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, color: 'var(--cisa-blue)', marginBottom: 'var(--spacing-lg)' }}>Recent Soft Matches</h2>
      <div className="card" style={{ padding: 0, overflow: 'hidden', maxHeight: '75vh', overflowY: 'auto' }}>
        <table className="table">
          <thead style={{ position: 'sticky', top: 0, zIndex: 10 }}>
            <tr>
              <th style={{ textAlign: 'left' }}>Text</th>
              <th style={{ textAlign: 'right' }}>Similarity</th>
              <th style={{ textAlign: 'left' }}>Source Doc</th>
              <th style={{ textAlign: 'right' }}>Date</th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((r, i) => (
              <tr key={i}>
                <td style={{ maxWidth: '400px', color: 'var(--cisa-black)' }}>{r.new_text}</td>
                <td style={{ textAlign: 'right' }}>{r.similarity?.toFixed(3)}</td>
                <td>{r.source_doc}</td>
                <td style={{ textAlign: 'right', color: 'var(--cisa-gray)' }}>
                  {new Date(r.created_at).toLocaleString()}
                </td>
              </tr>
            )) || (
              <tr>
                <td style={{ padding: 'var(--spacing-md)' }} colSpan="4">
                  <p style={{ color: 'var(--cisa-gray)' }}>No soft match data yet.</p>
                </td>
              </tr>
            )}
            {loading && (
              <tr>
                <td style={{ padding: 'var(--spacing-md)' }} colSpan={4}>
                  <p style={{ color: 'var(--cisa-gray)' }}>Loading...</p>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
