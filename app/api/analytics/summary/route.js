/**
 * Next.js API proxy route for Flask analytics summary
 * Proxies to Flask backend at /api/analytics/summary
 */

import { NextResponse } from 'next/server';

const FLASK_URL = process.env.NEXT_PUBLIC_FLASK_URL || 
                  process.env.NEXT_PUBLIC_FLASK_API_URL || 
                  'http://localhost:8080';

export async function GET(request) {
  try {
    // Add timeout to fetch request
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
    
    let response;
    try {
      response = await fetch(`${FLASK_URL}/api/analytics/summary`, {
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
            error: 'Request timeout',
            message: 'Flask server did not respond within 10 seconds',
            flaskUrl: FLASK_URL
          },
          { status: 504 }
        );
      }
      
      if (fetchError.code === 'ECONNREFUSED' || fetchError.message?.includes('ECONNREFUSED')) {
        return NextResponse.json(
          { 
            error: 'Connection refused',
            message: 'Flask server is not running or not accessible',
            flaskUrl: FLASK_URL,
            hint: 'Make sure the Flask server is running on the configured port'
          },
          { status: 503 }
        );
      }
      
      throw fetchError; // Re-throw other errors
    }

    // Forward the status code from Flask
    const status = response.status;
    
    if (!response.ok) {
      // If Flask returns 202 (pending), forward it
      if (status === 202) {
        const data = await response.json().catch(() => ({ status: 'pending', message: 'Analytics not ready' }));
        return NextResponse.json(data, { status: 202 });
      }
      
      // Try to get error details from Flask
      let errorData = { error: 'Flask server returned an error', status: status };
      try {
        const text = await response.text();
        if (text) {
          try {
            errorData = { ...errorData, ...JSON.parse(text) };
          } catch {
            errorData.details = text;
          }
        }
      } catch {
        // Ignore parsing errors
      }
      
      return NextResponse.json(errorData, { status: status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[Analytics Proxy] Error:', error);
    console.error('[Analytics Proxy] Flask URL:', FLASK_URL);
    return NextResponse.json(
      { 
        error: 'Unable to fetch analytics',
        message: error.message,
        flaskUrl: FLASK_URL,
        type: error.name || 'UnknownError'
      },
      { status: 500 }
    );
  }
}

