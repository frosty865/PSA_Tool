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
              supabase: 'unknown',
              tunnel: 'unknown',
              model_manager: 'unknown'
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
              supabase: 'unknown',
              tunnel: 'unknown',
              model_manager: 'unknown'
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
              supabase: 'unknown',
              tunnel: 'unknown',
              model_manager: 'unknown'
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
      // 502 Bad Gateway from tunnel is temporary - return 200 with error status instead of 503
      // This prevents frontend from thinking the service is permanently down
      if (response.status === 502) {
        console.warn('[Health Proxy] Tunnel returned 502 - likely temporary tunnel issue');
        return NextResponse.json(
          { 
            status: 'error',
            components: {
              flask: 'unknown', // Don't mark as offline for 502
              ollama: 'unknown',
              supabase: 'unknown',
              tunnel: 'unknown'
            },
            error: 'Tunnel temporarily unavailable (502)',
            statusCode: response.status,
            flaskUrl: FLASK_URL,
            hint: 'This is usually a temporary tunnel connectivity issue. The service may still be running.'
          },
          { status: 200 } // Return 200 so frontend doesn't treat as permanent failure
        );
      }
      
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
    
    // Transform Flask response to match frontend expectations
    // Flask returns: { flask: "ok", ollama: "ok", supabase: "ok", model_manager: "ok", ... }
    // Frontend expects: { components: { flask: "...", ollama: "...", supabase: "...", model_manager: "..." }, ... }
    const transformedData = {
      ...data,
      components: {
        flask: data.flask || data.components?.flask || 'unknown',
        ollama: data.ollama || data.components?.ollama || 'unknown',
        supabase: data.supabase || data.components?.supabase || 'unknown',
        tunnel: data.tunnel || data.components?.tunnel || 'unknown',
        model_manager: data.model_manager || data.components?.model_manager || 'unknown'
      }
    };
    
    return NextResponse.json(transformedData);
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

