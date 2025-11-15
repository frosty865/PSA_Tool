/**
 * Next.js API proxy route for Flask system logs
 * Proxies to Flask backend at /api/system/logs
 * 
 * Route: /api/system/logs
 * Method: GET
 * Query params: tail (optional, default: 50)
 */

import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';

const FLASK_URL = getFlaskUrl();

// Force dynamic rendering - never cache this route
export const dynamic = 'force-dynamic';
export const dynamicParams = true;
export const revalidate = 0;

// Explicitly set runtime to nodejs (required for Vercel)
export const runtime = 'nodejs';

export async function GET(request) {
  try {
    // Validate FLASK_URL is available
    if (!FLASK_URL) {
      const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19)
      return NextResponse.json({
        lines: [`${timestamp} | ERROR | [MONITOR] Flask URL not configured - check environment variables`],
        status: 'error',
        error: 'Flask URL not configured',
        message: 'Flask server URL is not available'
      }, { status: 200 });
    }

    // Get tail parameter from query string
    const { searchParams } = new URL(request.url);
    const tail = searchParams.get('tail') || '50';
    
    // Construct Flask URL - handle cases where FLASK_URL may or may not include /api
    // Remove trailing slash from FLASK_URL if present
    const baseUrl = FLASK_URL.replace(/\/$/, '');
    // Check if baseUrl already ends with /api
    const apiBase = baseUrl.endsWith('/api') ? baseUrl : `${baseUrl}/api`;
    const flaskLogsUrl = `${apiBase}/system/logs?tail=${tail}`;
    
    // Log the URL being used (for debugging - remove in production if needed)
    console.log('[Logs Proxy] FLASK_URL =', FLASK_URL);
    console.log('[Logs Proxy] Constructed URL =', flaskLogsUrl);
    
    // Add timeout to fetch request
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
    
    let response;
    try {
      response = await fetch(flaskLogsUrl, {
        cache: 'no-store',
        signal: controller.signal,
        headers: {
          'Accept': 'application/json',
        },
      });
      clearTimeout(timeoutId);
    } catch (fetchError) {
      clearTimeout(timeoutId);
      
      // BULLETPROOF: Always return valid response with heartbeat
      const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19)
      
      if (fetchError.name === 'AbortError') {
        return NextResponse.json(
          { 
            lines: [`${timestamp} | ERROR | [MONITOR] Request timeout - Flask server did not respond within 30 seconds`],
            status: 'timeout',
            error: 'Request timeout',
            message: 'Flask server did not respond within 30 seconds'
          },
          { status: 200 } // Return 200 with heartbeat so frontend doesn't break
        );
      }
      
      if (fetchError.code === 'ECONNREFUSED' || fetchError.message?.includes('ECONNREFUSED')) {
        return NextResponse.json(
          { 
            lines: [`${timestamp} | ERROR | [MONITOR] Connection refused - Flask server is not running or not accessible (URL: ${flaskLogsUrl})`],
            status: 'error',
            error: 'Connection refused',
            message: 'Flask server is not running or not accessible',
            attemptedUrl: flaskLogsUrl
          },
          { status: 200 } // Return 200 with heartbeat so frontend doesn't break
        );
      }
      
      // Other network errors - return heartbeat
      return NextResponse.json(
        { 
          lines: [`${timestamp} | ERROR | [MONITOR] Network error: ${fetchError.message || 'Unknown error'} (URL: ${flaskLogsUrl})`],
          status: 'error',
          error: fetchError.message || 'Network error',
          message: 'Failed to connect to Flask server',
          attemptedUrl: flaskLogsUrl
        },
        { status: 200 }
      );
    }

    // Forward the status code from Flask
    const status = response.status;
    
    if (!response.ok) {
      // BULLETPROOF: Always return valid response with heartbeat
      const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19)
      
      // Try to get error details from Flask
      let errorData = { lines: [], error: 'Flask server returned an error' };
      try {
        errorData = await response.json();
        // If Flask returned lines, use them; otherwise create heartbeat
        if (!errorData.lines || !Array.isArray(errorData.lines) || errorData.lines.length === 0) {
          errorData.lines = [`${timestamp} | ERROR | [MONITOR] Flask server returned status ${status}: ${errorData.error || errorData.message || 'Unknown error'} (URL: ${flaskLogsUrl})`]
        }
      } catch {
        // If JSON parsing fails, create heartbeat
        errorData.lines = [`${timestamp} | ERROR | [MONITOR] Flask server returned status ${status} - unable to parse error response (URL: ${flaskLogsUrl})`]
      }
      
      return NextResponse.json(
        { 
          lines: errorData.lines,
          status: 'error',
          error: errorData.error || `Flask server returned status ${status}`,
          message: errorData.message || 'Unable to fetch logs',
          attemptedUrl: flaskLogsUrl,
          statusCode: status
        },
        { status: 200 } // Return 200 with heartbeat so frontend doesn't break
      );
    }

    // Forward the JSON response from Flask
    // BULLETPROOF: Wrap in try-catch in case Flask returns HTML instead of JSON
    let data;
    try {
      data = await response.json();
    } catch (jsonError) {
      // Flask returned non-JSON (probably HTML error page)
      console.error('[Logs Proxy] Flask returned non-JSON response:', jsonError);
      const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19)
      return NextResponse.json({
        lines: [`${timestamp} | ERROR | [MONITOR] Flask server returned invalid response (not JSON) - status ${response.status}`],
        status: 'error',
        error: 'Invalid response format from Flask',
        message: 'Flask returned non-JSON response'
      }, { status: 200 });
    }
    
    // BULLETPROOF: Ensure we always return a valid response with lines array
    if (!data.lines || !Array.isArray(data.lines)) {
      console.warn('[Logs Proxy] Flask returned invalid data structure:', data);
      const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19)
      return NextResponse.json({
        lines: [`${timestamp} | ERROR | [MONITOR] Invalid response format from Flask - returned unexpected data structure`],
        status: 'error',
        error: 'Invalid response format from Flask',
        message: 'Flask returned unexpected data structure'
      }, { status: 200 });
    }
    
    // BULLETPROOF: If Flask returned empty lines, add heartbeat
    if (data.lines.length === 0) {
      const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19)
      data.lines = [`${timestamp} | INFO | [MONITOR] No logs available yet - waiting for log entries...`]
    }
    
    return NextResponse.json(data, { status: 200 });
    
  } catch (error) {
    // BULLETPROOF: Always return valid response, even on unexpected errors
    console.error('[Logs Proxy] Error:', error);
    const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19)
    return NextResponse.json(
      { 
        lines: [`${timestamp} | ERROR | [MONITOR] Failed to fetch logs: ${error.message || 'Unknown error'}`],
        status: 'error',
        error: error.message || 'Unknown error',
        message: 'Failed to fetch logs from Flask server'
      },
      { status: 200 } // Return 200 with heartbeat so frontend doesn't break
    );
  }
}
