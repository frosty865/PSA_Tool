/**
 * Next.js API proxy route for Flask system health
 * Proxies to Flask backend at /api/system/health
 */

import { NextResponse } from 'next/server';

const FLASK_URL = process.env.NEXT_PUBLIC_FLASK_URL || 
                  process.env.NEXT_PUBLIC_FLASK_API_URL || 
                  'http://localhost:8080';

export async function GET(request) {
  try {
    // Add timeout to prevent hanging
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout
    
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
      
      if (fetchError.name === 'AbortError') {
        return NextResponse.json(
          { 
            status: 'timeout',
            components: {
              flask: 'offline',
              ollama: 'unknown',
              supabase: 'unknown'
            },
            error: 'Flask server did not respond within 5 seconds',
            flaskUrl: FLASK_URL
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
            error: 'Flask server is not running or not accessible',
            flaskUrl: FLASK_URL,
            hint: 'Make sure the Flask server is running on the configured port'
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

