/**
 * Next.js API proxy route for Flask analytics summary
 * Proxies to Flask backend at /api/analytics/summary
 */

import { NextResponse } from 'next/server';

const FLASK_URL = process.env.NEXT_PUBLIC_FLASK_URL || 
                  process.env.NEXT_PUBLIC_FLASK_API_URL || 
                  'http://localhost:8080';

export async function GET(request) {
  try {
    const response = await fetch(`${FLASK_URL}/api/analytics/summary`, {
      cache: 'no-store',
      headers: {
        'Accept': 'application/json',
      },
    });

    // Forward the status code from Flask
    const status = response.status;
    
    if (!response.ok) {
      // If Flask returns 202 (pending), forward it
      if (status === 202) {
        const data = await response.json().catch(() => ({ status: 'pending', message: 'Analytics not ready' }));
        return NextResponse.json(data, { status: 202 });
      }
      
      return NextResponse.json(
        { 
          error: 'Flask server returned an error',
          status: status 
        },
        { status: status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[Analytics Proxy] Error:', error);
    return NextResponse.json(
      { 
        error: 'Unable to fetch analytics',
        message: error.message 
      },
      { status: 500 }
    );
  }
}

