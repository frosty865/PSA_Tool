/**
 * Next.js API proxy route for Flask retraining events
 * Proxies to Flask backend at /api/learning/retrain-events
 */

import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';

const FLASK_URL = getFlaskUrl();

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get('limit') || '10';
    
    const response = await fetch(`${FLASK_URL}/api/learning/retrain-events?limit=${limit}`, {
      cache: 'no-store',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { 
          error: errorData.error || 'Flask server error',
          message: errorData.message || 'Failed to fetch retraining events',
          status: response.status,
          events: []
        },
        { status: 200 } // Return 200 with empty events to prevent UI crash
      );
    }

    const data = await response.json();
    // Flask returns { status: "ok", events: [...], count: N }
    return NextResponse.json(data.events || []); // Return just the array of events
  } catch (error) {
    console.error('[Retrain Events Proxy] Error:', error);
    return NextResponse.json(
      { 
        error: 'Failed to connect to Flask server',
        message: error.message,
        events: []
      },
      { status: 200 } // Return 200 with empty events to prevent UI crash
    );
  }
}

