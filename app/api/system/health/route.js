/**
 * Next.js API proxy route for Flask system health
 * Proxies to Flask backend at /api/system/health
 */

import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';

// Use the shared utility that handles production detection
const FLASK_URL = getFlaskUrl();

export async function GET(request) {
  // Log Flask URL for debugging (only in server logs, not exposed to client)
  console.log('[Health Proxy] Attempting to connect to Flask at:', FLASK_URL);
  console.log('[Health Proxy] Environment check:', {
    NEXT_PUBLIC_FLASK_URL: process.env.NEXT_PUBLIC_FLASK_URL || 'not set',
    NEXT_PUBLIC_FLASK_API_URL: process.env.NEXT_PUBLIC_FLASK_API_URL || 'not set',
    NODE_ENV: process.env.NODE_ENV || 'not set',
    VERCEL: process.env.VERCEL || 'not set',
    resolvedUrl: FLASK_URL
  });
  
  try {
    // Add timeout to prevent hanging
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // Increased to 10 seconds for service
    
    let response;
    try {
      const healthUrl = `${FLASK_URL}/api/system/health`;
      console.log('[Health Proxy] Fetching from:', healthUrl);
      
      response = await fetch(healthUrl, {
        cache: 'no-store',
        signal: controller.signal,
        headers: {
          'Accept': 'application/json',
        },
      });
      clearTimeout(timeoutId);
      
      console.log('[Health Proxy] Response status:', response.status, response.statusText);
    } catch (fetchError) {
      clearTimeout(timeoutId);
      
      console.error('[Health Proxy] Fetch error:', {
        name: fetchError.name,
        message: fetchError.message,
        code: fetchError.code,
        cause: fetchError.cause
      });
      
      if (fetchError.name === 'AbortError') {
        return NextResponse.json(
          { 
            status: 'timeout',
            components: {
              flask: 'offline',
              ollama: 'unknown',
              supabase: 'unknown'
            },
            error: 'Flask server did not respond within 10 seconds',
            flaskUrl: FLASK_URL,
            hint: 'Flask service may be slow to respond or unreachable at this URL'
          },
          { status: 503 }
        );
      }
      
      if (fetchError.code === 'ECONNREFUSED' || fetchError.message?.includes('ECONNREFUSED')) {
        return NextResponse.json(
          { 
            status: 'error',
            components: {
              flask: 'offline',
              ollama: 'unknown',
              supabase: 'unknown'
            },
            error: 'Connection refused - Flask service may not be accessible at this URL',
            flaskUrl: FLASK_URL,
            hint: `Check that Flask service is running and accessible at ${FLASK_URL}. Verify NEXT_PUBLIC_FLASK_URL environment variable.`
          },
          { status: 503 }
        );
      }
      
      // Handle other network errors
      if (fetchError.message?.includes('fetch failed') || fetchError.message?.includes('network')) {
        return NextResponse.json(
          { 
            status: 'error',
            components: {
              flask: 'offline',
              ollama: 'unknown',
              supabase: 'unknown'
            },
            error: 'Network error connecting to Flask service',
            flaskUrl: FLASK_URL,
            message: fetchError.message,
            hint: 'Check network connectivity and Flask service URL configuration'
          },
          { status: 503 }
        );
      }
      
      throw fetchError;
    }

    if (!response.ok) {
      return NextResponse.json(
        { 
          status: 'error',
          components: {
            flask: 'offline',
            ollama: 'unknown',
            supabase: 'unknown'
          },
          error: 'Flask server returned an error',
          statusCode: response.status,
          flaskUrl: FLASK_URL
        },
        { status: 503 }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[Health Proxy] Error:', error);
    return NextResponse.json(
      { 
        status: 'error',
        components: {
          flask: 'offline',
          ollama: 'unknown',
          supabase: 'unknown'
        },
        error: 'Failed to connect to Flask server',
        message: error.message,
        flaskUrl: FLASK_URL
      },
      { status: 503 }
    );
  }
}

