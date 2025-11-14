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
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout (increased for slow networks)
    
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
            message: 'Flask server did not respond within 30 seconds',
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
      
      // 502 Bad Gateway from tunnel is temporary - return 200 with error status instead of 502
      // This prevents frontend from thinking the service is permanently down
      if (status === 502) {
        console.warn('[System Dashboard Proxy] Tunnel returned 502 - likely temporary tunnel issue');
        return NextResponse.json(
          {
            ...errorData,
            status: 'error',
            components: {
              flask: 'unknown', // Don't mark as offline for 502
              ollama: 'unknown',
              supabase: 'unknown',
              tunnel: 'unknown'
            },
            hint: 'This is usually a temporary tunnel connectivity issue. The service may still be running.'
          },
          { status: 200 } // Return 200 so frontend doesn't treat as permanent failure
        );
      }
      
      return NextResponse.json(errorData, { status: status });
    }

    const data = await response.json();
    
    // Transform Flask response to match frontend expectations
    // Flask returns: { flask: "ok", ollama: "ok", supabase: "ok", ... }
    // Frontend expects: { components: { flask: "...", ollama: "...", supabase: "..." }, ... }
    const transformedData = {
      ...data,
      components: {
        flask: data.flask || data.components?.flask || 'unknown',
        ollama: data.ollama || data.components?.ollama || 'unknown',
        supabase: data.supabase || data.components?.supabase || 'unknown',
        tunnel: data.tunnel || data.components?.tunnel || 'unknown'
      }
    };
    
    return NextResponse.json(transformedData);
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

