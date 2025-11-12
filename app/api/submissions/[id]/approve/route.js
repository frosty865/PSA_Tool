import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { logAuditEvent, getReviewerId } from '@/app/lib/audit-logger.js';

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
      reviewerId = await getReviewerId(request) || reviewedBy || null;
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

        // Track production IDs for audit logging
        const productionVulnIds = [];
        const productionOfcIds = [];
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
              subsector_id: subsectorId,
              severity_level: v.severity_level || null  // Copy severity level from submission
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
            
            // Track vulnerability ID for audit logging
            if (insertedVuln?.id) {
              productionVulnIds.push(insertedVuln.id);
            }
            
            // Map vulnerability key to production ID for linking OFCs later
            const vulnKey = v.id || v.title || v.vulnerability || vulnStatement;
            vulnOfcMapping.set(vulnKey, insertedVuln.id);
          }
          
          console.log(`✅ Inserted ${productionVulnIds.length} vulnerabilities into production table`);
        }

        // --- Move to Production Tables: Options for Consideration ---
        const ofcVulnLinks = []; // Store OFC-to-vulnerability links to create after insertion
        const submissionToProductionOfcMap = new Map(); // Maps submission OFC IDs to production OFC IDs
        const ofcTextToProductionIdMap = new Map(); // Maps OFC text to production ID (fallback mapping)
        
        // First, fetch submission OFCs to get their database IDs
        let submissionOfcs = [];
        try {
          const { data: submissionOfcsData } = await supabase
            .from('submission_options_for_consideration')
            .select('*')
            .eq('submission_id', submissionId);
          
          if (submissionOfcsData) {
            submissionOfcs = submissionOfcsData;
          }
        } catch (ofcFetchError) {
          console.warn('⚠️ Could not fetch submission OFCs:', ofcFetchError);
        }
        
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
            
            // Track OFC ID for audit logging
            if (insertedOfc?.id) {
              productionOfcIds.push(insertedOfc.id);
            }
            
            // Store OFC and track which vulnerability it's linked to
            const ofcKey = o.id || o.title || o.option || ofcText;
            const linkedVulnKey = o.linked_vulnerability || o.vulnerability_id || o.vuln_id;
            
            ofcVulnLinks.push({
              ofc_id: insertedOfc.id,
              ofc_key: ofcKey,
              linked_vuln_key: linkedVulnKey
            });
            
            // Map OFC text to production ID (for fallback matching)
            ofcTextToProductionIdMap.set(ofcText.toLowerCase().trim(), insertedOfc.id);
            
            // Try to map submission OFC ID to production OFC ID
            // Match by text since submission OFC IDs might not match parsed data IDs
            const matchingSubmissionOfc = submissionOfcs.find(so => 
              (so.option_text || '').toLowerCase().trim() === ofcText.toLowerCase().trim()
            );
            
            if (matchingSubmissionOfc?.id) {
              submissionToProductionOfcMap.set(matchingSubmissionOfc.id, insertedOfc.id);
            } else if (o.id) {
              // Fallback: use parsed data ID if available
              submissionToProductionOfcMap.set(o.id, insertedOfc.id);
            }
          }
          
          console.log(`✅ Inserted ${productionOfcIds.length} OFCs into production table`);
          
          // --- Create vulnerability-OFC links ---
          if (ofcVulnLinks.length > 0 && vulnOfcMapping.size > 0) {
            const linkPromises = [];
            
            for (const prodOfc of ofcVulnLinks) {
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

        // --- Sources: Promote to production and create OFC-source links ---
        const productionSourceIds = [];
        const submissionToProductionSourceMap = new Map(); // Maps submission source IDs to production source IDs
        
        // First, get submission sources (from submission_sources table or parsed data)
        let submissionSources = [];
        try {
          const { data: submissionSourcesData } = await supabase
            .from('submission_sources')
            .select('*')
            .eq('submission_id', submissionId);
          
          if (submissionSourcesData && submissionSourcesData.length > 0) {
            submissionSources = submissionSourcesData;
          } else if (parsed.sources && parsed.sources.length > 0) {
            // Fallback to parsed sources if submission_sources table is empty
            submissionSources = parsed.sources;
          }
        } catch (sourceFetchError) {
          console.warn('⚠️ Could not fetch submission sources:', sourceFetchError);
          // Continue - sources are optional
        }
        
        // Promote sources to production sources table
        if (submissionSources.length > 0) {
          for (const s of submissionSources) {
            const productionSource = {
              source_title: s.source_title || s.title || s.source_text || '',
              source_url: s.source_url || s.url || null,
              author_org: s.author_org || s.organization || null,
              publication_year: s.publication_year || s.year || null,
              citation: s.source_text || s.citation || s.source_title || null,
              content_restriction: s.content_restriction || 'public'
            };
            
            // Only insert if we have at least a title
            if (productionSource.source_title) {
              const { data: insertedSource, error: srcErr } = await supabase
                .from('sources')
                .insert(productionSource)
                .select('id')
                .single();
              
              if (srcErr) {
                // Try to find existing source instead of failing
                const { data: existingSource } = await supabase
                  .from('sources')
                  .select('id')
                  .eq('source_title', productionSource.source_title)
                  .maybeSingle();
                
                if (existingSource?.id) {
                  productionSourceIds.push(existingSource.id);
                  // Map submission source ID to production source ID
                  if (s.id) {
                    submissionToProductionSourceMap.set(s.id, existingSource.id);
                  }
                  console.log(`✅ Using existing source: ${productionSource.source_title}`);
                } else {
                  console.warn('⚠️ Could not insert or find source:', srcErr);
                }
              } else if (insertedSource?.id) {
                productionSourceIds.push(insertedSource.id);
                // Map submission source ID to production source ID
                if (s.id) {
                  submissionToProductionSourceMap.set(s.id, insertedSource.id);
                }
                console.log(`✅ Promoted source to production: ${productionSource.source_title}`);
              }
            }
          }
        }
        
        // Create OFC-source links in production ofc_sources table
        if (productionSourceIds.length > 0 && productionOfcIds.length > 0) {
          // Get submission OFC-source links to map to production
          let submissionOfcSourceLinks = [];
          try {
            const { data: submissionLinks } = await supabase
              .from('submission_ofc_sources')
              .select('*')
              .eq('submission_id', submissionId);
            
            if (submissionLinks) {
              submissionOfcSourceLinks = submissionLinks;
            }
          } catch (linkFetchError) {
            console.warn('⚠️ Could not fetch submission OFC-source links:', linkFetchError);
          }
          
          // Create production OFC-source links
          // Map submission OFC-source links to production IDs
          const ofcSourceLinkPromises = [];
          const createdLinks = new Set(); // Track created links to avoid duplicates
          
          if (submissionOfcSourceLinks.length > 0 && submissionToProductionOfcMap.size > 0) {
            // Use submission links to map to production IDs
            for (const link of submissionOfcSourceLinks) {
              const submissionOfcId = link.ofc_id;
              const submissionSourceId = link.source_id;
              
              // Map submission OFC ID to production OFC ID
              const productionOfcId = submissionToProductionOfcMap.get(submissionOfcId);
              
              // Map submission source ID to production source ID
              const productionSourceId = submissionToProductionSourceMap.get(submissionSourceId);
              
              if (productionOfcId && productionSourceId) {
                const linkKey = `${productionOfcId}-${productionSourceId}`;
                if (!createdLinks.has(linkKey)) {
                  createdLinks.add(linkKey);
                  ofcSourceLinkPromises.push(
                    supabase
                      .from('ofc_sources')
                      .insert({
                        ofc_id: productionOfcId,
                        source_id: productionSourceId
                      })
                      .then(({ error }) => {
                        if (error && !error.message.includes('duplicate') && !error.message.includes('unique')) {
                          console.warn('⚠️ Error creating OFC-source link:', error);
                        }
                      })
                  );
                }
              }
            }
          }
          
          // If no submission links or mapping failed, link all OFCs to first source as fallback
          if (ofcSourceLinkPromises.length === 0 && productionSourceIds.length > 0) {
            for (const ofcId of productionOfcIds) {
              // Link to first source
              const sourceId = productionSourceIds[0];
              const linkKey = `${ofcId}-${sourceId}`;
              if (!createdLinks.has(linkKey)) {
                createdLinks.add(linkKey);
                ofcSourceLinkPromises.push(
                  supabase
                    .from('ofc_sources')
                    .insert({
                      ofc_id: ofcId,
                      source_id: sourceId
                    })
                    .then(({ error }) => {
                      if (error && !error.message.includes('duplicate') && !error.message.includes('unique')) {
                        console.warn('⚠️ Error creating OFC-source link:', error);
                      }
                    })
                );
              }
            }
          }
          
          await Promise.all(ofcSourceLinkPromises);
          console.log(`✅ Created ${ofcSourceLinkPromises.length} OFC-source links in production`);
        }

        console.log(`✅ Submission ${submissionId} promoted successfully.`);

        // --- Log Audit Event ---
        // Log audit event with collected vulnerability and OFC IDs (non-blocking)
        try {
          await logAuditEvent(
            submissionId,
            reviewerId,
            'approved',
            productionVulnIds,
            productionOfcIds,
            comments || null
          );
        } catch (auditError) {
          console.warn('⚠️ Error logging audit event (non-fatal):', auditError);
          // Continue - approval is more important than audit logging
        }

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
      // On REJECT, delete the submission immediately
      console.log(`🗑️ Submission ${submissionId} rejected. Deleting submission and related records...`);
      
      // --- Log Audit Event BEFORE deletion ---
      try {
        await logAuditEvent(
          submissionId,
          reviewerId,
          'rejected',
          [],
          [],
          comments || null
        );
      } catch (auditError) {
        console.warn('⚠️ Error logging audit event (non-fatal):', auditError);
      }
      
      // --- Delete submission and all related records ---
      // Delete from submission mirror tables first (due to foreign key constraints)
      await supabase
        .from('submission_vulnerability_ofc_links')
        .delete()
        .eq('submission_id', submissionId);
      
      await supabase
        .from('submission_ofc_sources')
        .delete()
        .eq('submission_id', submissionId);
      
      await supabase
        .from('submission_options_for_consideration')
        .delete()
        .eq('submission_id', submissionId);
      
      await supabase
        .from('submission_vulnerabilities')
        .delete()
        .eq('submission_id', submissionId);
      
      await supabase
        .from('submission_sources')
        .delete()
        .eq('submission_id', submissionId);
      
      // Finally, delete the main submission
      const { error: deleteError } = await supabase
        .from('submissions')
        .delete()
        .eq('id', submissionId);
      
      if (deleteError) {
        console.error('❌ Error deleting rejected submission:', deleteError);
        return NextResponse.json(
          { 
            error: 'Failed to delete rejected submission', 
            details: deleteError.message 
          },
          { status: 500 }
        );
      }
      
      console.log('✅ Rejected submission deleted successfully');
      
      // Return success with deleted status
      return NextResponse.json(
        { 
          success: true, 
          id: submissionId, 
          status: 'rejected',
          message: 'Submission rejected and deleted successfully',
          deleted: true
        },
        { status: 200 }
      );
    }

    // -----------------------------------------------------------------
    // 4️⃣ Respond to client (for approved submissions)
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
