/**
 * Next.js API proxy route for Flask system dashboard
 * Proxies to Flask backend at /api/system/health
 */

import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';

const FLASK_URL = getFlaskUrl();

export async function GET(request) {
  try {
    // Add timeout to fetch request
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
    
    let response;
    try {
      response = await fetch(`${FLASK_URL}/api/system/health`, {
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
    console.error('[System Dashboard Proxy] Error:', error);
    console.error('[System Dashboard Proxy] Flask URL:', FLASK_URL);
    return NextResponse.json(
      { 
        error: 'Unable to fetch system status',
        message: error.message,
        flaskUrl: FLASK_URL,
        type: error.name || 'UnknownError'
      },
      { status: 500 }
    );
  }
}

