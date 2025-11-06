'use client'

import { useState } from 'react'

export default function AssessmentPage() {
  const [loading, setLoading] = useState(false)

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '2rem', marginBottom: '1rem', fontWeight: 'bold' }}>
        Generate Vulnerability Assessment
      </h1>
      
      <div style={{ 
        padding: '2rem', 
        backgroundColor: '#f5f5f5', 
        borderRadius: '8px',
        marginTop: '2rem'
      }}>
        <p style={{ fontSize: '1.1rem', color: '#666', marginBottom: '1rem' }}>
          This page is under development. Assessment generation functionality will be available soon.
        </p>
        
        <div style={{ 
          padding: '1rem', 
          backgroundColor: '#fff3cd', 
          border: '1px solid #ffc107',
          borderRadius: '4px',
          marginTop: '1rem'
        }}>
          <strong>Coming Soon:</strong>
          <ul style={{ marginTop: '0.5rem', paddingLeft: '1.5rem' }}>
            <li>Generate vulnerability assessments from templates</li>
            <li>Customize assessment questions</li>
            <li>Export assessment reports</li>
          </ul>
        </div>
      </div>
    </div>
  )
}

