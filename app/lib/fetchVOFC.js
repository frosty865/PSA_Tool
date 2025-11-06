/**
 * VOFC Fetching Functions - Optimized with proper relationships
 */

// Use singleton Supabase client to avoid multiple instances
import { supabase } from './supabase-client.js';

// Database Schema Discovery Function - Query actual column information
export async function discoverDatabaseSchema() {
  try {
    // Query information_schema to get actual column names
    const { data: columns, error: columnsError } = await supabase
      .rpc('get_table_columns', {
        table_names: ['vulnerabilities', 'options_for_consideration', 'sources', 'vulnerability_ofc_links', 'ofc_sources', 'sectors', 'subsectors']
      });
    
    if (columnsError) {
      // Fallback: query each table directly to get column names
      const tables = [
        'vulnerabilities',
        'options_for_consideration', 
        'sources',
        'vulnerability_ofc_links',
        'ofc_sources',
        'sectors',
        'subsectors'
      ];
      
      const schema = {};
      
      for (const table of tables) {
        try {
          const { data, error } = await supabase
            .from(table)
            .select('*')
            .limit(1);
            
          if (error) {
            schema[table] = { error: error.message };
          } else {
            if (data && data.length > 0) {
              schema[table] = {
                exists: true,
                columns: Object.keys(data[0]),
                sampleData: data[0]
              };
            } else {
              schema[table] = {
                exists: true,
                columns: [],
                sampleData: null
              };
            }
          }
        } catch (err) {
          schema[table] = { error: err.message };
        }
      }
      
      return schema;
    } else {
      return columns;
    }
  } catch (error) {
    console.error('Error discovering schema:', error);
    return {};
  }
}

export async function fetchVOFC() {
  try {
    // Ensure user is authenticated before making queries
    const { data: { session }, error: sessionError } = await supabase.auth.getSession();
    
    if (sessionError || !session) {
      console.warn('No authenticated session for fetchVOFC');
      return [];
    }

    // Use basic select to see what columns actually exist
    const { data, error } = await supabase
      .from('options_for_consideration')
      .select('*');

    if (error) {
      console.error('Supabase error:', error);
      // If RLS error, return empty array gracefully instead of throwing
      if (error.code === '42501' || error.code === 'PGRST301') {
        console.warn('RLS policy blocking access to options_for_consideration table');
        return [];
      }
      // For other errors, also return empty array instead of throwing
      return [];
    }

    return data || [];
  } catch (error) {
    console.error('Error in fetchVOFC:', error);
    // Don't throw - return empty array instead
    return [];
  }
}

export async function linkOFCtoSource(ofcId, referenceNumber) {
  // 1️⃣ Find the source UUID by its reference number
  const { data: source, error: sourceError } = await supabase
    .from('sources')
    .select('id')
    .eq('"reference number"', referenceNumber)
    .single();

  if (sourceError || !source) throw sourceError || new Error('Source not found');

  // 2️⃣ Link it to the OFC (duplicate-safe because of unique constraint)
  const { error: linkError } = await supabase
    .from('ofc_sources')
    .insert([{ ofc_id: ofcId, source_id: source.id }])
    .select();

  if (linkError && !linkError.message.includes('duplicate key')) throw linkError;

  return { success: true };
}


// Fixed fetchSubsectors function
export async function fetchSubsectors() {
  try {
    const { data, error } = await supabase
      .from('subsectors')
      .select('*')
      .order('name');

    if (error) {
      console.error('Error fetching subsectors:', error);
      return [];
    }

    return data || [];
  } catch (error) {
    console.error('Error in fetchSubsectors:', error);
    return [];
  }
}

// Direct sources table query to see its columns
export async function fetchSources() {
  try {
    const { data, error } = await supabase
      .from('sources')
      .select('*')
      .limit(1);

    if (error) {
      console.error('Error fetching sources:', error);
      return [];
    }

    return data || [];
  } catch (error) {
    console.error('Error in fetchSources:', error);
    return [];
  }
}

