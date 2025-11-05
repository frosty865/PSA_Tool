import { NextResponse } from 'next/server';
import { monitoring } from '../../../lib/monitoring';

// Cache health check for 30 seconds
export const revalidate = 30;

export async function GET(request) {
  try {
    const systemStatus = await monitoring.getSystemStatus();
    
    const statusCode = systemStatus.status === 'healthy' ? 200 : 
                      systemStatus.status === 'degraded' ? 200 : 503;
    
    return NextResponse.json(systemStatus, { 
      status: statusCode,
      headers: {
        'Cache-Control': 'public, max-age=30, s-maxage=30',
        'Content-Type': 'application/json'
      }
    });
  } catch (error) {
    console.error('Health check failed:', error);
    return NextResponse.json(
      { 
        status: 'critical',
        error: 'Health check system failure',
        timestamp: new Date().toISOString()
      },
      { status: 503 }
    );
  }
}