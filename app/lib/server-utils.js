/**
 * Shared utilities for server URL detection and error handling
 * Ensures all three servers (Flask, Ollama, Next.js) are handled consistently
 */

/**
 * Get Flask server URL with fallback chain
 * Priority: Explicit env vars > localhost (dev) > remote URL (prod)
 */
export function getFlaskUrl() {
  // Check explicit environment variables first
  if (process.env.NEXT_PUBLIC_FLASK_API_URL) {
    return process.env.NEXT_PUBLIC_FLASK_API_URL;
  }
  if (process.env.NEXT_PUBLIC_FLASK_URL) {
    return process.env.NEXT_PUBLIC_FLASK_URL;
  }
  if (process.env.FLASK_URL) {
    return process.env.FLASK_URL;
  }
  if (process.env.NEXT_PUBLIC_OLLAMA_SERVER_URL) {
    return process.env.NEXT_PUBLIC_OLLAMA_SERVER_URL;
  }
  if (process.env.OLLAMA_SERVER_URL) {
    return process.env.OLLAMA_SERVER_URL;
  }
  if (process.env.OLLAMA_LOCAL_URL) {
    return process.env.OLLAMA_LOCAL_URL;
  }
  
  // Determine if we're in production
  // Vercel sets VERCEL=1, and NODE_ENV=production in production
  const isProduction = 
    process.env.VERCEL === '1' || 
    process.env.VERCEL === 'true' ||
    process.env.NODE_ENV === 'production';
  
  // Use tunnel URL in production, localhost in development
  const defaultUrl = isProduction 
    ? 'https://flask.frostech.site' 
    : 'http://localhost:8080';
  
  // Log for debugging (only in server-side)
  if (typeof console !== 'undefined') {
    console.log('[getFlaskUrl] Detected:', {
      isProduction,
      VERCEL: process.env.VERCEL,
      NODE_ENV: process.env.NODE_ENV,
      defaultUrl,
      using: defaultUrl
    });
  }
  
  return defaultUrl;
}

/**
 * Get Ollama server URL with fallback chain
 */
export function getOllamaUrl() {
  return (
    process.env.NEXT_PUBLIC_OLLAMA_URL ||
    process.env.OLLAMA_URL ||
    process.env.OLLAMA_API_BASE_URL ||
    process.env.OLLAMA_BASE_URL ||
    (process.env.NODE_ENV === 'development' || !process.env.VERCEL
      ? 'http://localhost:11434'
      : 'https://ollama.frostech.site')
  );
}

/**
 * Safe fetch with timeout and error handling
 * Returns a consistent error response format
 */
