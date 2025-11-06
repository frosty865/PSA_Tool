import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';

// Use the shared utility that handles production detection
const FLASK_URL = getFlaskUrl();

export const dynamic = 'force-dynamic';

export async function GET(request) {
  try {
    const url = new URL(request.url);
    const tail = url.searchParams.get('tail') || '50';
    
    const response = await fetch(`${FLASK_URL}/api/system/logs?tail=${tail}`, {
      cache: 'no-store',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      return NextResponse.json({
        lines: [],
        error: 'Failed to fetch logs'
      }, { status: 200 });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[Logs Proxy] Error:', error);
    return NextResponse.json({
      lines: [],
      error: error.message
    }, { status: 200 });
  }
}

