/**
 * Next.js API proxy route for Flask library search
 * Proxies to Flask backend at /api/library/search
 */

import { NextResponse } from 'next/server';

const FLASK_URL = process.env.NEXT_PUBLIC_FLASK_URL || 
                  process.env.NEXT_PUBLIC_FLASK_API_URL || 
                  'http://localhost:8080';

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const query = searchParams.get('query') || '';
    
    const response = await fetch(`${FLASK_URL}/api/library/search?query=${encodeURIComponent(query)}`, {
      cache: 'no-store',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      return NextResponse.json(
        { 
          error: 'Flask server not responding',
          status: response.status 
        },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[Library Search Proxy] Error:', error);
    return NextResponse.json(
      { 
        error: 'Failed to connect to Flask server',
        message: error.message 
      },
      { status: 503 }
    );
  }
}

export async function POST(request) {
  try {
    const body = await request.json();
    
    const response = await fetch(`${FLASK_URL}/api/library/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
      cache: 'no-store',
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { 
          error: errorData.error || 'Flask server error',
          status: response.status 
        },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[Library Search Proxy] Error:', error);
    return NextResponse.json(
      { 
        error: 'Failed to connect to Flask server',
        message: error.message 
      },
      { status: 503 }
    );
  }
}

