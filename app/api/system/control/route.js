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

    // No timeout - disable timeout messaging for long-running operations
    // Requests will wait as long as needed without showing timeout errors

    console.log(`[Control Proxy] Attempting to connect to Flask at: ${FLASK_URL}`);

    try {
      const response = await fetch(`${FLASK_URL}/api/system/control`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ action }),
        cache: 'no-store',
      });
      
      console.log(`[Control Proxy] Response status: ${response.status} from ${FLASK_URL}`);

      // Handle 502/503/530 Gateway errors - tunnel/server unavailable
      if (response.status === 502 || response.status === 503 || response.status === 530) {
        console.error(`[Control Proxy] Gateway error ${response.status} from ${FLASK_URL}`);
        
        // 502/503/530 typically means tunnel is up but Flask isn't responding, OR tunnel is misconfigured
        // 530 is Cloudflare-specific: "Origin is unreachable" or "Connection timed out"
        let errorMessage = `Gateway error (${response.status}) - `;
        let hint = '';
        
        if (response.status === 530) {
          errorMessage += 'Origin server unreachable (Cloudflare timeout).';
          hint = 'Cloudflare cannot reach the Flask server. This usually means: 1) Tunnel service is down or not running (nssm status "VOFC-Tunnel"), 2) Flask service is not running (nssm status "vofc-flask"), 3) Tunnel configuration is incorrect, 4) Network connectivity issue between tunnel and Flask';
        } else if (FLASK_URL.includes('flask.frostech.site') || FLASK_URL.includes('https://')) {
          errorMessage += 'Tunnel is responding but Flask may not be accessible through it.';
          hint = 'Flask is running locally but tunnel cannot reach it. Check: 1) Tunnel service is running (nssm status "VOFC-Tunnel"), 2) Tunnel config points to localhost:8080, 3) Flask is listening on port 8080';
        } else {
          errorMessage += 'Flask server may not be running or not accessible.';
          hint = 'Check Flask service status: nssm status "vofc-flask"';
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
              checkFlask: 'nssm status "vofc-flask"',
              testLocal: 'curl http://localhost:8080/api/system/health',
              restartTunnel: 'nssm restart "VOFC-Tunnel"',
              restartFlask: 'nssm restart "vofc-flask"'
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
          hint = 'The control endpoint is not available. Flask may need to be restarted to load new routes. Run: nssm restart "vofc-flask" (as Administrator)';
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
              restartFlask: 'nssm restart "vofc-flask" (run as Administrator)',
              checkFlask: 'nssm status "vofc-flask"',
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
      // Timeout messaging disabled - handle other errors only

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

