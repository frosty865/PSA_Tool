import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';

const FLASK_URL = getFlaskUrl();

export const dynamic = 'force-dynamic';

export async function GET(request) {
  try {
    // Add timeout to fetch request
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
    
    let response;
    try {
      response = await fetch(`${FLASK_URL}/api/system/tunnel/logs`, {
        cache: 'no-store',
        signal: controller.signal,
        headers: {
          'Accept': 'application/json',
        },
      });
      clearTimeout(timeoutId);
    } catch (fetchError) {
      clearTimeout(timeoutId);
      
      // Handle timeout or connection errors
      if (fetchError.name === 'AbortError' || fetchError.code === 'ECONNREFUSED' || fetchError.message?.includes('ECONNREFUSED')) {
        return NextResponse.json({
          file: null,
          lines: [],
          count: 0,
          error: fetchError.name === 'AbortError' ? 'Request timeout' : 'Connection refused'
        }, { status: 200 }); // Return 200 with empty data
      }
      
      throw fetchError; // Re-throw other errors
    }

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

