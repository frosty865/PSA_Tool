/**
 * Next.js API route for dashboard status
 * Returns current system status for dashboard display
 */

import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';

const FLASK_URL = getFlaskUrl();

export const dynamic = 'force-dynamic';

export async function GET(request) {
  try {
    // Get system health and progress
    const [healthRes, progressRes] = await Promise.allSettled([
      fetch(`${FLASK_URL}/api/system/health`, {
        cache: 'no-store',
        headers: { 'Accept': 'application/json' },
      }).catch(() => null),
      fetch(`${FLASK_URL}/api/system/progress`, {
        cache: 'no-store',
        headers: { 'Accept': 'application/json' },
      }).catch(() => null),
    ]);

    const health = healthRes.status === 'fulfilled' && healthRes.value?.ok
      ? await healthRes.value.json().catch(() => ({}))
      : { components: { flask: 'offline', ollama: 'unknown', supabase: 'unknown' } };

    const progress = progressRes.status === 'fulfilled' && progressRes.value?.ok
      ? await progressRes.value.json().catch(() => ({}))
      : { incoming: 0, processed: 0, library: 0, errors: 0, review: 0 };

    return NextResponse.json({
      status: 'ok',
      health: health.components || health,
      progress: progress,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('[Dashboard Status] Error:', error);
    return NextResponse.json(
      {
        status: 'error',
        health: { flask: 'offline', ollama: 'unknown', supabase: 'unknown' },
        progress: { incoming: 0, processed: 0, library: 0, errors: 0, review: 0 },
        error: error.message,
        timestamp: new Date().toISOString()
      },
      { status: 200 } // Return 200 so frontend can handle gracefully
    );
  }
}

