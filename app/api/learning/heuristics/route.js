/**
 * Next.js API proxy route for Flask learning heuristics
 * Proxies to Flask backend at /api/learning/heuristics
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
      response = await fetch(`${FLASK_URL}/api/learning/heuristics`, {
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
            heuristics: null
          },
          { status: 200 } // Return 200 with null heuristics to prevent UI crash
        );
      }
      
      if (fetchError.code === 'ECONNREFUSED' || fetchError.message?.includes('ECONNREFUSED')) {
        return NextResponse.json(
          { 
            error: 'Connection refused',
            message: 'Flask server is not running or not accessible',
            flaskUrl: FLASK_URL,
            heuristics: null
          },
          { status: 200 } // Return 200 with null heuristics to prevent UI crash
        );
      }
      
      throw fetchError; // Re-throw other errors
    }

    if (!response.ok) {
      // Try to get error details from Flask
      let errorData = { error: 'Flask server returned an error', status: response.status, heuristics: null };
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
      
      // Return 200 with null heuristics instead of error to prevent UI crash
      return NextResponse.json(
        { 
          ...errorData,
          heuristics: null
        },
        { status: 200 }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[Learning Heuristics Proxy] Error:', error);
    console.error('[Learning Heuristics Proxy] Flask URL:', FLASK_URL);
    
    // Return null heuristics instead of error to prevent UI crash
    return NextResponse.json(
      { 
        error: 'Unable to fetch heuristics',
        message: error.message,
        flaskUrl: FLASK_URL,
        heuristics: null
      },
      { status: 200 }
    );
  }
}

