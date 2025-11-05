import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/app/lib/supabase-admin.js';

const supabase = supabaseAdmin;

/**
 * Check if a vulnerability or OFC already exists in the database (fuzzy match by intent)
 * Uses text similarity to detect duplicates, not just exact matches
 */
function normalizeText(text) {
  if (!text) return '';
  return text
    .toLowerCase()
    .replace(/[^\w\s]/g, ' ') // Remove punctuation
    .replace(/\s+/g, ' ') // Normalize whitespace
    .trim();
}

function calculateSimilarity(text1, text2) {
  const norm1 = normalizeText(text1);
  const norm2 = normalizeText(text2);
  
  if (!norm1 || !norm2) return 0;
  if (norm1 === norm2) return 1;
  
  // Simple token-based similarity
  const tokens1 = new Set(norm1.split(' ').filter(w => w.length > 2));
  const tokens2 = new Set(norm2.split(' ').filter(w => w.length > 2));
  
  if (tokens1.size === 0 || tokens2.size === 0) return 0;
  
  const intersection = new Set([...tokens1].filter(t => tokens2.has(t)));
  const union = new Set([...tokens1, ...tokens2]);
  
  // Jaccard similarity
  return intersection.size / union.size;
}

export async function POST(request) {
  try {
    const { vulnerabilities, ofcs } = await request.json();
    
    if (!vulnerabilities && !ofcs) {
      return NextResponse.json({ error: 'No vulnerabilities or OFCs provided' }, { status: 400 });
    }
    
    const duplicateResults = {
      vulnerabilities: [],
      ofcs: []
    };
    
    // Check vulnerabilities for duplicates
    if (vulnerabilities && Array.isArray(vulnerabilities)) {
      // Get all existing vulnerabilities from production tables
      const { data: existingVulns, error: vulnError } = await supabase
        .from('submission_vulnerabilities')
        .select('id, title, description, category');
      
      if (!vulnError && existingVulns) {
        for (const vuln of vulnerabilities) {
          const vulnText = `${vuln.title || vuln.vulnerability || ''} ${vuln.description || ''}`.trim();
          
          if (!vulnText) continue;
          
          let maxSimilarity = 0;
          let duplicate = null;
          
          for (const existing of existingVulns) {
            const existingText = `${existing.title || ''} ${existing.description || ''}`.trim();
            const similarity = calculateSimilarity(vulnText, existingText);
            
            if (similarity > maxSimilarity && similarity >= 0.7) { // 70% similarity threshold
              maxSimilarity = similarity;
              duplicate = existing;
            }
          }
          
          if (duplicate) {
            duplicateResults.vulnerabilities.push({
              submission_vuln: vuln,
              existing_vuln: duplicate,
              similarity: maxSimilarity,
              is_duplicate: true
            });
          } else {
            duplicateResults.vulnerabilities.push({
              submission_vuln: vuln,
              is_duplicate: false
            });
          }
        }
      }
    }
    
    // Check OFCs for duplicates
    if (ofcs && Array.isArray(ofcs)) {
      // Get all existing OFCs from production tables
      const { data: existingOfcs, error: ofcError } = await supabase
        .from('submission_options_for_consideration')
        .select('id, title, description');
      
      if (!ofcError && existingOfcs) {
        for (const ofc of ofcs) {
          const ofcText = `${ofc.title || ofc.option || ''} ${ofc.description || ''}`.trim();
          
          if (!ofcText) continue;
          
          let maxSimilarity = 0;
          let duplicate = null;
          
          for (const existing of existingOfcs) {
            const existingText = `${existing.title || ''} ${existing.description || ''}`.trim();
            const similarity = calculateSimilarity(ofcText, existingText);
            
            if (similarity > maxSimilarity && similarity >= 0.7) { // 70% similarity threshold
              maxSimilarity = similarity;
              duplicate = existing;
            }
          }
          
          if (duplicate) {
            duplicateResults.ofcs.push({
              submission_ofc: ofc,
              existing_ofc: duplicate,
              similarity: maxSimilarity,
              is_duplicate: true
            });
          } else {
            duplicateResults.ofcs.push({
              submission_ofc: ofc,
              is_duplicate: false
            });
          }
        }
      }
    }
    
    return NextResponse.json({
      success: true,
      duplicates: duplicateResults
    });
    
  } catch (e) {
    console.error('Error checking duplicates:', e);
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}

