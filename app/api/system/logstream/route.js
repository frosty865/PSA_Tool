import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';

// Use the shared utility that handles production detection
const FLASK_URL = getFlaskUrl();

export const dynamic = 'force-dynamic';

export async function GET(request) {
  try {
    // For Next.js, we'll need to proxy the SSE stream
    // Since Next.js API routes don't support streaming SSE directly,
    // we'll redirect to Flask's endpoint or use a workaround
    
    // Option: Return the Flask URL for direct connection
    // Or use a polling approach instead of SSE
    
    // For now, return Flask URL - client can connect directly
    // In production with tunnel, this should work
    return NextResponse.json({
      streamUrl: `${FLASK_URL}/api/system/logstream`,
      message: 'Connect to Flask SSE endpoint directly'
    });
  } catch (error) {
    console.error('[Log Stream Proxy] Error:', error);
    return NextResponse.json(
      { error: error.message },
      { status: 500 }
    );
  }
}