export async function safeFetch(url, options = {}) {
  const {
    timeout = 10000,
    method = 'GET',
    headers = {},
    body = null,
    ...restOptions
  } = options;

  // Log request for debugging
  if (typeof console !== 'undefined') {
    console.log(`[safeFetch] ${method} ${url}`, {
      timeout,
      hasBody: !!body,
    });
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      method,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        ...headers,
      },
      body: body ? JSON.stringify(body) : null,
      signal: controller.signal,
      cache: 'no-store',
      ...restOptions,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}`;
      let errorDetails = null;
      
      try {
        const errorText = await response.text();
        try {
          errorDetails = JSON.parse(errorText);
          errorMessage = errorDetails.message || errorDetails.error || errorMessage;
        } catch {
          errorMessage = errorText.substring(0, 200) || response.statusText || errorMessage;
        }
      } catch {
        errorMessage = response.statusText || errorMessage;
      }

      // Log error for debugging
      if (typeof console !== 'undefined') {
        console.error(`[safeFetch] Error ${response.status} from ${url}:`, {
          errorMessage,
          errorDetails,
          statusText: response.statusText,
        });
      }

      return {
        success: false,
        error: errorMessage,
        statusCode: response.status,
        data: null,
        url, // Include URL in response for debugging
      };
    }

    const data = await response.json();
    
    // Log success for debugging
    if (typeof console !== 'undefined') {
      console.log(`[safeFetch] Success ${response.status} from ${url}`);
    }
    
    return {
      success: true,
      error: null,
      statusCode: response.status,
      data,
    };
  } catch (err) {
    clearTimeout(timeoutId);

    // Log error for debugging
    if (typeof console !== 'undefined') {
      console.error(`[safeFetch] Exception for ${url}:`, {
        name: err.name,
        message: err.message,
        stack: err.stack?.substring(0, 200),
      });
    }

    if (err.name === 'AbortError') {
      return {
        success: false,
        error: `Request timeout after ${timeout}ms - server may be unavailable`,
        statusCode: 504,
        data: null,
        url, // Include URL in response for debugging
      };
    }

    // Check for specific connection errors
    let errorMessage = err.message || 'Failed to connect to server';
    if (err.message?.includes('ECONNREFUSED')) {
      errorMessage = 'Connection refused - server may not be running or tunnel may be down';
    } else if (err.message?.includes('ENOTFOUND') || err.message?.includes('getaddrinfo')) {
      errorMessage = 'DNS lookup failed - check tunnel URL configuration';
    } else if (err.message?.includes('certificate') || err.message?.includes('SSL')) {
      errorMessage = 'SSL/TLS certificate error - check tunnel certificate';
    }

    return {
      success: false,
      error: errorMessage,
      statusCode: 503,
      data: null,
      url, // Include URL in response for debugging
    };
  }
}

/**
 * Check Flask server health with retry logic for 99.99% uptime
 * Implements exponential backoff and multiple endpoint fallbacks
 */
export async function checkFlaskHealth(retries = 3) {
  const flaskUrl = getFlaskUrl();
  
  // Try multiple endpoints as fallback
  const healthEndpoints = [
    `${flaskUrl}/api/system/health`,
    `${flaskUrl}/health`,
    `${flaskUrl}/api/health`,
  ];
  
  let lastError = null;
  let lastStatusCode = null;
  
  // Try each endpoint with retries
  for (const healthUrl of healthEndpoints) {
    // Log what we're checking
    if (typeof console !== 'undefined') {
      console.log(`[checkFlaskHealth] Checking: ${healthUrl} (${retries} retries)`);
    }
    
    // Retry loop with exponential backoff
    for (let attempt = 0; attempt < retries; attempt++) {
      try {
        // Exponential backoff: 2s, 4s, 8s
        if (attempt > 0) {
          const delay = Math.min(2000 * Math.pow(2, attempt - 1), 8000);
          if (typeof console !== 'undefined') {
            console.log(`[checkFlaskHealth] Retry ${attempt}/${retries} after ${delay}ms delay`);
          }
          await new Promise(resolve => setTimeout(resolve, delay));
        }
        
        const result = await safeFetch(healthUrl, {
          timeout: 15000, // Increased timeout for production reliability
        });
        
        // Log result
        if (typeof console !== 'undefined') {
          console.log(`[checkFlaskHealth] Attempt ${attempt + 1} result:`, {
            success: result.success,
            statusCode: result.statusCode,
            error: result.error,
            hasData: !!result.data,
            url: healthUrl,
          });
        }
        
        if (result.success && result.data) {
          const data = result.data;
          // Flask is definitely online if we got a response
          const response = {
            status: 'ok',
            timestamp: data.timestamp || new Date().toISOString(),
            components: {
              flask: 'online',
              ollama: data.components?.ollama || data.ollama?.status || 'unknown',
              supabase: data.components?.supabase || data.supabase?.status || 'unknown',
            },
            ...data,
            url: flaskUrl,
            endpoint: healthUrl,
            attempts: attempt + 1,
          };
          
          if (typeof console !== 'undefined') {
            console.log('[checkFlaskHealth] Success:', {
              status: response.status,
              flask: response.components.flask,
              endpoint: healthUrl,
              attempts: attempt + 1,
            });
          }
          
          return response;
        }
        
        // Store error for logging but continue to next attempt
        lastError = result.error;
        lastStatusCode = result.statusCode;
        
        // If it's a 404, try next endpoint immediately
        if (result.statusCode === 404) {
          if (typeof console !== 'undefined') {
            console.log(`[checkFlaskHealth] Endpoint ${healthUrl} returned 404, trying next endpoint`);
          }
          break; // Break retry loop, try next endpoint
        }
        
        // For other errors, continue retrying this endpoint
        if (attempt < retries - 1) {
          continue; // Try again with backoff
        }
      } catch (err) {
        lastError = err.message || 'Failed to connect to Flask';
        
        if (typeof console !== 'undefined') {
          console.error(`[checkFlaskHealth] Attempt ${attempt + 1} exception:`, {
            error: err.message,
            name: err.name,
            url: healthUrl,
          });
        }
        
        // If this is the last attempt on this endpoint, try next endpoint
        if (attempt === retries - 1) {
          break; // Break retry loop, try next endpoint
        }
      }
    }
  }
  
  // All endpoints failed - Flask is offline
  const errorResponse = {
    status: 'offline',
    message: lastError || 'Flask server not responding after all retries',
    components: {
      flask: 'offline',
    },
    url: flaskUrl,
    error: lastError,
    statusCode: lastStatusCode,
    attempts: retries,
    endpoints: healthEndpoints,
  };
  
  if (typeof console !== 'undefined') {
    console.error('[checkFlaskHealth] All endpoints failed:', errorResponse);
  }
  
  return errorResponse;
}

/**
 * Check Ollama server health
 */
export async function checkOllamaHealth() {
  const ollamaUrl = getOllamaUrl();
  const result = await safeFetch(`${ollamaUrl}/api/tags`, {
    timeout: 5000,
  });

  if (!result.success) {
    return {
      status: 'offline',
      message: result.error,
      url: ollamaUrl,
      models: [],
    };
  }

  const data = result.data;
  return {
    status: 'online',
    url: ollamaUrl,
    models: data.models || [],
    message: 'Ollama server is online',
  };
}

/**
 * Create a safe error response for Next.js API routes
 * Always returns 200 with error status, so frontend can handle gracefully
 */
export function createSafeErrorResponse(message, status = 'idle', data = {}) {
  return {
    status,
    message: message || 'Server unavailable',
    ...data,
  };
}

/**
 * Create a safe success response
 */
export function createSafeSuccessResponse(data, message = 'Success') {
  return {
    status: 'ok',
    message,
    ...data,
  };
}

