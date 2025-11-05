import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

// Use service role for API routes to bypass RLS
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

export async function POST(request, { params }) {
  try {
    const { id: submissionId } = await params;
    const body = await request.json();
    const action = body.action;
    const comments = body.comments || body.rejection_reason || null;
    const reviewedBy = body.reviewed_by || null; // User ID from auth token

    // Get user from auth token if available
    let reviewerId = reviewedBy;
    try {
      const authHeader = request.headers.get('authorization');
      if (authHeader && authHeader.toLowerCase().startsWith('bearer ')) {
        const accessToken = authHeader.slice(7).trim();
        const { data: { user }, error: userError } = await supabase.auth.getUser(accessToken);
        if (!userError && user) {
          reviewerId = user.id;
        }
      }
    } catch (authError) {
      console.warn('Could not get reviewer from token:', authError);
    }

    if (!submissionId || !action) {
      return NextResponse.json(
        { error: 'Missing submissionId or action' },
        { status: 400 }
      );
    }

    // -----------------------------------------------------------------
    // 1️⃣ Determine new status
    // -----------------------------------------------------------------
    let status;
    if (action === 'approve') {
      status = 'approved';
    } else if (action === 'reject') {
      status = 'rejected';
    } else {
      return NextResponse.json(
        { error: 'Invalid action: must be approve or reject' },
        { status: 400 }
      );
    }

    // -----------------------------------------------------------------
    // 2️⃣ Update submission record with proper columns
    // -----------------------------------------------------------------
    const updatePayload = {
      status,
      updated_at: new Date().toISOString()
    };
    
    // Add reviewed_at timestamp
    updatePayload.reviewed_at = new Date().toISOString();
    
    // Add reviewed_by if we have a reviewer ID
    if (reviewerId) {
      updatePayload.reviewed_by = reviewerId;
    }
    
    // For rejections, store reason in rejection_reason column
    if (status === 'rejected' && comments) {
      updatePayload.rejection_reason = comments;
    }
    
    // For approvals, store comments in review_comments column
    if (status === 'approved' && comments) {
      updatePayload.review_comments = comments;
    }
    
    // Try to update with all columns, fallback to data JSON if columns don't exist
    let updated;
    let updateError;
    
    try {
      const { data, error } = await supabase
        .from('submissions')
        .update(updatePayload)
        .eq('id', submissionId)
        .select()
        .single();
      
      updated = data;
      updateError = error;
    } catch (e) {
      updateError = e;
    }
    
    // If update failed due to missing columns, store in data JSON as fallback
    if (updateError) {
      console.warn('Primary update failed, trying fallback to data JSON:', updateError.message);
      
      const { data: currentSubmission } = await supabase
        .from('submissions')
        .select('data')
        .eq('id', submissionId)
        .single();
      
      if (currentSubmission && currentSubmission.data) {
        const currentData = typeof currentSubmission.data === 'string'
          ? JSON.parse(currentSubmission.data)
          : currentSubmission.data;
        
        const fallbackPayload = {
          status,
          updated_at: new Date().toISOString(),
          data: JSON.stringify({
            ...currentData,
            reviewed_at: new Date().toISOString(),
            reviewed_by: reviewerId,
            rejection_reason: status === 'rejected' ? comments : undefined,
            review_comments: status === 'approved' ? comments : undefined
          })
        };
        
        const { data: fallbackData, error: fallbackError } = await supabase
          .from('submissions')
          .update(fallbackPayload)
          .eq('id', submissionId)
          .select()
          .single();
        
        if (fallbackError) {
          console.error('Fallback update also failed:', fallbackError);
          throw fallbackError;
        }
        
        updated = fallbackData;
      } else {
        throw updateError;
      }
    }

    if (!updated) {
      throw new Error('Failed to update submission');
    }

    // -----------------------------------------------------------------
    // 3️⃣ Optional: On APPROVE, promote data into production tables
    // -----------------------------------------------------------------
    if (status === 'approved') {
      console.log(`🚀 Promoting submission ${submissionId} to production tables...`);

      // Load submission data
      const { data: submissionData, error: subErr } = await supabase
        .from('submissions')
        .select('data')
        .eq('id', submissionId)
        .single();

      if (subErr) {
        console.error('Error loading submission data:', subErr);
        throw subErr;
      }

      if (!submissionData || !submissionData.data) {
        console.warn(`⚠️ No data field found for submission ${submissionId}`);
      } else {
        // Parse stored JSON safely
        const parsed = typeof submissionData.data === 'string'
          ? JSON.parse(submissionData.data)
          : submissionData.data;

        // --- Vulnerabilities ---
        if (parsed.vulnerabilities && parsed.vulnerabilities.length > 0) {
          const vulnPayload = parsed.vulnerabilities.map(v => {
            // Build description from structured fields if available
            // Use vulnerability or title (NOT vulnerability_text which doesn't exist in schema)
            const vulnStatement = v.vulnerability || v.title || '';
            
            // Build full description text
            let vulnerabilityText = '';
            if (v.question || v.what || v.so_what || vulnStatement) {
              const parts = [];
              if (v.question) parts.push(`Assessment Question: ${v.question}`);
              if (vulnStatement) parts.push(`Vulnerability Statement: ${vulnStatement}`);
              if (v.what) parts.push(`What: ${v.what}`);
              if (v.so_what) parts.push(`So What: ${v.so_what}`);
              vulnerabilityText = parts.join('\n\n');
            } else {
              vulnerabilityText = v.description || '';
            }
            
            // Schema has 'vulnerability' (NOT NULL), 'title', and 'description'
            return {
              submission_id: submissionId,
              vulnerability: vulnStatement, // Required NOT NULL column
              title: vulnStatement, // Also set title for consistency
              description: vulnerabilityText,
              category: v.category || null,
              severity: v.severity || null
            };
          });

          // Insert vulnerabilities with basic fields first
          const { data: insertedVulns, error: vulnErr } = await supabase
            .from('submission_vulnerabilities')
            .insert(vulnPayload)
            .select('id');
          
          // If insert succeeded and we have structured fields, try to update them
          if (insertedVulns && !vulnErr && insertedVulns.length > 0) {
            // Update with structured fields for each vulnerability
            for (let i = 0; i < insertedVulns.length && i < parsed.vulnerabilities.length; i++) {
              const v = parsed.vulnerabilities[i]
              const insertedId = insertedVulns[i].id
              
              const updatePayload = {}
              if (v.question) updatePayload.question = v.question
              if (v.what) updatePayload.what = v.what
              if (v.so_what) updatePayload.so_what = v.so_what
              if (v.sector) updatePayload.sector = v.sector
              if (v.subsector) updatePayload.subsector = v.subsector
              if (v.discipline) updatePayload.discipline = v.discipline
              
              if (Object.keys(updatePayload).length > 0) {
                // Try to update (will fail silently if columns don't exist)
                await supabase
                  .from('submission_vulnerabilities')
                  .update(updatePayload)
                  .eq('id', insertedId)
                  .then(({ error }) => {
                    if (error && error.code !== 'PGRST116') {
                      console.warn('Could not update structured fields (columns may not exist):', error.message)
                    }
                  })
              }
            }
          }
          
          if (vulnErr) {
            console.error('Error inserting vulnerabilities:', vulnErr);
            throw vulnErr;
          }
        }

        // --- OFCs ---
        if (parsed.ofcs && parsed.ofcs.length > 0) {
          const ofcPayload = parsed.ofcs.map(o => ({
            submission_id: submissionId,
            title: o.title,
            description: o.description,
            linked_vulnerability: o.linked_vulnerability || null
          }));

          const { error: ofcErr } = await supabase
            .from('submission_options_for_consideration')
            .insert(ofcPayload);

          if (ofcErr) {
            console.error('Error inserting OFCs:', ofcErr);
            throw ofcErr;
          }
        }

        // --- Sources (optional) ---
        if (parsed.sources && parsed.sources.length > 0) {
          const sourcePayload = parsed.sources.map(s => ({
            submission_id: submissionId,
            source_title: s.title || s.source_title || '',
            source_url: s.url || s.source_url || '',
            organization: s.organization || ''
          }));

          const { error: srcErr } = await supabase
            .from('submission_sources')
            .insert(sourcePayload);

          if (srcErr) {
            console.error('Error inserting sources:', srcErr);
            throw srcErr;
          }
        }

        console.log(`✅ Submission ${submissionId} promoted successfully.`);

        // --- Feed Learning Algorithm ---
        // Create learning events for approved submission
        // This feeds the learning algorithm with positive examples
        try {
          if (parsed.vulnerabilities && parsed.vulnerabilities.length > 0) {
            const learningEvents = parsed.vulnerabilities.map(v => {
              const linkedOfcCount = parsed.ofcs 
                ? parsed.ofcs.filter(o => o.linked_vulnerability === (v.id || v.title || v.vulnerability)).length 
                : 0;
              
              return {
                submission_id: submissionId,
                event_type: 'approval',
                approved: true,
                model_version: process.env.OLLAMA_MODEL || 'vofc-engine:latest',
                confidence_score: 1.0, // Approved by admin = high confidence
                metadata: JSON.stringify({
                  vulnerability_id: v.id || null,
                  vulnerability: v.title || v.vulnerability,
                  category: v.category,
                  severity: v.severity,
                  ofc_count: linkedOfcCount,
                  document_name: parsed.document_name || submissionData.data?.document_name || 'Unknown'
                })
              };
            });

            // Insert learning events (non-blocking - don't fail approval if this fails)
            const { error: learningErr } = await supabase
              .from('learning_events')
              .insert(learningEvents);

            if (learningErr) {
              console.warn('⚠️ Error creating learning events (non-fatal):', learningErr);
              // Don't fail the approval if learning events fail
            } else {
              console.log(`📚 Created ${learningEvents.length} learning events for submission ${submissionId}`);
              console.log(`✅ Learning algorithm fed with approved submission data`);
            }
          }
        } catch (learningError) {
          console.warn('⚠️ Learning event creation failed (non-fatal):', learningError);
          // Continue - approval is more important than learning events
        }
      }
    } else if (status === 'rejected') {
      // On REJECT, optionally create negative learning events
      console.log(`🗑️ Submission ${submissionId} rejected. Not feeding learning algorithm.`);
      // Rejected submissions don't feed the learning algorithm - they're considered invalid
    }

    // -----------------------------------------------------------------
    // 4️⃣ Respond to client
    // -----------------------------------------------------------------
    return NextResponse.json(
      { success: true, id: submissionId, status },
      { status: 200 }
    );

  } catch (e) {
    console.error('❌ Error in POST /api/submissions/[id]/approve:', e);
    return NextResponse.json(
      { error: e.message },
      { status: 500 }
    );
  }
}
