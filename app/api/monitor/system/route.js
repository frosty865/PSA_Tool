import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function GET(request) {
  try {
    const flaskUrl = getFlaskUrl();
    
    // Get system health from Flask
    let systemHealth = {
      flask: 'offline',
      ollama: 'offline',
      supabase: 'offline',
      tunnel: 'offline'
    };
    
    try {
      const healthResponse = await fetch(`${flaskUrl}/api/system/health`);
      if (healthResponse.ok) {
        const healthData = await healthResponse.json();
        systemHealth = {
          flask: healthData.flask || 'offline',
          ollama: healthData.ollama || 'offline',
          supabase: healthData.supabase || 'offline',
          tunnel: healthData.tunnel || 'offline'
        };
      }
    } catch (e) {
      console.warn('[monitor/system] Failed to get system health:', e);
    }
    
    // Get progress
    let progress = null;
    try {
      const progressResponse = await fetch(`${flaskUrl}/api/system/progress`);
      if (progressResponse.ok) {
        progress = await progressResponse.json();
      }
    } catch (e) {
      console.warn('[monitor/system] Failed to get progress:', e);
    }
    
    const system = {
      timestamp: new Date().toISOString(),
      health: systemHealth,
      progress: progress,
      urls: {
        flask: flaskUrl,
        ollama: process.env.OLLAMA_HOST || 'http://127.0.0.1:11434',
        tunnel: process.env.TUNNEL_URL || ''
      }
    };
    
    return NextResponse.json({
      success: true,
      system
    });
  } catch (error) {
    console.error('[monitor/system] Error:', error);
    return NextResponse.json(
      {
        success: false,
        error: error.message || 'Failed to load system data',
        system: {
          timestamp: new Date().toISOString(),
          health: { flask: 'error', ollama: 'error', supabase: 'error', tunnel: 'error' },
          progress: null
        }
      },
      { status: 500 }
    );
  }
}

