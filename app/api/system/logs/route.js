import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';

const FLASK_URL = getFlaskUrl();

export const dynamic = 'force-dynamic';

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const tail = searchParams.get('tail') || '50';
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);
    
    try {
      const response = await fetch(`${FLASK_URL}/api/system/logs?tail=${tail}`, {
        cache: 'no-store',
        signal: controller.signal,
        headers: {
          'Accept': 'application/json',
        },
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        return NextResponse.json(
          { lines: [], error: `Flask returned ${response.status}` },
          { status: 200 } // Return 200 so frontend doesn't break
        );
      }
      
      const data = await response.json();
      return NextResponse.json(data);
    } catch (fetchError) {
      clearTimeout(timeoutId);
      
      if (fetchError.name === 'AbortError') {
        return NextResponse.json(
          { lines: [], error: 'Request timeout' },
          { status: 200 }
        );
      }
      
      console.error('[Logs Proxy] Error:', fetchError);
      return NextResponse.json(
        { lines: [], error: fetchError.message || 'Failed to fetch logs' },
        { status: 200 }
      );
    }
  } catch (error) {
    console.error('[Logs Proxy] Error:', error);
    return NextResponse.json(
      { lines: [], error: error.message || 'Failed to fetch logs' },
      { status: 200 }
    );
  }
}
