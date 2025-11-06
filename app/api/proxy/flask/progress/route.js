/**
 * Next.js API proxy route for Flask progress endpoint
 * Proxies to Flask backend at /api/system/progress
 */

import { NextResponse } from 'next/server';

const FLASK_URL = process.env.NEXT_PUBLIC_FLASK_URL || 
                  process.env.NEXT_PUBLIC_FLASK_API_URL || 
                  'http://localhost:8080';

export async function GET(request) {
  try {
    const response = await fetch(`${FLASK_URL}/api/system/progress`, {
      cache: 'no-store',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      // Return 200 with empty/error state instead of error status
      // This prevents frontend crashes
      return NextResponse.json(
        { 
          status: 'idle',
          message: 'No active processing',
          current_file: null,
          progress_percent: 0,
          total_files: 0,
          current_step: 0
        },
        { status: 200 }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[Progress Proxy] Error:', error);
    // Return graceful fallback instead of error
    return NextResponse.json(
      { 
        status: 'idle',
        message: 'Progress service unavailable',
        current_file: null,
        progress_percent: 0,
        total_files: 0,
        current_step: 0
      },
      { status: 200 }
    );
  }
}