// Get vulnerability text by ID
export async function getVulnerabilityText(vulnerabilityId) {
  try {
    const { data, error } = await supabase
      .from('vulnerabilities')
      .select('*')
      .eq('id', vulnerabilityId)
      .single();

    if (error) {
      console.error('Error fetching vulnerability text:', error);
      return null;
    }

    return data;
  } catch (error) {
    console.error('Error in getVulnerabilityText:', error);
    return null;
  }
}

// Fetch subsectors by sector ID
export async function fetchSubsectorsBySector(sectorId) {
  try {
    if (!sectorId) {
      console.warn('[fetchSubsectorsBySector] No sectorId provided');
      return [];
    }

    console.log(`[fetchSubsectorsBySector] Fetching subsectors for sectorId: ${sectorId}`);
    
    const { data, error } = await supabase
      .from('subsectors')
      .select('id, name, sector_id, description')
      .eq('sector_id', sectorId)
      .order('name');

    if (error) {
      console.error('[fetchSubsectorsBySector] Error:', error);
      console.error('[fetchSubsectorsBySector] Error details:', {
        code: error.code,
        message: error.message,
        details: error.details,
        hint: error.hint
      });
      // If RLS error, return empty array gracefully instead of throwing
      if (error.code === '42501' || error.code === 'PGRST301') {
        console.warn('[fetchSubsectorsBySector] RLS policy blocking access - this may be expected');
      }
      return [];
    }
    
    console.log(`[fetchSubsectorsBySector] Successfully fetched ${data?.length || 0} subsectors`);
    return data || [];
  } catch (error) {
    console.error('[fetchSubsectorsBySector] Exception:', error);
    return [];
  }
}

// Fetch vulnerabilities with their linked OFCs using manual joins
export async function fetchVulnerabilities() {
  try {
    // Ensure user is authenticated before making queries
    const { data: { session }, error: sessionError } = await supabase.auth.getSession();
    
    if (sessionError || !session) {
      console.warn('No authenticated session for fetchVulnerabilities');
      return [];
    }

    // Get all vulnerabilities
    const { data: vulnerabilities, error: vulnError } = await supabase
      .from('vulnerabilities')
      .select('*')
      .order('created_at', { ascending: false });

    if (vulnError) {
      console.error('❌ Error fetching vulnerabilities:', vulnError);
      // If RLS error, return empty array gracefully
      if (vulnError.code === '42501' || vulnError.code === 'PGRST301') {
        console.warn('RLS policy blocking access to vulnerabilities table');
        return [];
      }
      return [];
    }

    // Get all vulnerability-OFC links
    const { data: links, error: linkError } = await supabase
      .from('vulnerability_ofc_links')
      .select('*');

    if (linkError) {
      console.error('❌ Error fetching vulnerability-OFC links:', linkError);
      if (linkError.code === '42501' || linkError.code === 'PGRST301') {
        console.warn('RLS policy blocking access to vulnerability_ofc_links table');
        return vulnerabilities || [];
      }
      return vulnerabilities || [];
    }

    // Get all OFCs
    const { data: ofcs, error: ofcError } = await supabase
      .from('options_for_consideration')
      .select('*');

    if (ofcError) {
      console.error('❌ Error fetching OFCs:', ofcError);
      if (ofcError.code === '42501' || ofcError.code === 'PGRST301') {
        console.warn('RLS policy blocking access to options_for_consideration table');
        return vulnerabilities || [];
      }
      return vulnerabilities || [];
    }

    // Get all OFC-Source links
    const { data: ofcSources, error: ofcSourceError } = await supabase
      .from('ofc_sources')
      .select('*');

    if (ofcSourceError) {
      console.error('❌ Error fetching OFC-Source links:', ofcSourceError);
      console.warn('⚠️  Continuing without OFC sources due to error');
      // Don't return early - continue with empty ofcSources
    }

    console.log(`[fetchVulnerabilities] Found ${ofcSources?.length || 0} OFC-Source links`);

    // Get all sources
    const { data: sources, error: sourceError } = await supabase
      .from('sources')
      .select('*');

    if (sourceError) {
      console.error('❌ Error fetching sources:', sourceError);
      console.warn('⚠️  Continuing without sources due to error');
      // Don't return early - continue with empty sources array
    }

    console.log(`[fetchVulnerabilities] Found ${sources?.length || 0} sources`);


    // Build the complete data structure
    const vulnerabilitiesWithOFCs = vulnerabilities.map(vuln => {
      const vulnLinks = links.filter(link => link.vulnerability_id === vuln.id);
      
      const ofcsWithSources = vulnLinks.map(link => {
        const ofc = ofcs.find(o => o.id === link.ofc_id);
        if (!ofc) return null;
        
        const ofcSourceLinks = (ofcSources || []).filter(os => os.ofc_id === ofc.id);
        let ofcSourcesData = ofcSourceLinks.map(sourceLink => 
          (sources || []).find(s => s.id === sourceLink.source_id)
        ).filter(Boolean);
        
        // Fallback: If no sources linked via junction table, check if OFC has source info directly
        // Some OFCs might have source info stored in their own fields (from submission data)
        if (ofcSourcesData.length === 0 && (ofc.source || ofc.source_title || ofc.source_url)) {
          // Create a source object from OFC's own source fields
          ofcSourcesData = [{
            id: null, // No source ID since it's not in sources table
            source_title: ofc.source_title || ofc.source || 'Source',
            source_url: ofc.source_url || null,
            citation: ofc.source || null,
            author_org: null,
            publication_year: null
          }];
          console.log(`[fetchVulnerabilities] OFC ${ofc.id} using direct source fields (no junction table link)`);
        }
        
        // Debug logging
        if (ofcSourceLinks.length > 0) {
          console.log(`[fetchVulnerabilities] OFC ${ofc.id} has ${ofcSourceLinks.length} source links, found ${ofcSourcesData.length} sources`);
        } else if (ofcSourcesData.length > 0) {
          console.log(`[fetchVulnerabilities] OFC ${ofc.id} using direct source fields`);
        } else {
          console.log(`[fetchVulnerabilities] OFC ${ofc.id} has no source links and no direct source fields`);
        }
        
        return {
          ...ofc,
          sources: ofcSourcesData
        };
      }).filter(Boolean);

      return {
        ...vuln,
        ofcs: ofcsWithSources
      };
    });

    return vulnerabilitiesWithOFCs || [];
  } catch (error) {
    console.error('Error in fetchVulnerabilities:', error);
    return [];
  }
}

