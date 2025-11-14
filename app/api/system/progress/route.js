import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';

// Use the shared utility that handles production detection
const FLASK_URL = getFlaskUrl();

export const dynamic = 'force-dynamic'; // Ensure this API route is always dynamic

export async function GET(request) {
  try {
    const response = await fetch(`${FLASK_URL}/api/system/progress`, {
      cache: 'no-store',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      // Return default values instead of error
      // Note: This might indicate Flask is offline or unreachable
      return NextResponse.json({
        status: 'unknown',
        message: 'Flask API unavailable - cannot read progress',
        timestamp: new Date().toISOString(),
        incoming: 0,
        processed: 0,
        library: 0,
        errors: 0,
        review: 0,
        watcher_status: 'unknown'
      }, { status: 200 });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[Progress Proxy] Error:', error);
    // Return default values on error
    // Check if it's a connection error
    const errorMessage = error.message?.includes('ECONNREFUSED') || error.message?.includes('fetch failed')
      ? 'Cannot connect to Flask server - check if service is running'
      : error.message || 'Unknown error';
    
    return NextResponse.json({
      status: 'error',
      message: errorMessage,
      timestamp: new Date().toISOString(),
      incoming: 0,
      processed: 0,
      library: 0,
      errors: 0,
      review: 0,
      watcher_status: 'unknown'
    }, { status: 200 });
  }
}

