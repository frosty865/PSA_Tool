import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';

// Use the shared utility that handles production detection
const FLASK_URL = getFlaskUrl();

export const dynamic = 'force-dynamic';

export async function POST(request) {
  try {
    const body = await request.json();
    const { action } = body;

    if (!action) {
      return NextResponse.json(
        { status: 'error', message: 'Action is required' },
        { status: 400 }
      );
    }

    // Add timeout to prevent hanging requests
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 second timeout

    try {
      const response = await fetch(`${FLASK_URL}/api/system/control`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ action }),
        signal: controller.signal,
        cache: 'no-store',
      });

      clearTimeout(timeoutId);

      // Handle 502 Bad Gateway - tunnel/server unavailable
      if (response.status === 502 || response.status === 503) {
        console.error(`[Control Proxy] Gateway error ${response.status} from ${FLASK_URL}`);
        return NextResponse.json(
          { 
            status: 'error', 
            message: `Flask server unavailable (${response.status}). Check tunnel status and Flask service.`,
            flaskUrl: FLASK_URL,
            action
          },
          { status: 200 } // Return 200 so frontend can handle gracefully
        );
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ 
          message: `Control action failed with status ${response.status}` 
        }));
        return NextResponse.json(
          { 
            status: 'error', 
            message: errorData.message || `Control action failed (HTTP ${response.status})`,
            action,
            flaskUrl: FLASK_URL
          },
          { status: 200 } // Return 200 so frontend can handle gracefully
        );
      }

      const data = await response.json();
      return NextResponse.json(data);
    } catch (fetchError) {
      clearTimeout(timeoutId);
      
      // Handle timeout
      if (fetchError.name === 'AbortError') {
        console.error('[Control Proxy] Request timeout:', FLASK_URL);
        return NextResponse.json(
          { 
            status: 'error', 
            message: 'Request timeout - Flask server may be slow or unavailable. Check tunnel status.',
            flaskUrl: FLASK_URL,
            action
          },
          { status: 200 } // Return 200 so frontend can handle gracefully
        );
      }

      // Handle connection errors
      let errorMessage = fetchError.message || 'Failed to connect to Flask server';
      if (fetchError.message?.includes('ECONNREFUSED')) {
        errorMessage = 'Connection refused - Flask server may not be running or tunnel may be down';
      } else if (fetchError.message?.includes('ENOTFOUND') || fetchError.message?.includes('getaddrinfo')) {
        errorMessage = 'DNS lookup failed - check tunnel URL configuration';
      } else if (fetchError.message?.includes('certificate') || fetchError.message?.includes('SSL')) {
        errorMessage = 'SSL/TLS certificate error - check tunnel certificate';
      }

      console.error('[Control Proxy] Connection error:', {
        error: fetchError.message,
        name: fetchError.name,
        flaskUrl: FLASK_URL,
        action
      });

      return NextResponse.json(
        { 
          status: 'error', 
          message: errorMessage,
          flaskUrl: FLASK_URL,
          action
        },
        { status: 200 } // Return 200 so frontend can handle gracefully
      );
    }
  } catch (error) {
    console.error('[Control Proxy] Parse error:', error);
    return NextResponse.json(
      { 
        status: 'error', 
        message: error.message || 'Invalid request format',
        action: null
      },
      { status: 200 } // Return 200 so frontend can handle gracefully
    );
  }
}