// Additional functions needed by the dashboard
// Get OFCs for a specific vulnerability
export async function getOFCsForVulnerability(vulnerabilityId) {
  try {
    // Get vulnerability-OFC links
    const { data: links, error: linkError } = await supabase
      .from('vulnerability_ofc_links')
      .select('*')
      .eq('vulnerability_id', vulnerabilityId);

    if (linkError) {
      console.error('Error fetching vulnerability OFC links:', linkError);
      return [];
    }

    if (!links || links.length === 0) {
      return [];
    }

    // Get all OFCs linked to this vulnerability
    const ofcIds = links.map(link => link.ofc_id);
    const { data: ofcs, error: ofcError } = await supabase
      .from('options_for_consideration')
      .select('*')
      .in('id', ofcIds);

    if (ofcError) {
      console.error('Error fetching OFC details:', ofcError);
      return [];
    }

    // Get all OFC-Source links for these OFCs
    const { data: ofcSources, error: ofcSourceError } = await supabase
      .from('ofc_sources')
      .select('*')
      .in('ofc_id', ofcIds);

    if (ofcSourceError) {
      console.warn('Error fetching OFC-Source links:', ofcSourceError);
      // Continue without sources if this fails
    }

    // Get all sources linked to these OFCs
    let sources = [];
    if (ofcSources && ofcSources.length > 0) {
      const sourceIds = ofcSources.map(os => os.source_id);
      const { data: sourcesData, error: sourceError } = await supabase
        .from('sources')
        .select('*')
        .in('id', sourceIds);

      if (sourceError) {
        console.warn('Error fetching sources:', sourceError);
      } else {
        sources = sourcesData || [];
      }
    }

    // Build OFCs with their sources attached
    const ofcsWithSources = ofcs.map(ofc => {
        const ofcSourceLinks = (ofcSources || []).filter(os => os.ofc_id === ofc.id);
        let ofcSourcesData = ofcSourceLinks.map(sourceLink => 
          sources.find(s => s.id === sourceLink.source_id)
        ).filter(Boolean);

        // Fallback: If no sources linked via junction table, check if OFC has source info directly
        if (ofcSourcesData.length === 0 && (ofc.source || ofc.source_title || ofc.source_url)) {
          ofcSourcesData = [{
            id: null,
            source_title: ofc.source_title || ofc.source || 'Source',
            source_url: ofc.source_url || null,
            citation: ofc.source || null,
            author_org: null,
            publication_year: null
          }];
        }

        return {
          ...ofc,
          sources: ofcSourcesData
        };
    });

    return ofcsWithSources;
  } catch (error) {
    console.error('Error in getOFCsForVulnerability:', error);
    return [];
  }
}

