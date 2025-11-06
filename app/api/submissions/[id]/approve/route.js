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

        // --- Move to Production Tables: Vulnerabilities ---
        // Helper functions to resolve sector/subsector IDs
        const resolveSectorId = async (sectorName) => {
          if (!sectorName) return null;
          try {
            const { data } = await supabase
              .from('sectors')
              .select('id')
              .ilike('name', sectorName)
              .maybeSingle();
            return data?.id || null;
          } catch {
            return null;
          }
        };
        
        const resolveSubsectorId = async (subsectorName) => {
          if (!subsectorName) return null;
          try {
            const { data } = await supabase
              .from('subsectors')
              .select('id')
              .ilike('name', subsectorName)
              .maybeSingle();
            return data?.id || null;
          } catch {
            return null;
          }
        };

        const productionVulns = [];
        const vulnOfcMapping = new Map(); // Maps vulnerability keys to production vulnerability IDs
        
        if (parsed.vulnerabilities && parsed.vulnerabilities.length > 0) {
          // Process each vulnerability and move to production
          for (const v of parsed.vulnerabilities) {
            const vulnStatement = v.vulnerability || v.title || '';
            if (!vulnStatement) continue;
            
            // Build description from structured fields
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
            
            // Resolve taxonomy IDs
            const sectorId = v.sector_id || await resolveSectorId(v.sector);
            const subsectorId = v.subsector_id || await resolveSubsectorId(v.subsector);
            
            // Insert into production vulnerabilities table
            const productionVuln = {
              vulnerability_name: vulnStatement,
              description: vulnerabilityText,
              discipline: v.discipline || null,
              sector_id: sectorId,
              subsector_id: subsectorId
            };
            
            const { data: insertedVuln, error: vulnErr } = await supabase
              .from('vulnerabilities')
              .insert(productionVuln)
              .select('id')
              .single();
            
            if (vulnErr) {
              console.error('Error inserting production vulnerability:', vulnErr);
              // Continue with other vulnerabilities even if one fails
              continue;
            }
            
            productionVulns.push(insertedVuln);
            
            // Map vulnerability key to production ID for linking OFCs later
            const vulnKey = v.id || v.title || v.vulnerability || vulnStatement;
            vulnOfcMapping.set(vulnKey, insertedVuln.id);
          }
          
          console.log(`✅ Inserted ${productionVulns.length} vulnerabilities into production table`);
        }

        // --- Move to Production Tables: Options for Consideration ---
        const productionOfcs = [];
        const ofcVulnLinks = []; // Store OFC-to-vulnerability links to create after insertion
        
        if (parsed.ofcs && parsed.ofcs.length > 0) {
          // Insert OFCs into production table
          for (const o of parsed.ofcs) {
            const ofcText = o.option_text || o.option || o.title || '';
            if (!ofcText) continue;
            
            // Resolve taxonomy IDs
            const sectorId = o.sector_id || await resolveSectorId(o.sector);
            const subsectorId = o.subsector_id || await resolveSubsectorId(o.subsector);
            
            const productionOfc = {
              option_text: ofcText,
              discipline: o.discipline || null,
              sector_id: sectorId,
              subsector_id: subsectorId
            };
            
            const { data: insertedOfc, error: ofcErr } = await supabase
              .from('options_for_consideration')
              .insert(productionOfc)
              .select('id')
              .single();
            
            if (ofcErr) {
              console.error('Error inserting production OFC:', ofcErr);
              continue;
            }
            
            // Store OFC and track which vulnerability it's linked to
            const ofcKey = o.id || o.title || o.option || ofcText;
            const linkedVulnKey = o.linked_vulnerability || o.vulnerability_id || o.vuln_id;
            
            productionOfcs.push({
              ofc_id: insertedOfc.id,
              ofc_key: ofcKey,
              linked_vuln_key: linkedVulnKey
            });
          }
          
          console.log(`✅ Inserted ${productionOfcs.length} OFCs into production table`);
          
          // --- Create vulnerability-OFC links ---
          if (productionOfcs.length > 0 && vulnOfcMapping.size > 0) {
            const linkPromises = [];
            
            for (const prodOfc of productionOfcs) {
              if (!prodOfc.linked_vuln_key) continue;
              
              // Find the production vulnerability ID for this OFC's linked vulnerability
              const prodVulnId = vulnOfcMapping.get(prodOfc.linked_vuln_key);
              
              if (prodVulnId) {
                linkPromises.push(
                  supabase
                    .from('vulnerability_ofc_links')
                    .insert({
                      vulnerability_id: prodVulnId,
                      ofc_id: prodOfc.ofc_id,
                      link_type: 'direct',
                      confidence_score: 1.0 // Approved by admin = high confidence
                    })
                    .then(({ error }) => {
                      if (error && !error.message.includes('duplicate') && !error.message.includes('unique')) {
                        console.warn('Error creating vulnerability-OFC link:', error);
                      }
                    })
                );
              }
            }
            
            await Promise.all(linkPromises);
            console.log(`✅ Created ${linkPromises.length} vulnerability-OFC links`);
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
