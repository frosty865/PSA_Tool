'use client';
// Cache bust: v3.0 - Added submit button debugging and improved template
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/app/lib/supabase-client.js';
import { getCurrentUser, getUserProfile, canSubmitVOFC } from '../../lib/auth';
import { fetchSectors, fetchSubsectorsBySector } from '../../lib/fetchVOFC';
import SessionTimeoutWarning from '../../../components/SessionTimeoutWarning';

export default function BulkSubmission() {
  const [currentUser, setCurrentUser] = useState(null);
  const [userRole, setUserRole] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [csvData, setCsvData] = useState('');
  const [previewData, setPreviewData] = useState(null);
  const [validationErrors, setValidationErrors] = useState([]);
  const [showPreview, setShowPreview] = useState(false);
  const [sectors, setSectors] = useState([]);
  const [subsectors, setSubsectors] = useState([]);
  const [selectedSector, setSelectedSector] = useState('');
  const [selectedSubsector, setSelectedSubsector] = useState('');
  const [showBackToTop, setShowBackToTop] = useState(false);
  const [autocorrectResults, setAutocorrectResults] = useState([]);
  const [submitterEmail, setSubmitterEmail] = useState('');
  
  const router = useRouter();

  useEffect(() => {
    checkAuth();
    loadSectorsAndSubsectors();
  }, []);

  useEffect(() => {
    const handleScroll = () => {
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      setShowBackToTop(scrollTop > 300);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    if (selectedSector) {
      loadSubsectors(selectedSector);
    } else {
      setSubsectors([]);
      setSelectedSubsector('');
    }
  }, [selectedSector]);

  const checkAuth = async () => {
    try {
      const user = await getCurrentUser();
      if (!user) {
        router.push('/splash');
        return;
      }

      const profile = await getUserProfile(user.id);
      setCurrentUser(user);
      setUserRole(profile.role);

      if (!canSubmitVOFC(profile.role)) {
        router.push('/');
        return;
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      router.push('/splash');
    } finally {
      setLoading(false);
    }
  };

  const loadSectorsAndSubsectors = async () => {
    try {
      const sectorsData = await fetchSectors();
      setSectors(sectorsData);
    } catch (error) {
      console.error('Error loading sectors:', error);
    }
  };

  const loadSubsectors = async (sectorId) => {
    try {
      const subsectorsData = await fetchSubsectorsBySector(sectorId);
      setSubsectors(subsectorsData);
    } catch (error) {
      console.error('Error loading subsectors:', error);
      setSubsectors([]);
    }
  };

  const parseCSV = (csvText) => {
    const lines = csvText.trim().split('\n');
    
    // Detect delimiter - check if it's tab-separated or comma-separated
    const firstLine = lines[0];
    const hasTabs = firstLine.includes('\t');
    const hasCommas = firstLine.includes(',');
    
    let delimiter = ',';
    if (hasTabs && !hasCommas) {
      delimiter = '\t';
      console.log('Detected tab-separated format');
    } else if (hasCommas && !hasTabs) {
      delimiter = ',';
      console.log('Detected comma-separated format');
    } else if (hasTabs && hasCommas) {
      // If both exist, use the one that appears more frequently
      const tabCount = (firstLine.match(/\t/g) || []).length;
      const commaCount = (firstLine.match(/,/g) || []).length;
      delimiter = tabCount > commaCount ? '\t' : ',';
      console.log(`Detected mixed format, using ${delimiter === '\t' ? 'tab' : 'comma'} separator`);
    }
    
    const headers = firstLine.split(delimiter).map(h => h.trim().replace(/"/g, ''));
    console.log('CSV Headers detected:', headers);
    
    const data = [];
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i];
      if (!line.trim()) continue;
      
      console.log(`Parsing line ${i + 1}:`, line);
      
      // Handle CSV parsing with quoted fields
      const values = [];
      let current = '';
      let inQuotes = false;
      
      for (let j = 0; j < line.length; j++) {
        const char = line[j];
        
        if (char === '"') {
          inQuotes = !inQuotes;
        } else if (char === delimiter && !inQuotes) {
          values.push(current.trim());
          current = '';
        } else {
          current += char;
        }
      }
      values.push(current.trim());
      
      console.log(`Parsed values for line ${i + 1}:`, values);
      
      // Create object from headers and values
      const row = {};
      headers.forEach((header, index) => {
        let value = values[index] ? values[index].replace(/"/g, '') : '';
        
        // Fix character encoding issues
        value = value
          .replace(/â€"/g, '—')  // Fix corrupted em dash
          .replace(/â€™/g, "'")  // Fix corrupted apostrophe
          .replace(/â€œ/g, '"')  // Fix corrupted opening quote
          .replace(/â€/g, '"')   // Fix corrupted closing quote
          .replace(/â€¢/g, '•')  // Fix corrupted bullet point
          .replace(/â€"/g, '–')  // Fix corrupted en dash
          .replace(/â€¦/g, '…')  // Fix corrupted ellipsis
          .replace(/â€"/g, '')   // Fix other corrupted characters
          .replace(/""/g, '—')   // Fix double quotes that should be em dashes
          .replace(/""/g, '–')  // Fix double quotes that should be en dashes
          .trim();
        
        row[header] = value;
        console.log(`  ${header}: "${value}"`);
      });
      
      data.push(row);
    }
    
    console.log('Final parsed data:', data);
    return data;
  };

  const detectCSVIssues = (csvText) => {
    const issues = [];
    const lines = csvText.trim().split('\n');
    
    // Detect delimiter
    const firstLine = lines[0];
    const hasTabs = firstLine.includes('\t');
    const hasCommas = firstLine.includes(',');
    
    let delimiter = ',';
    if (hasTabs && !hasCommas) {
      delimiter = '\t';
    } else if (hasTabs && hasCommas) {
      const tabCount = (firstLine.match(/\t/g) || []).length;
      const commaCount = (firstLine.match(/,/g) || []).length;
      delimiter = tabCount > commaCount ? '\t' : ',';
    }
    
    // Check for common CSV issues
    lines.forEach((line, index) => {
      const lineNum = index + 1;
      
      // Check for unquoted fields with the detected delimiter (only for comma-separated)
      if (delimiter === ',' && line.includes(delimiter) && !line.includes('"')) {
        const parts = line.split(delimiter);
        if (parts.length > 4) { // More than expected fields
          issues.push(`Line ${lineNum}: Possible unquoted fields with commas - consider adding quotes around fields containing commas`);
        }
      }
      
      // Check for missing quotes around long text (only for comma-separated)
      if (delimiter === ',' && line.length > 100 && !line.includes('"')) {
        issues.push(`Line ${lineNum}: Long text without quotes - consider wrapping in quotes`);
      }
      
      // Check for inconsistent field counts
      if (index > 0) { // Skip header
        const expectedFields = lines[0].split(delimiter).length;
        const actualFields = line.split(delimiter).length;
        if (actualFields !== expectedFields) {
          issues.push(`Line ${lineNum}: Expected ${expectedFields} fields, found ${actualFields} - check for missing quotes or extra ${delimiter === '\t' ? 'tabs' : 'commas'}`);
        }
      }
    });
    
    return issues;
  };

  const autocorrectCSV = (data) => {
    const corrections = [];
    
    data.forEach((row, index) => {
      const rowNum = index + 2; // +2 because we start from line 2 (after header)
      
      // Autocorrect common field name issues
      const fieldMappings = {
        'category': 'Category',
        'vulnerability': 'Vulnerability', 
        'options for consideration': 'Options for Consideration',
        'options': 'Options for Consideration',
        'ofc': 'Options for Consideration',
        'sources': 'Sources',
        'source': 'Sources',
        'sector': 'Sector',
        'subsector': 'Subsector'
      };
      
      // Check for lowercase field names and suggest corrections
      Object.keys(fieldMappings).forEach(lowercase => {
        if (row[lowercase] && !row[fieldMappings[lowercase]]) {
          row[fieldMappings[lowercase]] = row[lowercase];
          delete row[lowercase];
          corrections.push(`Row ${rowNum}: Fixed field name "${lowercase}" → "${fieldMappings[lowercase]}"`);
        }
      });
      
      // Autocorrect common category names
      if (row['Category']) {
        const categoryCorrections = {
          'video security': 'Video Security Systems (Digital)',
          'video security systems': 'Video Security Systems (Digital)',
          'physical security': 'Physical Security',
          'cybersecurity': 'Cybersecurity',
          'access control': 'Access Control',
          'perimeter security': 'Perimeter Security',
          'information sharing': 'Information Sharing',
          'emergency management': 'Emergency Management'
        };
        
        const currentCategory = row['Category'].toLowerCase();
        if (categoryCorrections[currentCategory]) {
          const oldCategory = row['Category'];
          row['Category'] = categoryCorrections[currentCategory];
          corrections.push(`Row ${rowNum}: Fixed category "${oldCategory}" → "${categoryCorrections[currentCategory]}"`);
        }
      }
      
      // Autocorrect common vulnerability text issues
      if (row['Vulnerability']) {
        let vulnerability = row['Vulnerability'];
        
        // Fix common capitalization issues
        if (vulnerability.startsWith('the facility')) {
          vulnerability = vulnerability.charAt(0).toUpperCase() + vulnerability.slice(1);
        }
        
        // Fix common punctuation issues
        if (!vulnerability.endsWith('.') && !vulnerability.endsWith('!') && !vulnerability.endsWith('?')) {
          vulnerability += '.';
        }
        
        if (vulnerability !== row['Vulnerability']) {
          corrections.push(`Row ${rowNum}: Fixed vulnerability text formatting`);
          row['Vulnerability'] = vulnerability;
        }
      }
      
      // Autocorrect common OFC text issues
      if (row['Options for Consideration']) {
        let ofc = row['Options for Consideration'];
        
        // Fix bullet point formatting
        if (ofc.includes('•') || ofc.includes('-') || ofc.includes('*')) {
          ofc = ofc.replace(/[•\-*]\s*/g, '• ');
        }
        
        // Fix common capitalization
        if (ofc.startsWith('develop') || ofc.startsWith('implement') || ofc.startsWith('establish')) {
          ofc = ofc.charAt(0).toUpperCase() + ofc.slice(1);
        }
        
        if (ofc !== row['Options for Consideration']) {
          corrections.push(`Row ${rowNum}: Fixed OFC text formatting`);
          row['Options for Consideration'] = ofc;
        }
      }
    });
    
    return { data, corrections };
  };

  const convertDataToCSV = (data) => {
    if (!data || data.length === 0) return '';
    
    const headers = Object.keys(data[0]);
    const csvRows = [headers.join(',')];
    
    data.forEach(row => {
      const values = headers.map(header => {
        const value = row[header] || '';
        // Escape values that contain commas or quotes
        if (value.includes(',') || value.includes('"') || value.includes('\n')) {
          return `"${value.replace(/"/g, '""')}"`;
        }
        return value;
      });
      csvRows.push(values.join(','));
    });
    
    return csvRows.join('\n');
  };

  const validateCSVData = (data) => {
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
  };

  const handlePreview = () => {
    if (!csvData.trim()) {
      alert('Please paste CSV data first');
      return;
    }

    try {
      // First detect CSV formatting issues
      const csvIssues = detectCSVIssues(csvData);
      console.log('CSV Format Issues:', csvIssues);
      
      const parsedData = parseCSV(csvData);
      console.log('Parsed CSV data:', parsedData);
      
      // Apply autocorrect
      const { data: correctedData, corrections } = autocorrectCSV(parsedData);
      console.log('Autocorrect applied:', corrections);
      
      const errors = validateCSVData(correctedData);
      console.log('Validation errors:', errors);
      
      // Combine CSV issues with validation errors
      const allErrors = [...csvIssues, ...errors];
      
      setValidationErrors(allErrors);
      setPreviewData(correctedData);
      setAutocorrectResults(corrections);
      setShowPreview(true);
      
      // Show autocorrect results if any corrections were made
      if (corrections.length > 0) {
        console.log('✅ Autocorrect applied successfully:');
        corrections.forEach(correction => console.log(`  - ${correction}`));
      }
      
      // Show CSV format issues
      if (csvIssues.length > 0) {
        console.log('⚠️ CSV Format Issues detected:');
        csvIssues.forEach(issue => console.log(`  - ${issue}`));
      }
    } catch (error) {
      console.error('Error parsing CSV:', error);
      alert('Error parsing CSV data. Please check the format.');
    }
  };

  const handleSubmit = async () => {
    console.log('Submit button clicked');
    console.log('Validation errors:', validationErrors);
    console.log('Selected sector:', selectedSector);
    console.log('Show preview:', showPreview);
    
    if (validationErrors.length > 0) {
      alert('Please fix validation errors before submitting');
      return;
    }

    if (!selectedSector) {
      alert('Please select a sector');
      return;
    }

    setSubmitting(true);

    try {
      // Apply autocorrect to the CSV data before submitting
      const parsedData = parseCSV(csvData);
      const { data: correctedData, corrections } = autocorrectCSV(parsedData);
      
      // Convert corrected data back to CSV format for submission
      const correctedCSV = convertDataToCSV(correctedData);
      
      // Log autocorrect results
      if (corrections.length > 0) {
        console.log('✅ Autocorrect applied before submission:');
        corrections.forEach(correction => console.log(`  - ${correction}`));
      }
      
      const response = await fetch('/api/submissions/bulk', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          csvData: correctedCSV,
          submittedBy: currentUser.id,
          sectorId: selectedSector,
          subsectorId: selectedSubsector || null,
          submitterEmail: submitterEmail
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to submit');
      }

      const result = await response.json();
      alert(`Successfully created ${result.summary.total} submissions!`);
      
      // Reset form
      setCsvData('');
      setPreviewData(null);
      setShowPreview(false);
      setValidationErrors([]);
      setAutocorrectResults([]);
    } catch (error) {
      console.error('Error submitting:', error);
      alert('Error submitting: ' + error.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      <SessionTimeoutWarning />
      <div className="card">
        <div className="card-header">
          <h1 className="card-title">Bulk CSV Submission</h1>
          <p className="text-secondary">Upload multiple vulnerabilities and options for consideration via CSV</p>
        </div>

        <div className="card-body">
          <div className="alert alert-info mb-4">
            <h4 className="alert-heading">How to Use Bulk Submission</h4>
            <ol className="mb-0">
              <li><strong>Select sector and subsector</strong> for all submissions in this batch</li>
              <li><strong>Download the template</strong> using the button below to get the correct format</li>
              <li><strong>Fill in your data</strong> following the template structure</li>
              <li><strong>Copy and paste</strong> your completed CSV data into the text area</li>
              <li><strong>Preview</strong> to check for any validation errors</li>
              <li><strong>Submit</strong> when everything looks correct</li>
            </ol>
          </div>

          <div className="row mb-4">
            <div className="col-md-6">
              <label className="form-label">Sector <span className="text-danger">*</span></label>
              <select
                value={selectedSector}
                onChange={(e) => setSelectedSector(e.target.value)}
                className="form-select"
                required
              >
                <option value="">Select a sector...</option>
                {sectors.map((sector) => (
                  <option key={sector.id} value={sector.id}>
                    {sector.sector_name}
                  </option>
                ))}
              </select>
            </div>
            <div className="col-md-6">
              <label className="form-label">Subsector</label>
              <select
                value={selectedSubsector}
                onChange={(e) => setSelectedSubsector(e.target.value)}
                className="form-select"
                disabled={!selectedSector}
              >
                <option value="">Select a subsector...</option>
                {subsectors.map((subsector) => (
                  <option key={subsector.id} value={subsector.id}>
                    {subsector.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="mb-4">
            <div className="flex justify-between items-center mb-2">
              <label className="form-label">CSV Data</label>
              <a 
                href="/templates/vofc-bulk-template.csv" 
                download="vofc-bulk-template.csv"
                className="btn btn-sm btn-outline-primary"
              >
                <i className="fas fa-download mr-1"></i>
                Download Template
              </a>
            </div>
            <textarea
              value={csvData}
              onChange={(e) => setCsvData(e.target.value)}
              className="form-textarea"
              rows="10"
              placeholder="Paste your CSV data here..."
            />
                   <div className="text-sm text-secondary mt-2">
                     <strong>Required columns:</strong> Category, Vulnerability, Options for Consideration<br />
                     <strong>Optional columns:</strong> Sources, Sector, Subsector (if not provided, will use dropdown selections)<br />
                     <br />
                     <strong>Example format:</strong><br />
                     Category,Vulnerability,"Options for Consideration",Sources<br />
                     Physical Security,"Facility lacks perimeter fencing","Install perimeter fencing","DHS, 2023, Physical Security Guidelines, https://www.cisa.gov/physical-security"<br />
                     Physical Security,"Facility lacks perimeter fencing","Add security lighting","ASIS International, 2022, Physical Security Standards, https://www.asisonline.org/standards"<br />
                     <br />
                     <strong>Multiple OFCs per vulnerability:</strong> Use the same vulnerability text in multiple rows to group multiple options for consideration with one vulnerability.<br />
                     <br />
                     <strong>UAS & Counter-UAS Technologies:</strong> Include drone detection, authorized counter-UAS systems, radar systems, and AI-powered visual detection for unauthorized aerial systems. Note: RF jamming is illegal in most jurisdictions.<br />
              <br />
              <strong>Required fields:</strong> Category, Vulnerability, Options for Consideration<br />
              <strong>Optional fields:</strong> Sources<br />
              <strong>Minimum length:</strong> 10 characters for Vulnerability and Options for Consideration<br />
              <br />
              <strong>Source Citation Formats:</strong><br />
              • <strong>Government Documents:</strong> "DHS CISA, 2024, Counter-UAS Guidelines, https://www.cisa.gov/counter-uas"<br />
              • <strong>Standards:</strong> "NIST SP 800-63B, 2023, Digital Identity Guidelines, https://pages.nist.gov/800-63-3/"<br />
              • <strong>Industry Standards:</strong> "ASIS International, 2022, Physical Security Standards, https://www.asisonline.org/standards"<br />
              • <strong>Web Pages:</strong> "FAA, 2024, Counter-UAS Regulations, https://www.faa.gov/uas/counter-uas"<br />
              <br />
              <strong>Automatic assignments:</strong><br />
              • <strong>Discipline</strong> = Category from CSV<br />
              • <strong>Sector/Subsector</strong> = Mapped based on Category<br />
              • <strong>Record ID</strong> = Generated during approval<br />
              • <strong>Multiple OFCs</strong> = Automatically grouped with vulnerability<br />
              • <strong>Vulnerability-OFC Links</strong> = Created automatically during approval<br />
              <br />
              <strong>Common Categories:</strong> Physical Security (with sub-disciplines: Barriers and Fencing, Electronic Security Systems, Video Security Systems, Access Control Systems, Intrusion Detection Systems, Perimeter Security, Security Lighting, Physical Barriers, Security Hardware), Cybersecurity, Personnel Security, Operational Security, Information Security, Facility Information, Emergency Management, Risk Management, Training and Awareness
            </div>
          </div>

          <div className="flex gap-2 mb-4">
            <button
              onClick={handlePreview}
              disabled={!csvData.trim()}
              className="btn btn-secondary"
            >
              Preview Data
            </button>
            <button
              onClick={() => {
                setCsvData('');
                setPreviewData(null);
                setShowPreview(false);
                setValidationErrors([]);
                setAutocorrectResults([]);
              }}
              className="btn btn-outline-secondary"
            >
              Clear
            </button>
          </div>

          {autocorrectResults.length > 0 && (
            <div className="alert alert-info mb-4">
              <h4 className="alert-heading"><i className="fas fa-magic me-2"></i>Autocorrect Applied</h4>
              <ul className="mb-0">
                {autocorrectResults.map((correction, index) => (
                  <li key={index}>{correction}</li>
                ))}
              </ul>
            </div>
          )}

          {validationErrors.length > 0 && (
            <div className="alert alert-danger mb-4">
              <h4 className="alert-heading">Validation Errors</h4>
              <ul className="mb-0">
                {validationErrors.map((error, index) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            </div>
          )}

          {showPreview && previewData && (
            <div className="mb-4">
              <h3 className="text-lg font-semibold mb-2">Preview ({previewData.length} rows)</h3>
              <div className="table-responsive" style={{maxHeight: '500px', overflowY: 'auto'}}>
                <table className="table table-striped table-bordered table-sm">
                  <thead className="table-dark sticky-top">
                    <tr>
                      <th style={{width: '60px'}}>Row</th>
                      <th style={{width: '150px'}}>Category</th>
                      <th style={{width: '200px'}}>Vulnerability</th>
                      <th style={{width: '250px'}}>Options for Consideration</th>
                      <th style={{width: '200px'}}>Sources</th>
                      <th style={{width: '120px'}}>Sector</th>
                      <th style={{width: '120px'}}>Subsector</th>
                    </tr>
                  </thead>
                  <tbody>
                    {previewData.slice(0, 10).map((row, index) => (
                      <tr key={index}>
                        <td className="text-center">{index + 1}</td>
                        <td className="text-truncate" style={{maxWidth: '150px'}} title={row['Category'] || ''}>
                          {row['Category'] || ''}
                        </td>
                        <td className="text-truncate" style={{maxWidth: '200px'}} title={row['Vulnerability'] || ''}>
                          {row['Vulnerability'] || ''}
                        </td>
                        <td className="text-truncate" style={{maxWidth: '250px'}} title={row['Options for Consideration'] || ''}>
                          {row['Options for Consideration'] || ''}
                        </td>
                        <td className="text-truncate" style={{maxWidth: '200px'}} title={row['Sources'] || 'N/A'}>
                          {row['Sources'] || 'N/A'}
                        </td>
                        <td className="text-truncate" style={{maxWidth: '120px'}} title={row['Sector'] || (selectedSector ? sectors.find(s => s.id == selectedSector)?.sector_name || 'Selected' : 'Not selected')}>
                          {row['Sector'] || (selectedSector ? sectors.find(s => s.id == selectedSector)?.sector_name || 'Selected' : 'Not selected')}
                        </td>
                        <td className="text-truncate" style={{maxWidth: '120px'}} title={row['Subsector'] || (selectedSubsector ? subsectors.find(s => s.id == selectedSubsector)?.name || 'Selected' : 'Not selected')}>
                          {row['Subsector'] || (selectedSubsector ? subsectors.find(s => s.id == selectedSubsector)?.name || 'Selected' : 'Not selected')}
                        </td>
                      </tr>
                    ))}
                    {previewData.length > 10 && (
                      <tr>
                        <td colSpan="7" className="text-center text-secondary">
                          ... and {previewData.length - 10} more rows
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="mb-4">
            <label className="form-label">Your Email Address *</label>
            <input
              type="email"
              required
              value={submitterEmail}
              onChange={(e) => setSubmitterEmail(e.target.value)}
              className="form-input"
              placeholder="your.email@example.com"
            />
            <small className="text-secondary">We'll use this to notify you about your submission status</small>
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleSubmit}
              disabled={submitting || validationErrors.length > 0 || !showPreview || !submitterEmail}
              className="btn btn-primary"
            >
              {submitting ? 'Submitting...' : 'Submit All'}
            </button>
            <button
              onClick={() => router.push('/submit')}
              className="btn btn-outline-primary"
            >
              Single Submission
            </button>
          </div>
        </div>
      </div>

      {/* Back to Top Button */}
      {showBackToTop && (
        <button
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          className="back-to-top"
          title="Back to top"
        >
          <i className="fas fa-arrow-up"></i>
        </button>
      )}
    </div>
  );
}