export async function fetchVulnerabilityOFCLinks() {
  try {
    const { data, error } = await supabase
      .from('vulnerability_ofc_links')
      .select('*');

    if (error) {
      console.error('Error fetching vulnerability OFC links:', error);
      return [];
    }

    return data || [];
  } catch (error) {
    console.error('Error in fetchVulnerabilityOFCLinks:', error);
    return [];
  }
}

export async function fetchSectors() {
  try {
    console.log('[fetchSectors] Fetching sectors from database...');
    
    // Check authentication status
    const { data: { session } } = await supabase.auth.getSession();
    console.log('[fetchSectors] Session status:', session ? 'authenticated' : 'not authenticated');
    
    // Try with all possible column combinations
    let data = null;
    let error = null;
    
    // Try: select all columns first
    const result = await supabase
      .from('sectors')
      .select('*')
      .order('id');
    
    data = result.data;
    error = result.error;

    if (error) {
      console.error('[fetchSectors] Error:', error);
      console.error('[fetchSectors] Error details:', {
        code: error.code,
        message: error.message,
        details: error.details,
        hint: error.hint
      });
      
      // If RLS error or access denied, try with explicit columns
      if (error.code === '42501' || error.code === 'PGRST301' || error.code === '42P01') {
        console.warn('[fetchSectors] Access error - trying with explicit column selection...');
        const altResult = await supabase
          .from('sectors')
          .select('id, name, description')
          .order('id');
        
        if (!altResult.error) {
          data = altResult.data;
          error = null;
        }
      }
      
      if (error) {
        return [];
      }
    }

    console.log(`[fetchSectors] Query successful - fetched ${data?.length || 0} sectors`);
    
    if (data && data.length > 0) {
      console.log('[fetchSectors] Sample sector:', data[0]);
      // Normalize sector_name - use sector_name if it exists, otherwise name
      return data.map(s => ({
        ...s,
        sector_name: s.sector_name || s.name || `Sector ${s.id}`
      }));
    } else {
      console.warn('[fetchSectors] Sectors table appears to be empty or RLS is filtering all rows');
      console.warn('[fetchSectors] This could mean:');
      console.warn('[fetchSectors]   1. The sectors table is empty');
      console.warn('[fetchSectors]   2. RLS policies are filtering all rows');
      console.warn('[fetchSectors]   3. The user does not have permission to read sectors');
      return [];
    }
  } catch (error) {
    console.error('[fetchSectors] Exception:', error);
    return [];
  }
}

// Fetch disciplines
export async function fetchDisciplines() {
  try {
    const { data, error } = await supabase
      .from('disciplines')
      .select('*')
      .eq('is_active', true)
      .order('category, name');

    if (error) {
      console.error('Error fetching disciplines:', error);
      return [];
    }

    return data || [];
  } catch (error) {
    console.error('Error in fetchDisciplines:', error);
    return [];
  }
}

// Fetch disciplines by category
export async function fetchDisciplinesByCategory(category) {
  try {
    const { data, error } = await supabase
      .from('disciplines')
      .select('*')
      .eq('category', category)
      .eq('is_active', true)
      .order('name');

    if (error) {
      console.error('Error fetching disciplines by category:', error);
      return [];
    }

    return data || [];
  } catch (error) {
    console.error('Error in fetchDisciplinesByCategory:', error);
    return [];
  }
}

// No mock data - all data comes from the database











