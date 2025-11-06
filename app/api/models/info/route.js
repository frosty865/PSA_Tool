import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';

const FLASK_URL = getFlaskUrl();

export const dynamic = 'force-dynamic';

export async function GET(request) {
  try {
    const response = await fetch(`${FLASK_URL}/api/models/info`, {
      cache: 'no-store',
      headers: {
        'Accept': 'application/json',
      },
    });

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

