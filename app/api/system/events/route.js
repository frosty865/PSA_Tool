import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';

const FLASK_URL = getFlaskUrl();

export const dynamic = 'force-dynamic';

export async function GET(request) {
  try {
    const response = await fetch(`${FLASK_URL}/api/system/events`, {
      cache: 'no-store',
      headers: {
        'Accept': 'application/json',
      },
    });

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

