/**
 * Next.js API route for dashboard SSE stream
 * Returns Flask SSE endpoint URL for direct connection
 * Note: Next.js doesn't support SSE streaming directly, so we return the Flask URL
 */

import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';

const FLASK_URL = getFlaskUrl();

export const dynamic = 'force-dynamic';

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const mode = searchParams.get('mode') || 'live';

    // Return Flask SSE endpoint URL for direct connection
    // Client should connect directly to Flask for SSE streaming
    return NextResponse.json({
      streamUrl: `${FLASK_URL}/api/system/logstream?mode=${mode}`,
      message: 'Connect to Flask SSE endpoint directly',
      flaskUrl: FLASK_URL
    });

  } catch (error) {
    console.error('[Dashboard Stream] Error:', error);
    return NextResponse.json(
      {
        error: error.message || 'Unknown error',
        message: 'Failed to get stream URL'
      },
      { status: 500 }
    );
  }
}

