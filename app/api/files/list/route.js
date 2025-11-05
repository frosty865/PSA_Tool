/**
 * Next.js API proxy route for Flask file listing
 * Proxies to Flask backend at /api/files/list
 */

import { NextResponse } from 'next/server';

const FLASK_URL = process.env.NEXT_PUBLIC_FLASK_URL || 
                  process.env.NEXT_PUBLIC_FLASK_API_URL || 
                  'http://localhost:8080';

export async function GET(request) {
  try {
    const response = await fetch(`${FLASK_URL}/api/files/list`, {
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
    console.error('[Files List Proxy] Error:', error);
    return NextResponse.json(
      { 
        error: 'Failed to connect to Flask server',
        message: error.message 
      },
      { status: 503 }
    );
  }
}

