import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';

const FLASK_URL = getFlaskUrl();

export const dynamic = 'force-dynamic';

export async function GET(request) {
  try {
    const response = await fetch(`${FLASK_URL}/api/system/tunnel/logs`, {
      cache: 'no-store',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      return NextResponse.json({
        file: null,
        lines: [],
        count: 0,
        error: 'Failed to fetch tunnel logs'
      }, { status: 200 }); // Return 200 with empty data
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[Tunnel Logs Proxy] Error:', error);
    return NextResponse.json({
      file: null,
      lines: [],
      count: 0,
      error: error.message
    }, { status: 200 }); // Return 200 to prevent frontend errors
  }
}

