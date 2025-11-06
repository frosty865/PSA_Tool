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
      return NextResponse.json({
        status: 'unknown',
        message: 'Progress file not available',
        timestamp: new Date().toISOString(),
        incoming: 0,
        processed: 0,
        library: 0,
        errors: 0,
        review: 0
      }, { status: 200 });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[Progress Proxy] Error:', error);
    // Return default values on error
    return NextResponse.json({
      status: 'error',
      message: error.message,
      timestamp: new Date().toISOString(),
      incoming: 0,
      processed: 0,
      library: 0,
      errors: 0,
      review: 0
    }, { status: 200 });
  }
}

