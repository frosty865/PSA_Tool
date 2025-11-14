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
      response = await fetch(`${FLASK_URL}/api/models/info`, {
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
          name: 'unknown',
          version: 'unknown',
          size_gb: null,
          status: 'error',
          error: fetchError.name === 'AbortError' ? 'Request timeout' : 'Connection refused'
        }, { status: 200 });
      }
      
      throw fetchError; // Re-throw other errors
    }

    if (!response.ok) {
      return NextResponse.json({
        name: 'unknown',
        version: 'unknown',
        size_gb: null,
        status: 'error'
      }, { status: 200 }); // Return 200 with default values
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[Model Info Proxy] Error:', error);
    return NextResponse.json({
      name: 'unknown',
      version: 'unknown',
      size_gb: null,
      status: 'error',
      error: error.message
    }, { status: 200 });
  }
}

