import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';

// Use the shared utility that handles production detection
const FLASK_URL = getFlaskUrl();

export const dynamic = 'force-dynamic'; // Ensure this API route is always dynamic

export async function GET(request) {
  try {
    // Add timeout to fetch request
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
    
    let response;
    try {
      response = await fetch(`${FLASK_URL}/api/system/progress`, {
        cache: 'no-store',
        signal: controller.signal,
        headers: {
          'Accept': 'application/json',
        },
      });
      clearTimeout(timeoutId);
    } catch (fetchError) {
      clearTimeout(timeoutId);
      
      // Handle timeout - return 503 instead of default progress
      if (fetchError.name === 'AbortError') {
        return NextResponse.json({
          status: 'timeout',
          message: 'Flask server did not respond within 30 seconds',
          error: 'Service Timeout',
          timestamp: new Date().toISOString()
        }, { status: 503 });
      }
      
      // Handle connection refused - return 503 instead of default progress
      if (fetchError.code === 'ECONNREFUSED' || fetchError.message?.includes('ECONNREFUSED')) {
        return NextResponse.json({
          status: 'error',
          message: 'Cannot connect to Flask server - check if service is running',
          error: 'Connection Refused',
          timestamp: new Date().toISOString()
        }, { status: 503 });
      }
      
      throw fetchError; // Re-throw other errors
    }

    if (!response.ok) {
      // Return 503 instead of default progress - let frontend handle error state
      return NextResponse.json({
        status: 'error',
        message: 'Flask API unavailable - cannot read progress',
        error: `HTTP ${response.status}`,
        timestamp: new Date().toISOString()
      }, { status: 503 });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[Progress Proxy] Error:', error);
    // Return 503 instead of default progress - let frontend handle error state
    const errorMessage = error.message?.includes('ECONNREFUSED') || error.message?.includes('fetch failed')
      ? 'Cannot connect to Flask server - check if service is running'
      : error.message || 'Unknown error';
    
    return NextResponse.json({
      status: 'error',
      message: errorMessage,
      error: 'Unexpected Error',
      timestamp: new Date().toISOString()
    }, { status: 503 });
  }
}

