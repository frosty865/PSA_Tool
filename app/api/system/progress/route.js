import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';

// Use the shared utility that handles production detection
const FLASK_URL = getFlaskUrl();

export const dynamic = 'force-dynamic'; // Ensure this API route is always dynamic

export async function GET(request) {
  try {
    // Add timeout to fetch request
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
    
    let response;
    try {
      response = await fetch(`${FLASK_URL}/api/system/progress`, {
        cache: 'no-store',
        signal: controller.signal,
        headers: {
          'Accept': 'application/json',
        },
      });
      clearTimeout(timeoutId);
    } catch (fetchError) {
      clearTimeout(timeoutId);
      
      // Handle timeout
      if (fetchError.name === 'AbortError') {
        return NextResponse.json({
          status: 'timeout',
          message: 'Flask server did not respond within 30 seconds',
          timestamp: new Date().toISOString(),
          incoming: 0,
          incoming_label: 'Pending Processing (Learning Mode)',
          incoming_description: 'Files waiting for processing or reprocessing to improve extraction',
          processed: 0,
          processed_label: 'Processed JSON',
          processed_description: 'Extraction results (JSON files)',
          library: 0,
          library_label: 'Archived (Complete)',
          library_description: 'Files successfully processed with sufficient records',
          errors: 0,
          errors_label: 'Processing Errors',
          errors_description: 'Files that failed processing (moved to errors)',
          review: 0,
          review_label: 'Review Queue',
          review_description: 'Extraction results pending review',
          watcher_status: 'unknown'
        }, { status: 200 });
      }
      
      // Handle connection refused
      if (fetchError.code === 'ECONNREFUSED' || fetchError.message?.includes('ECONNREFUSED')) {
        return NextResponse.json({
          status: 'error',
          message: 'Cannot connect to Flask server - check if service is running',
          timestamp: new Date().toISOString(),
          incoming: 0,
          incoming_label: 'Pending Processing (Learning Mode)',
          incoming_description: 'Files waiting for processing or reprocessing to improve extraction',
          processed: 0,
          processed_label: 'Processed JSON',
          processed_description: 'Extraction results (JSON files)',
          library: 0,
          library_label: 'Archived (Complete)',
          library_description: 'Files successfully processed with sufficient records',
          errors: 0,
          errors_label: 'Processing Errors',
          errors_description: 'Files that failed processing (moved to errors)',
          review: 0,
          review_label: 'Review Queue',
          review_description: 'Extraction results pending review',
          watcher_status: 'unknown'
        }, { status: 200 });
      }
      
      throw fetchError; // Re-throw other errors
    }

    if (!response.ok) {
      // Return default values instead of error
      // Note: This might indicate Flask is offline or unreachable
      return NextResponse.json({
        status: 'unknown',
        message: 'Flask API unavailable - cannot read progress',
        timestamp: new Date().toISOString(),
        incoming: 0,
        incoming_label: 'Pending Processing (Learning Mode)',
        incoming_description: 'Files waiting for processing or reprocessing to improve extraction',
        processed: 0,
        processed_label: 'Processed JSON',
        processed_description: 'Extraction results (JSON files)',
        library: 0,
        library_label: 'Archived (Complete)',
        library_description: 'Files successfully processed with sufficient records',
        errors: 0,
        errors_label: 'Processing Errors',
        errors_description: 'Files that failed processing (moved to errors)',
        review: 0,
        review_label: 'Review Queue',
        review_description: 'Extraction results pending review',
        watcher_status: 'unknown'
      }, { status: 200 });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[Progress Proxy] Error:', error);
    // Return default values on error
    // Check if it's a connection error
    const errorMessage = error.message?.includes('ECONNREFUSED') || error.message?.includes('fetch failed')
      ? 'Cannot connect to Flask server - check if service is running'
      : error.message || 'Unknown error';
    
    return NextResponse.json({
      status: 'error',
      message: errorMessage,
      timestamp: new Date().toISOString(),
      incoming: 0,
      incoming_label: 'Pending Processing (Learning Mode)',
      incoming_description: 'Files waiting for processing or reprocessing to improve extraction',
      processed: 0,
      processed_label: 'Processed JSON',
      processed_description: 'Extraction results (JSON files)',
      library: 0,
      library_label: 'Archived (Complete)',
      library_description: 'Files successfully processed with sufficient records',
      errors: 0,
      errors_label: 'Processing Errors',
      errors_description: 'Files that failed processing (moved to errors)',
      review: 0,
      review_label: 'Review Queue',
      review_description: 'Extraction results pending review',
      watcher_status: 'unknown'
    }, { status: 200 });
  }
}

