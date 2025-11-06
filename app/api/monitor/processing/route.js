import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';
import { supabaseAdmin } from '@/app/lib/supabase-admin';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function GET(request) {
  try {
    const flaskUrl = getFlaskUrl();
    
    // Get progress from auto-processor
    let progress = null;
    try {
      const progressResponse = await fetch(`${flaskUrl}/api/system/progress`);
      if (progressResponse.ok) {
        progress = await progressResponse.json();
      }
    } catch (e) {
      console.warn('[monitor/processing] Failed to get progress:', e);
    }
    
    // Get Ollama service status
    let ollamaService = {
      status: 'offline',
      url: process.env.OLLAMA_HOST || 'http://127.0.0.1:11434',
      model: process.env.OLLAMA_MODEL || 'vofc-engine:latest',
      target_model_found: false,
      error: null
    };
    
    try {
      const ollamaResponse = await fetch(`${ollamaService.url}/api/tags`);
      if (ollamaResponse.ok) {
        const ollamaData = await ollamaResponse.json();
        const models = ollamaData.models || [];
        ollamaService.target_model_found = models.some(m => m.name === ollamaService.model);
        ollamaService.status = ollamaService.target_model_found ? 'online' : 'offline';
      }
    } catch (e) {
      ollamaService.status = 'offline';
      ollamaService.error = e.message;
    }
    
    // Get submissions analysis
    let submissionsAnalysis = {
      total: 0,
      pending: 0,
      processed: 0,
      with_ollama_results: 0
    };
    
    let recentSubmissions = [];
    
    try {
      const { data: submissions, error } = await supabaseAdmin
        .from('submissions')
        .select('id, type, status, created_at, data')
        .order('created_at', { ascending: false })
        .limit(10);
      
      if (!error && submissions) {
        submissionsAnalysis.total = submissions.length;
        submissionsAnalysis.pending = submissions.filter(s => s.status === 'pending_review').length;
        submissionsAnalysis.processed = submissions.filter(s => s.status === 'approved').length;
        
        // Check for Ollama results in data field
        submissionsAnalysis.with_ollama_results = submissions.filter(s => {
          const data = typeof s.data === 'string' ? JSON.parse(s.data) : s.data;
          return data && (data.ollama_results || data.model_results || data.chunks);
        }).length;
        
        recentSubmissions = submissions.map(s => ({
          id: s.id,
          type: s.type,
          status: s.status,
          created_at: s.created_at,
          has_ollama_results: (() => {
            const data = typeof s.data === 'string' ? JSON.parse(s.data) : s.data;
            return !!(data && (data.ollama_results || data.model_results || data.chunks));
          })()
        }));
      }
    } catch (e) {
      console.error('[monitor/processing] Error fetching submissions:', e);
    }
    
    // Get file processing stats from progress
    const fileProcessing = {
      docs: {
        count: progress?.incoming || 0
      },
      processing: {
        count: progress?.status === 'running' ? (progress?.incoming || 0) : 0
      },
      completed: {
        count: progress?.processed || 0
      },
      failed: {
        count: progress?.errors || 0
      }
    };
    
    const monitoring = {
      timestamp: new Date().toISOString(),
      ollama_service: ollamaService,
      submissions: {
        analysis: submissionsAnalysis,
        recent_submissions: recentSubmissions
      },
      file_processing: fileProcessing,
      progress: progress
    };
    
    return NextResponse.json({
      success: true,
      monitoring
    });
  } catch (error) {
    console.error('[monitor/processing] Error:', error);
    return NextResponse.json(
      {
        success: false,
        error: error.message || 'Failed to load monitoring data',
        monitoring: {
          timestamp: new Date().toISOString(),
          ollama_service: { status: 'error', error: error.message },
          submissions: { analysis: {}, recent_submissions: [] },
          file_processing: { docs: { count: 0 }, processing: { count: 0 }, completed: { count: 0 }, failed: { count: 0 } }
        }
      },
      { status: 500 }
    );
  }
}

