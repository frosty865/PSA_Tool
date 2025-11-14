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
      response = await fetch(`${FLASK_URL}/api/system/events`, {
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
        return NextResponse.json([], { status: 200 }); // Return empty array on error
      }
      
      throw fetchError; // Re-throw other errors
    }

    if (!response.ok) {
      return NextResponse.json([], { status: 200 }); // Return empty array on error
    }

    const data = await response.json();
    return NextResponse.json(Array.isArray(data) ? data : []);
  } catch (error) {
    console.error('[System Events Proxy] Error:', error);
    return NextResponse.json([], { status: 200 }); // Return empty array on error
  }
}

