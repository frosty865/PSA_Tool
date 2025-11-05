import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

// Function to parse CSV data
function parseCSV(csvText) {
  const lines = csvText.trim().split('\n');
  const headers = lines[0].split(',').map(h => h.trim().replace(/"/g, ''));
  
  const data = [];
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i];
    if (!line.trim()) continue;
    
    // Handle CSV parsing with quoted fields
    const values = [];
    let current = '';
    let inQuotes = false;
    
    for (let j = 0; j < line.length; j++) {
      const char = line[j];
      
      if (char === '"') {
        inQuotes = !inQuotes;
      } else if (char === ',' && !inQuotes) {
        values.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }
    values.push(current.trim());
    
    // Create object from headers and values
    const row = {};
    headers.forEach((header, index) => {
      row[header] = values[index] ? values[index].replace(/"/g, '') : '';
    });
    
    data.push(row);
  }
  
  return data;
}

// Function to validate CSV data
function validateCSVData(data) {
  const errors = [];
  const requiredFields = ['Category', 'Vulnerability', 'Options for Consideration'];
  const optionalFields = ['Sources', 'Sector', 'Subsector'];
  
  data.forEach((row, index) => {
    const rowNum = index + 2; // +2 because we start from line 2 (after header)
    
    // Check required fields
    requiredFields.forEach(field => {
      if (!row[field] || row[field].trim() === '') {
        errors.push(`Row ${rowNum}: Missing required field "${field}"`);
      }
    });
    
    // Check optional fields (silently note if missing - no console warnings needed)
    // These fields are optional and will use dropdown selections if empty
    
    // Check for minimum content length
    if (row['Vulnerability'] && row['Vulnerability'].length < 10) {
      errors.push(`Row ${rowNum}: Vulnerability description too short (minimum 10 characters)`);
    }
    
    if (row['Options for Consideration'] && row['Options for Consideration'].length < 10) {
      errors.push(`Row ${rowNum}: Options for consideration too short (minimum 10 characters)`);
    }
  });
  
  return errors;
}

// Function to map category to sector and subsector IDs
function mapCategoryToSector(category) {
  const categoryMapping = {
    'Physical Security': { sector_id: 2, subsector_id: null }, // Commercial Facilities
    'Physical Security Systems': { sector_id: 2, subsector_id: null }, // Commercial Facilities (electronic/mechanical/AI)
    'Cybersecurity': { sector_id: 13, subsector_id: null }, // Information Technology
    'Personnel Security': { sector_id: 2, subsector_id: null }, // Commercial Facilities
    'Operational Security': { sector_id: 2, subsector_id: null }, // Commercial Facilities
    'Information Security': { sector_id: 13, subsector_id: null }, // Information Technology
    'Facility Information': { sector_id: 2, subsector_id: null }, // Commercial Facilities
    'Emergency Management': { sector_id: 7, subsector_id: null }, // Emergency Services
    'Risk Management': { sector_id: 2, subsector_id: null }, // Commercial Facilities
    'Compliance': { sector_id: 2, subsector_id: null }, // Commercial Facilities
    'Training and Awareness': { sector_id: 2, subsector_id: null } // Commercial Facilities
  };
  
  return categoryMapping[category] || { sector_id: 2, subsector_id: null }; // Default to Commercial Facilities
}

// Function to group vulnerabilities with their OFCs
function groupVulnerabilitiesWithOFCs(csvData) {
  const grouped = {};
  
  csvData.forEach(row => {
    const category = row['Category'] || 'General';
    const vulnerability = row['Vulnerability']?.trim();
    const ofc = row['Options for Consideration']?.trim();
    const sources = row['Sources']?.trim() || '';
    
    if (vulnerability) {
      // Create a unique key based on vulnerability text and category
      const key = `${vulnerability}|${category}`;
      
      if (!grouped[key]) {
        grouped[key] = {
          vulnerability: vulnerability,
          category: category,
          sources: sources,
          ofcs: []
        };
      }
      
      if (ofc) {
        grouped[key].ofcs.push(ofc);
      }
    }
  });
  
  return Object.values(grouped);
}

// Function to create submissions for grouped data
function createGroupedSubmissions(groupedData, sectorId, subsectorId, submitterEmail) {
  const submissions = [];
  
  groupedData.forEach(group => {
    // Use form-provided sector/subsector instead of category mapping
    const finalSectorId = sectorId;
    const finalSubsectorId = subsectorId;
    
    // Create vulnerability submission
    submissions.push({
      type: 'vulnerability',
      data: JSON.stringify({
        vulnerability: group.vulnerability,
        discipline: group.category,
        source: group.sources,
        sector_id: finalSectorId,
        subsector_id: finalSubsectorId,
        // Add metadata to indicate this has associated OFCs
        has_associated_ofcs: group.ofcs.length > 0,
        ofc_count: group.ofcs.length,
        associated_ofcs: group.ofcs // Store OFCs for linking
      }),
      source: 'bulk_csv_grouped',
      status: 'pending_review',
      submitter_email: submitterEmail,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    });
    
    // Create OFC submissions for each option
    group.ofcs.forEach((ofc, index) => {
      submissions.push({
        type: 'ofc',
        data: JSON.stringify({
          option_text: ofc,
          discipline: group.category,
          source: group.sources,
          sector_id: finalSectorId,
          subsector_id: finalSubsectorId,
          // Add metadata to link back to vulnerability
          associated_vulnerability: group.vulnerability,
          ofc_sequence: index + 1,
          total_ofcs: group.ofcs.length
        }),
        source: 'bulk_csv_grouped',
        status: 'pending_review',
        submitter_email: submitterEmail,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      });
    });
  });
  
  return submissions;
}

export async function POST(request) {
  try {
    const { csvData, submittedBy, sectorId, subsectorId } = await request.json();
    
    if (!csvData || !submittedBy) {
      return NextResponse.json(
        { error: 'CSV data and submittedBy are required' },
        { status: 400 }
      );
    }

    if (!sectorId) {
      return NextResponse.json(
        { error: 'Sector selection is required' },
        { status: 400 }
      );
    }
    
    // Parse CSV data
    const parsedData = parseCSV(csvData);
    
    if (parsedData.length === 0) {
      return NextResponse.json(
        { error: 'No valid data found in CSV' },
        { status: 400 }
      );
    }
    
    // Validate CSV data
    const validationErrors = validateCSVData(parsedData);
    if (validationErrors.length > 0) {
      return NextResponse.json(
        { 
          error: 'Validation errors found',
          details: validationErrors
        },
        { status: 400 }
      );
    }
    
    // Group vulnerabilities with their OFCs
    const groupedData = groupVulnerabilitiesWithOFCs(parsedData);
    
    // Create submissions
    const submissions = createGroupedSubmissions(groupedData, sectorId, subsectorId, submitterEmail);
    
    if (submissions.length === 0) {
      return NextResponse.json(
        { error: 'No valid submissions could be created from CSV data' },
        { status: 400 }
      );
    }
    
    // Insert submissions into database
    const { data: insertedSubmissions, error } = await supabase
      .from('submissions')
      .insert(submissions)
      .select();
    
    if (error) {
      console.error('Error inserting submissions:', error);
      return NextResponse.json(
        { error: 'Failed to save submissions to database' },
        { status: 500 }
      );
    }
    
    // Calculate enhanced summary
    const summary = {
      total: insertedSubmissions.length,
      vulnerabilities: insertedSubmissions.filter(s => s.type === 'vulnerability').length,
      ofcs: insertedSubmissions.filter(s => s.type === 'ofc').length,
      grouped_vulnerabilities: groupedData.length,
      total_ofcs: groupedData.reduce((sum, group) => sum + group.ofcs.length, 0)
    };
    
    return NextResponse.json({
      success: true,
      message: `Successfully created ${insertedSubmissions.length} submissions`,
      summary: summary,
      submissionIds: insertedSubmissions.map(s => s.id),
      groupedData: groupedData.map(group => ({
        vulnerability: group.vulnerability,
        ofc_count: group.ofcs.length,
        category: group.category
      }))
    });
    
  } catch (error) {
    console.error('Error processing bulk CSV submission:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
