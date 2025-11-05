import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase-client.js';
import { spawn } from 'child_process';
import path from 'path';

export async function POST() {
  try {
    console.log('🤖 Starting auto OFC generation...');
    
    // Check if there are vulnerabilities that need OFCs
    const { data: vulns, error } = await supabaseAdmin.rpc('get_vulns_missing_ofcs');
    
    if (error) {
      console.error('Error fetching vulnerabilities:', error);
      return NextResponse.json(
        { success: false, error: 'Failed to fetch vulnerabilities' },
        { status: 500 }
      );
    }
    
    if (!vulns || vulns.length === 0) {
      return NextResponse.json({
        success: true,
        message: 'No vulnerabilities need new OFCs',
        generated: 0
      });
    }
    
    console.log(`📊 Found ${vulns.length} vulnerabilities needing OFCs`);
    
    // Run the OFC generation script
    const scriptPath = path.join(process.cwd(), 'apps', 'backend', 'server', 'services', 'knowledge', 'generateOFCs.js');
    
    return new Promise((resolve) => {
      const child = spawn('node', [scriptPath], {
        cwd: process.cwd(),
        env: {
          ...process.env,
          SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
          SUPABASE_SERVICE_ROLE_KEY: process.env.SUPABASE_SERVICE_ROLE_KEY,
          OLLAMA_URL: process.env.OLLAMA_URL || process.env.OLLAMA_API_BASE_URL || process.env.OLLAMA_BASE_URL || 'https://ollama.frostech.site/api',
          OLLAMA_MODEL: process.env.OLLAMA_MODEL || 'mistral:latest'
        }
      });
      
      let output = '';
      let errorOutput = '';
      
      child.stdout.on('data', (data) => {
        output += data.toString();
        console.log('OFC Generator:', data.toString());
      });
      
      child.stderr.on('data', (data) => {
        errorOutput += data.toString();
        console.error('OFC Generator Error:', data.toString());
      });
      
      child.on('close', (code) => {
        if (code === 0) {
          resolve(NextResponse.json({
            success: true,
            message: 'OFC generation completed successfully',
            output: output,
            vulnerabilities_processed: vulns.length
          }));
        } else {
          resolve(NextResponse.json({
            success: false,
            error: 'OFC generation failed',
            output: output,
            error: errorOutput
          }, { status: 500 }));
        }
      });
    });
    
  } catch (error) {
    console.error('Error in OFC generation API:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}
