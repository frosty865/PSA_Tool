/**
 * Next.js API proxy route for Flask learning stats
 * Proxies to Flask backend at /api/learning/stats
 */

import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';

const FLASK_URL = getFlaskUrl();

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get('limit') || '50';
    
    // Add timeout to fetch request
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
    
    let response;
    try {
      response = await fetch(`${FLASK_URL}/api/learning/stats?limit=${limit}`, {
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
            flaskUrl: FLASK_URL,
            stats: []
          },
          { status: 200 } // Return 200 with empty stats to prevent UI crash
        );
      }
      
      if (fetchError.code === 'ECONNREFUSED' || fetchError.message?.includes('ECONNREFUSED')) {
        return NextResponse.json(
          { 
            error: 'Connection refused',
            message: 'Flask server is not running or not accessible',
            flaskUrl: FLASK_URL,
            stats: []
          },
          { status: 200 } // Return 200 with empty stats to prevent UI crash
        );
      }
      
      throw fetchError; // Re-throw other errors
    }

    if (!response.ok) {
      // Try to get error details from Flask
      let errorData = { error: 'Flask server returned an error', status: response.status, stats: [] };
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
      
      // Return 200 with empty stats instead of error to prevent UI crash
      return NextResponse.json(
        { 
          ...errorData,
          stats: []
        },
        { status: 200 }
      );
    }

    const data = await response.json();
    
    // Transform Flask response to match frontend expectations
    // Flask returns: { status: "ok", stats: [...], count: N }
    // Frontend expects: array of stats or { stats: [...] }
    const stats = data.stats || data || [];
    
    return NextResponse.json(stats);
  } catch (error) {
    console.error('[Learning Stats Proxy] Error:', error);
    console.error('[Learning Stats Proxy] Flask URL:', FLASK_URL);
    
    // Return empty stats instead of error to prevent UI crash
    return NextResponse.json(
      { 
        error: 'Unable to fetch learning stats',
        message: error.message,
        flaskUrl: FLASK_URL,
        stats: []
      },
      { status: 200 }
    );
  }
}

