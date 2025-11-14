/**
 * Next.js API proxy route for Flask process-pending endpoint
 * Proxies to Flask backend at /api/process/start or similar
 */

import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';

const FLASK_URL = getFlaskUrl();

export const dynamic = 'force-dynamic';

export async function POST(request) {
  try {
    // Add timeout to fetch request
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout for processing
    
    let response;
    try {
      // Try Flask process endpoint
      response = await fetch(`${FLASK_URL}/api/process/start`, {
        method: 'POST',
        cache: 'no-store',
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ action: 'process_pending' }),
      });
      clearTimeout(timeoutId);
    } catch (fetchError) {
      clearTimeout(timeoutId);
      
      // Handle specific connection errors
      if (fetchError.name === 'AbortError') {
        return NextResponse.json(
          { 
            success: false,
            error: 'Request timeout',
            message: 'Flask server did not respond within 60 seconds',
            hint: 'Processing may be taking longer than expected. Check Flask service status.'
          },
          { status: 200 } // Return 200 so frontend can handle gracefully
        );
      }
      
      if (fetchError.code === 'ECONNREFUSED' || fetchError.message?.includes('ECONNREFUSED')) {
        return NextResponse.json(
          { 
            success: false,
            error: 'Connection refused',
            message: 'Flask server is not running or not accessible',
            hint: 'Check that Flask service is running and tunnel is configured correctly'
          },
          { status: 200 } // Return 200 so frontend can handle gracefully
        );
      }
      
      throw fetchError; // Re-throw other errors
    }

    if (!response.ok) {
      // Try to get error details from Flask
      let errorData = { success: false, error: 'Flask server returned an error' };
      try {
        errorData = await response.json();
      } catch {
        // If JSON parsing fails, use default error
      }
      
      return NextResponse.json(
        { 
          success: false,
          ...errorData,
          hint: errorData.hint || 'Check Flask service logs for details'
        },
        { status: 200 } // Return 200 so frontend can handle gracefully
      );
    }

    const data = await response.json();
    return NextResponse.json({
      success: true,
      ...data
    }, { status: 200 });
    
  } catch (error) {
    console.error('[Process Pending Proxy] Error:', error);
    return NextResponse.json(
      { 
        success: false,
        error: error.message || 'Unknown error',
        message: 'Failed to process pending files',
        hint: 'Check Flask service status and network connectivity'
      },
      { status: 200 } // Return 200 so frontend can handle gracefully
    );
  }
}

