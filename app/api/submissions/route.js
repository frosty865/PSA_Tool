import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/app/lib/supabase-admin.js';
import { ollamaChatJSON } from '@/lib/ollama.js';

export async function POST(request) {
  try {
    const data = await request.json();
    const { type, vulnerability, option_text, discipline, subdiscipline, sources, source_title, source_url } = data;

    // Validate required fields
    if (!type || (type === 'vulnerability' && !vulnerability) || (type === 'ofc' && !option_text)) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      );
    }

    // Create submission record
    const submissionData = {
      type,
      data: JSON.stringify(data),
      status: 'pending_review',
      source: 'api_submission',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    const { data: submission, error: submissionError } = await supabaseAdmin
      .from('submissions')
      .insert([submissionData])
      .select()
      .single();

    if (submissionError) {
      console.error('Submission creation error:', submissionError);
      return NextResponse.json(
        { error: 'Failed to create submission' },
        { status: 500 }
      );
    }

    console.log('✅ Submission created:', submission.id);

    // Create content for Ollama processing
    let content = `Source: ${source_title || 'Submission Document'}\n`;
    content += `URL: ${source_url || 'N/A'}\n`;
    content += `Type: ${type}\n\n`;
    
    if (type === 'vulnerability') {
      content += `Vulnerability: ${vulnerability}\n`;
      content += `Discipline: ${discipline}\n`;
      content += `Sources: ${sources || 'N/A'}\n`;
    } else if (type === 'ofc') {
      content += `Option for Consideration: ${option_text}\n`;
      content += `Discipline: ${discipline}\n`;
      content += `Sources: ${sources || 'N/A'}\n`;
    }

    // Save to docs folder for document processor
    const fs = require('fs');
    const path = require('path');
    
    const docsDir = path.join(process.cwd(), 'data', 'docs');
    if (!fs.existsSync(docsDir)) {
      fs.mkdirSync(docsDir, { recursive: true });
    }
    
    const docsFile = path.join(docsDir, `submission_${submission.id.slice(0, 8)}.txt`);
    fs.writeFileSync(docsFile, content);
    console.log('📄 Document saved to docs folder for processing:', docsFile);

    // Update submission status to processing
    await supabaseAdmin
      .from('submissions')
      .update({
        status: 'processing',
        updated_at: new Date().toISOString()
      })
      .eq('id', submission.id);

    // Run Ollama API using the new utility
    try {
      console.log('🤖 Running Ollama API for document analysis...');
      console.log(`📊 Processing submission ${submission.id} with Ollama...`);
      
      const prompt = `You are an expert document analyzer for the VOFC (Vulnerability and Options for Consideration) Engine. 
Your task is to extract vulnerabilities and options for consideration from security documents.

Extract the following information:
1. Vulnerabilities: Security weaknesses, risks, or threats mentioned in the document
2. Options for Consideration (OFCs): Mitigation strategies, recommendations, or actions to address vulnerabilities

Return your analysis as a JSON object with this structure:
{
  "vulnerabilities": [
    {
      "id": "unique_id",
      "text": "vulnerability description",
      "discipline": "relevant discipline",
      "source": "source information"
    }
  ],
  "options_for_consideration": [
    {
      "id": "unique_id", 
      "text": "OFC description",
      "discipline": "relevant discipline",
      "source": "source information"
    }
  ]
}

Document Content:
${content}

Please provide a structured JSON response with vulnerabilities and OFCs.`;

      // Use the new Ollama utility
      const parsedResult = await ollamaChatJSON({
        model: 'mistral:latest',
        prompt,
        temperature: 0.1,
        top_p: 0.9
      });

      if (!parsedResult) {
        throw new Error('Ollama returned null response');
      }

      console.log('✅ Ollama analysis completed successfully');
      
      const ofcCount = parsedResult.options_for_consideration?.length || 0;
      const vulnCount = parsedResult.vulnerabilities?.length || 0;
      
      console.log(`📊 OFCs found: ${ofcCount}`);
      console.log(`📊 Vulnerabilities found: ${vulnCount}`);
      
      // Determine discipline based on content analysis
      let discipline = data.discipline || 'General';
      let subdiscipline = data.subdiscipline || null;
      
      if (data.source_title?.toLowerCase().includes('security')) {
        discipline = 'Physical Security';
        // Try to determine sub-discipline for Physical Security
        if (!subdiscipline) {
          const content = (data.vulnerability || data.option_text || '').toLowerCase();
          if (content.includes('fence') || content.includes('barrier') || content.includes('gate')) {
            subdiscipline = 'Barriers and Fencing';
          } else if (content.includes('camera') || content.includes('video') || content.includes('cctv')) {
            subdiscipline = 'Video Security Systems';
          } else if (content.includes('access control') || content.includes('card reader') || content.includes('biometric')) {
            subdiscipline = 'Access Control Systems';
          } else if (content.includes('alarm') || content.includes('sensor') || content.includes('detector')) {
            subdiscipline = 'Electronic Security Systems';
          } else if (content.includes('lighting') || content.includes('illumination')) {
            subdiscipline = 'Security Lighting';
          } else if (content.includes('lock') || content.includes('hardware')) {
            subdiscipline = 'Security Hardware';
          } else {
            subdiscipline = 'Physical Barriers'; // Default
          }
        }
      } else if (data.source_title?.toLowerCase().includes('cyber')) {
        discipline = 'Cybersecurity';
      } else if (data.source_title?.toLowerCase().includes('emergency')) {
        discipline = 'Emergency Management';
      } else if (data.source_title?.toLowerCase().includes('planning')) {
        discipline = 'Risk Management';
      } else if (data.source_title?.toLowerCase().includes('response')) {
        discipline = 'Emergency Management';
      }
      
      // Update the submission with enhanced parsing results and metadata
      const enhancedData = {
        ...data,
        discipline: data.discipline || discipline,
        subdiscipline: data.subdiscipline || subdiscipline,
        sources: data.sources || data.source_url || 'Document Analysis',
        source_title: data.source_title || 'Submission Document',
        source_url: data.source_url || null,
        enhanced_extraction: parsedResult,
        parsed_at: new Date().toISOString(),
        parser_version: 'ollama_api_v1.0',
        extraction_stats: {
          ofc_count: ofcCount,
          vulnerability_count: vulnCount
        },
        ofc_count: ofcCount,
        vulnerability_count: vulnCount
      };

      const { error: updateError } = await supabase
        .from('submissions')
        .update({
          data: JSON.stringify(enhancedData),
          updated_at: new Date().toISOString()
        })
        .eq('id', submission.id);

      if (updateError) {
        console.error('❌ Error updating submission with parsing results:', updateError);
        // Update status to failed
        await supabaseAdmin
          .from('submissions')
          .update({
            status: 'processing_failed',
            updated_at: new Date().toISOString()
          })
          .eq('id', submission.id);
      } else {
        console.log('✅ Submission updated with Ollama API results');
        // Update status back to pending_review for manual review
        await supabaseAdmin
          .from('submissions')
          .update({
            status: 'pending_review',
            updated_at: new Date().toISOString()
          })
          .eq('id', submission.id);
      }
      
    } catch (ollamaError) {
      console.error('❌ Ollama API processing failed:', ollamaError);
      console.log('⚠️ Skipping automatic processing due to Ollama error');
      
      // Update status to failed
      await supabaseAdmin
        .from('submissions')
        .update({
          status: 'processing_failed',
          updated_at: new Date().toISOString()
        })
        .eq('id', submission.id);
    }

    return NextResponse.json({
      success: true,
      submission_id: submission.id,
      status: submission.status,
      message: 'Submission created and processed with Ollama API'
    });

  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
