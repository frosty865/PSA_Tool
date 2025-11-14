/**
 * Next.js API proxy route for Flask system logs
 * Proxies to Flask backend at /api/system/logs
 */

import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';

const FLASK_URL = getFlaskUrl();

export const dynamic = 'force-dynamic'; // Ensure this API route is always dynamic
export const runtime = 'nodejs'; // Explicitly set runtime

export async function GET(request) {
  try {
    // Get tail parameter from query string
    const { searchParams } = new URL(request.url);
    const tail = searchParams.get('tail') || '50';
    
    // Add timeout to fetch request
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
    
    let response;
    try {
      response = await fetch(`${FLASK_URL}/api/system/logs?tail=${tail}`, {
        cache: 'no-store',
        signal: controller.signal,
        headers: {
          'Accept': 'application/json',
        },
      });
      clearTimeout(timeoutId);
    } catch (fetchError) {
      clearTimeout(timeoutId);
      
      // Handle specific connection errors
      if (fetchError.name === 'AbortError') {
        return NextResponse.json(
          { 
            lines: [],
            error: 'Request timeout',
            message: 'Flask server did not respond within 30 seconds'
          },
          { status: 200 } // Return 200 with empty lines so frontend doesn't break
        );
      }
      
      if (fetchError.code === 'ECONNREFUSED' || fetchError.message?.includes('ECONNREFUSED')) {
        return NextResponse.json(
          { 
            lines: [],
            error: 'Connection refused',
            message: 'Flask server is not running or not accessible'
          },
          { status: 200 } // Return 200 with empty lines so frontend doesn't break
        );
      }
      
      throw fetchError; // Re-throw other errors
    }

    // Forward the status code from Flask
    const status = response.status;
    
    if (!response.ok) {
      // Try to get error details from Flask
      let errorData = { lines: [], error: 'Flask server returned an error' };
      try {
        errorData = await response.json();
      } catch {
        // If JSON parsing fails, use default error
      }
      
      return NextResponse.json(
        { 
          lines: [],
          error: errorData.error || `Flask server returned status ${status}`,
          message: errorData.message || 'Unable to fetch logs'
        },
        { status: 200 } // Return 200 with empty lines so frontend doesn't break
      );
    }

    // Forward the JSON response from Flask
    const data = await response.json();
    return NextResponse.json(data, { status: 200 });
    
  } catch (error) {
    console.error('[Logs Proxy] Error:', error);
    return NextResponse.json(
      { 
        lines: [],
        error: error.message || 'Unknown error',
        message: 'Failed to fetch logs from Flask server'
      },
      { status: 200 } // Return 200 with empty lines so frontend doesn't break
    );
  }
}
