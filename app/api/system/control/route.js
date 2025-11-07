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

    console.log(`[Control Proxy] Attempting to connect to Flask at: ${FLASK_URL}`);

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
      
      console.log(`[Control Proxy] Response status: ${response.status} from ${FLASK_URL}`);

      // Handle 502 Bad Gateway - tunnel/server unavailable
      if (response.status === 502 || response.status === 503) {
        console.error(`[Control Proxy] Gateway error ${response.status} from ${FLASK_URL}`);
        
        // 502/503 typically means tunnel is up but Flask isn't responding, OR tunnel is misconfigured
        let errorMessage = `Gateway error (${response.status}) - `;
        let hint = '';
        
        if (FLASK_URL.includes('flask.frostech.site') || FLASK_URL.includes('https://')) {
          errorMessage += 'Tunnel is responding but Flask may not be accessible through it.';
          hint = 'Flask is running locally but tunnel cannot reach it. Check: 1) Tunnel service is running (nssm status "VOFC-Tunnel"), 2) Tunnel config points to localhost:8080, 3) Flask is listening on port 8080';
        } else {
          errorMessage += 'Flask server may not be running or not accessible.';
          hint = 'Check Flask service status: nssm status "VOFC-Flask"';
        }
        
        return NextResponse.json(
          { 
            status: 'error', 
            message: errorMessage,
            flaskUrl: FLASK_URL,
            action,
            hint,
            troubleshooting: {
              checkTunnel: 'nssm status "VOFC-Tunnel"',
              checkFlask: 'nssm status "VOFC-Flask"',
              testLocal: 'curl http://localhost:8080/api/system/health',
              restartTunnel: 'nssm restart "VOFC-Tunnel"',
              restartFlask: 'nssm restart "VOFC-Flask"'
            }
          },
          { status: 200 } // Return 200 so frontend can handle gracefully
        );
      }

      // Handle non-OK responses
      if (!response.ok) {
        let errorMessage = `Control action failed (HTTP ${response.status})`;
        let hint = '';
        
        try {
          const errorData = await response.json();
          errorMessage = errorData.message || errorData.error || errorMessage;
        } catch {
          // If JSON parsing fails, try text
          try {
            const errorText = await response.text();
            if (errorText) errorMessage = errorText;
          } catch {
            // Use default message
          }
        }
        
        // Special handling for 404 - route doesn't exist
        if (response.status === 404) {
          errorMessage = `Route not found: /api/system/control`;
          hint = 'The control endpoint is not available. Flask may need to be restarted to load new routes. Run: nssm restart "VOFC-Flask" (as Administrator)';
        }
        
        console.error(`[Control Proxy] Flask returned ${response.status}: ${errorMessage}`);
        return NextResponse.json(
          {
            status: 'error',
            message: errorMessage,
            hint,
            flaskUrl: FLASK_URL,
            action,
            troubleshooting: response.status === 404 ? {
              restartFlask: 'nssm restart "VOFC-Flask" (run as Administrator)',
              checkFlask: 'nssm status "VOFC-Flask"',
              testLocal: 'curl http://localhost:8080/api/system/control -X POST -H "Content-Type: application/json" -d \'{"action":"start_watcher"}\''
            } : undefined
          },
          { status: 200 } // Return 200 so frontend can handle gracefully
        );
      }

      // Parse successful response
      let data;
      try {
        data = await response.json();
      } catch (parseError) {
        console.error('[Control Proxy] Failed to parse Flask response:', parseError);
        return NextResponse.json(
          {
            status: 'error',
            message: 'Invalid response format from Flask server',
            flaskUrl: FLASK_URL,
            action
          },
          { status: 200 }
        );
      }

      // Ensure response has expected format
      if (!data.status) {
        data.status = 'ok';
      }
      if (!data.message && data.status === 'ok') {
        data.message = 'Action completed successfully';
      }

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

