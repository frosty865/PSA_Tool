import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/app/lib/supabase-admin.js';

/**
 * Update a submission record with VOFC data from the library JSON file
 * This is useful for submissions created before we started storing full data
 */
export async function POST(request, { params }) {
  try {
    // Check admin authentication
    const authHeader = request.headers.get('authorization');
    let accessToken = null;
    
    if (authHeader && authHeader.toLowerCase().startsWith('bearer ')) {
      accessToken = authHeader.slice(7).trim();
    }
    
    if (!accessToken) {
      return NextResponse.json({ error: 'No authentication token provided' }, { status: 401 });
    }
    
    const { data: { user }, error: userError } = await supabaseAdmin.auth.getUser(accessToken);
    
    if (userError || !user) {
      return NextResponse.json({ error: 'Invalid authentication token' }, { status: 401 });
    }
    
    // Check admin role
    const { data: profile } = await supabaseAdmin
      .from('user_profiles')
      .select('role')
      .eq('user_id', user.id)
      .maybeSingle();
    
    const derivedRole = String(profile?.role || user.user_metadata?.role || 'user').toLowerCase();
    const isAdmin = ['admin', 'spsa'].includes(derivedRole);
    const allowlist = (process.env.ADMIN_EMAILS || '').toLowerCase().split(',').map(s => s.trim()).filter(Boolean);
    const isEmailAdmin = allowlist.includes(String(user.email).toLowerCase());
    
    if (!isAdmin && !isEmailAdmin) {
      return NextResponse.json({ error: 'Admin access required' }, { status: 403 });
    }

    const { id: submissionId } = await params;

    // Get submission to find the document name
    const { data: submission, error: subError } = await supabaseAdmin
      .from('submissions')
      .select('data')
      .eq('id', submissionId)
      .single();

    if (subError || !submission) {
      return NextResponse.json({ error: 'Submission not found' }, { status: 404 });
    }

    const submissionData = typeof submission.data === 'string' 
      ? JSON.parse(submission.data) 
      : submission.data;

    const documentName = submissionData.document_name || submissionData.document_name;
    if (!documentName) {
      return NextResponse.json({ error: 'No document name found in submission' }, { status: 400 });
    }

    // Try to load JSON from Flask server's library endpoint
    // Extract base filename (without extension)
    const baseName = documentName.replace('.pdf', '').replace('.txt', '');
    const jsonFilename = `${baseName}.json`;
    
    // Flask Server URL - Priority: OLLAMA_SERVER_URL > OLLAMA_LOCAL_URL > derived from OLLAMA_URL > default
    const ollamaApiUrl = process.env.OLLAMA_URL || 'https://ollama.frostech.site';
    
    // Detect if we're in a local development environment
    const isLocalDev = process.env.NODE_ENV !== 'production' || 
                       process.env.VERCEL !== '1' ||
                       process.env.OLLAMA_LOCAL_URL;
    
    // Derive Flask server URL - use localhost in local dev, production URL in production
    // Production uses Cloudflare tunnel at flask.frostech.site (no port, HTTPS)
    let defaultFlaskUrl = isLocalDev 
      ? 'http://127.0.0.1:5000'  // Local development
      : 'https://flask.frostech.site';  // Production (Cloudflare tunnel)
    
    if (process.env.OLLAMA_URL && isLocalDev) {
      try {
        const url = new URL(ollamaApiUrl);
        if (url.hostname === 'localhost' || url.hostname === '127.0.0.1') {
          defaultFlaskUrl = 'http://127.0.0.1:5000';
        }
      } catch {
        // If URL parsing fails, use default
      }
    } else if (process.env.OLLAMA_URL && !isLocalDev) {
      // In production, prefer flask.frostech.site (Cloudflare tunnel)
      try {
        const url = new URL(ollamaApiUrl);
        if (url.hostname === 'ollama.frostech.site') {
          defaultFlaskUrl = 'https://flask.frostech.site';
        } else {
          defaultFlaskUrl = `${url.protocol}//flask.${url.hostname}`;
        }
      } catch {
        // If URL parsing fails, use default
      }
    }
    
    const flaskUrl = process.env.OLLAMA_SERVER_URL || process.env.OLLAMA_LOCAL_URL || defaultFlaskUrl;
    
    let vofcData = null;
    try {
      // Try to find the actual filename by listing files (if endpoint exists)
      let actualFilename = jsonFilename;
      let folderToUse = 'library'; // Default to library folder
      
      // Try to find the file in both 'library' and 'processed' folders
      const foldersToCheck = ['processed', 'library'];
      
      for (const folder of foldersToCheck) {
        try {
          const listResponse = await fetch(`${flaskUrl}/api/files/list?folder=${folder}`, {
            method: 'GET',
            signal: AbortSignal.timeout(3000)
          });
          
          if (listResponse.ok) {
            const fileList = await listResponse.json();
            // Find matching JSON file (case-insensitive, partial match)
            const baseNameLower = baseName.toLowerCase();
            const matchingFile = fileList.files?.find(f => 
              f.toLowerCase().includes(baseNameLower) && f.toLowerCase().endsWith('.json')
            );
            if (matchingFile) {
              actualFilename = matchingFile;
              folderToUse = folder;
              console.log(`Found matching JSON file in ${folder}: ${actualFilename}`);
              break; // Found it, stop searching
            }
          }
        } catch (listError) {
          // List endpoint might not exist, continue with next folder
          console.log(`File list endpoint not available for ${folder}, trying next folder`);
        }
      }

      // Read the JSON file from Flask server
      const jsonResponse = await fetch(`${flaskUrl}/api/files/read?folder=${folderToUse}&filename=${encodeURIComponent(actualFilename)}`, {
        method: 'GET',
        signal: AbortSignal.timeout(10000) // Increased timeout
      });
      
      if (jsonResponse.ok) {
        // Flask server returns parsed JSON directly for .json files
        vofcData = await jsonResponse.json();
        console.log(`Loaded VOFC data: ${vofcData.vulnerabilities?.length || 0} vulnerabilities, ${vofcData.ofcs?.length || 0} OFCs`);
      } else {
        const errorText = await jsonResponse.text().catch(() => 'Unknown error');
        let errorData;
        try {
          errorData = JSON.parse(errorText);
        } catch {
          errorData = { error: errorText };
        }
        console.error(`Flask server error (${jsonResponse.status}):`, errorData);
        return NextResponse.json({ 
          error: 'JSON file not found on Flask server', 
          filename: actualFilename,
          flask_error: errorData.error || errorText,
          message: 'The JSON file may have been moved or deleted. Flask server may not be accessible.',
          attempted_url: `${flaskUrl}/api/files/read?folder=${folderToUse}&filename=${encodeURIComponent(actualFilename)}`
        }, { status: 404 });
      }
    } catch (fetchError) {
      // Handle network errors (Flask server not accessible)
      console.error('Error fetching from Flask server:', fetchError);
      if (fetchError.name === 'AbortError') {
        return NextResponse.json({ 
          error: 'Flask server request timed out', 
          message: 'The Flask server did not respond within 10 seconds',
          note: 'Make sure Flask server is running',
          flask_url: flaskUrl
        }, { status: 503 });
      }
      return NextResponse.json({ 
        error: 'Failed to fetch JSON from Flask server', 
        message: fetchError.message || 'Network error',
        error_type: fetchError.name || 'Unknown',
        note: 'Make sure Flask server is running and accessible at ' + flaskUrl,
        flask_url: flaskUrl
      }, { status: 503 });
    }

    if (!vofcData || (!vofcData.vulnerabilities && !vofcData.ofcs)) {
      return NextResponse.json({ 
        error: 'Invalid or empty VOFC data in JSON file' 
      }, { status: 400 });
    }

    // Merge the VOFC data with existing metadata
    const updatedData = {
      ...submissionData,
      vulnerabilities: vofcData.vulnerabilities || [],
      ofcs: vofcData.ofcs || [],
      sources: vofcData.sources || [],
      links: vofcData.links || {}
    };

    // Update the submission record
    const { error: updateError } = await supabaseAdmin
      .from('submissions')
      .update({
        data: JSON.stringify(updatedData),
        updated_at: new Date().toISOString()
      })
      .eq('id', submissionId);

    if (updateError) {
      console.error('Error updating submission:', updateError);
      return NextResponse.json({ error: updateError.message }, { status: 500 });
    }

    return NextResponse.json({ 
      success: true,
      message: 'Submission data updated successfully',
      vulnerabilities: vofcData.vulnerabilities?.length || 0,
      ofcs: vofcData.ofcs?.length || 0
    });

  } catch (e) {
    console.error('Error updating submission data:', e);
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}

