'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/app/lib/supabase-client.js';
import { getCurrentUser, getUserProfile, canSubmitVOFC } from '../lib/auth';
import { fetchSectors, fetchSubsectors, fetchSubsectorsBySector } from '../lib/fetchVOFC';
import SessionTimeoutWarning from '@/components/SessionTimeoutWarning';
import '@/styles/cisa.css';

export default function VOFCSubmission() {
  const [currentUser, setCurrentUser] = useState(null);
  const [userRole, setUserRole] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submissionType, setSubmissionType] = useState('vulnerability');
  const [sectors, setSectors] = useState([]);
  const [subsectors, setSubsectors] = useState([]);
  const [filteredSubsectors, setFilteredSubsectors] = useState([]);
  const [formData, setFormData] = useState({
    vulnerability: '',
    option_text: '',
    discipline: '',
    discipline_id: '',
    subdiscipline: '',
    discipline_subtype_id: '',
    source_citation: '',
    id: '',
    id: '',
    submitter_email: ''
  });
  const [options_for_consideration, setOfcs] = useState([]);
  const [currentOfc, setCurrentOfc] = useState('');
  const [citationStatus, setCitationStatus] = useState('');
  const [citationTimeout, setCitationTimeout] = useState(null);
  const [disciplines, setDisciplines] = useState([]);
  const [subtypes, setSubtypes] = useState([]);

  const router = useRouter();

  // Fetch disciplines from API
  useEffect(() => {
    const fetchDisciplines = async () => {
      try {
        const response = await fetch('/api/disciplines?active=true');
        const data = await response.json();
        if (data.success && data.disciplines) {
          // Filter to only the 10 new CISA-aligned disciplines
          const newDisciplines = data.disciplines.filter(d => d.is_active);
          setDisciplines(newDisciplines);
        }
      } catch (error) {
        console.error('Error fetching disciplines:', error);
      }
    };
    fetchDisciplines();
  }, []);

  // Fetch subtypes when discipline is selected
  useEffect(() => {
    const fetchSubtypes = async () => {
      if (formData.discipline_id) {
        try {
          const response = await fetch(`/api/disciplines/subtypes?discipline_id=${formData.discipline_id}&active=true`);
          const data = await response.json();
          if (data.success && data.subtypes) {
            setSubtypes(data.subtypes);
          } else {
            setSubtypes([]);
          }
        } catch (error) {
          console.error('Error fetching subtypes:', error);
          setSubtypes([]);
        }
      } else {
        setSubtypes([]);
      }
    };
    fetchSubtypes();
  }, [formData.discipline_id]);

  // Get sub-disciplines for selected discipline
  const getSubdisciplines = () => {
    return subtypes.map(st => st.name);
  };

  useEffect(() => {
    checkAuth();
    loadSectorsAndSubsectors();
    handleUrlParams();
  }, []);

  const handleUrlParams = () => {
    const urlParams = new URLSearchParams(window.location.search);
    const type = urlParams.get('type');
    const vulnerabilityId = urlParams.get('id');
    const discipline = urlParams.get('discipline');
    const sector = urlParams.get('sector');
    
    if (type) {
      setSubmissionType(type);
    }
    
    if (discipline) {
      setFormData(prev => ({ ...prev, discipline: decodeURIComponent(discipline) }));
    }
    
    // Find sector ID by name if provided
    if (sector && sectors.length > 0) {
      const foundSector = sectors.find(s => s.sector_name === decodeURIComponent(sector));
      if (foundSector) {
        setFormData(prev => ({ ...prev, id: foundSector.id }));
      }
    }
  };

  useEffect(() => {
    // Fetch subsectors when sector changes
    if (formData.id) {
      loadSubsectorsForSector(formData.id);
    } else {
      setFilteredSubsectors([]);
    }
  }, [formData.id]);

  useEffect(() => {
    // Handle URL params after sectors are loaded
    if (sectors.length > 0) {
      handleUrlParams();
    }
  }, [sectors]);

  const loadSectorsAndSubsectors = async () => {
    try {
      const sectorsData = await fetchSectors();
      setSectors(sectorsData);
    } catch (error) {
      console.error('Error loading sectors:', error);
    }
  };

  const loadSubsectorsForSector = async (sectorId) => {
    try {
      const subsectorsData = await fetchSubsectorsBySector(sectorId);
      setFilteredSubsectors(subsectorsData);
    } catch (error) {
      console.error('Error loading subsectors for sector:', error);
      setFilteredSubsectors([]);
    }
  };

  const assignCitation = async (sourceText) => {
    if (!sourceText || sourceText.trim() === '') {
      setCitationStatus('');
      return null;
    }

    try {
      setCitationStatus('Assigning citation...');
      const response = await fetch('/api/sources/assign-citation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ sourceText: sourceText.trim() }),
      });

      const result = await response.json();
      
      if (result.success) {
        setCitationStatus(`Citation assigned: ${result.citation} ${result.isNew ? '(new source)' : '(existing source)'}`);
        return result.citation;
      } else {
        setCitationStatus(`Error: ${result.error}`);
        return null;
      }
    } catch (error) {
      console.error('Citation assignment error:', error);
      setCitationStatus('Error assigning citation');
      return null;
    }
  };

  const handleSourceChange = (e) => {
    const value = e.target.value;
    setFormData({...formData, source_citation: value});
    
    // Clear existing timeout
    if (citationTimeout) {
      clearTimeout(citationTimeout);
    }
    
    // Set new timeout for citation assignment
    if (value.trim()) {
      const timeout = setTimeout(() => {
        assignCitation(value);
      }, 1000); // Wait 1 second after user stops typing
      setCitationTimeout(timeout);
    } else {
      setCitationStatus('');
    }
  };

  const addOfc = () => {
    if (currentOfc.trim()) {
      setOfcs([...options_for_consideration, currentOfc.trim()]);
      setCurrentOfc('');
    }
  };

  const removeOfc = (index) => {
    setOfcs(options_for_consideration.filter((_, i) => i !== index));
  };

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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      // Validate that vulnerabilities must have at least one option for consideration
      if (submissionType === 'vulnerability' && options_for_consideration.length === 0) {
        alert('Vulnerabilities must have at least one associated option for consideration.');
        setSubmitting(false);
        return;
      }

      // Assign citation if source is provided
      let citation = null;
      if (formData.source_citation && formData.source_citation.trim()) {
        citation = await assignCitation(formData.source_citation);
        if (!citation) {
          alert('Failed to assign citation. Please try again.');
          setSubmitting(false);
          return;
        }
      }
      if (submissionType === 'vulnerability' && options_for_consideration.length > 0) {
        // Submit vulnerability with associated OFCs
        const submissionData = {
          type: 'vulnerability',
          data: {
            vulnerability: formData.vulnerability,
            discipline: formData.discipline,
            discipline_id: formData.discipline_id || null,
            subdiscipline: formData.subdiscipline || null,
            discipline_subtype_id: formData.discipline_subtype_id || null,
            sources: citation,
            id: formData.id || null,
            id: formData.id || null,
            has_associated_ofcs: true,
            ofc_count: options_for_consideration.length,
            associated_ofcs: options_for_consideration
          },
          submitterEmail: formData.submitter_email,
          submitted_by: currentUser.id,
          status: 'pending'
        };

        const response = await fetch('/api/submissions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(submissionData),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || 'Failed to submit');
        }

        const result = await response.json();
        alert(`Vulnerability with ${options_for_consideration.length} associated OFCs submitted successfully! Submission ID: ${result.id}`);
      } else {
        // Submit single vulnerability or OFC
        const submissionData = {
          type: submissionType,
          data: submissionType === 'vulnerability' 
            ? {
                vulnerability: formData.vulnerability,
                discipline: formData.discipline,
                discipline_id: formData.discipline_id || null,
                subdiscipline: formData.subdiscipline || null,
                discipline_subtype_id: formData.discipline_subtype_id || null,
                sources: citation,
                id: formData.id || null,
                id: formData.id || null
              }
            : {
                option_text: formData.option_text,
                discipline: formData.discipline,
                discipline_id: formData.discipline_id || null,
                subdiscipline: formData.subdiscipline || null,
                discipline_subtype_id: formData.discipline_subtype_id || null,
                sources: citation,
                id: formData.id || null,
                id: formData.id || null
              },
          submitterEmail: formData.submitter_email,
          submitted_by: currentUser.id,
          status: 'pending'
        };

        const response = await fetch('/api/submissions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(submissionData),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || 'Failed to submit');
        }

        const result = await response.json();
        console.log('Submission response:', result);
        alert(`${submissionType === 'vulnerability' ? 'Vulnerability' : 'Option for Consideration'} submitted successfully! Submission ID: ${result.submission_id}`);
      }

      // Reset form
      setFormData({
        vulnerability: '',
        option_text: '',
        discipline: '',
        discipline_id: '',
        subdiscipline: '',
        discipline_subtype_id: '',
        source_citation: '',
        id: '',
        id: ''
      });
      setOfcs([]);
      setCurrentOfc('');
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
    <div className="max-w-4xl mx-auto">
      <SessionTimeoutWarning />
      <div className="card">
        <div className="card-header">
          <h1 className="card-title">Submit New Vulnerability</h1>
          <p className="text-secondary">Contribute vulnerabilities and options for consideration</p>
        </div>

        <div className="card-body">
          <div className="mb-4">
            <label className="form-label">Submission Type</label>
            <div className="flex gap-4">
              <label className="flex items-center">
                <input
                  type="radio"
                  name="submissionType"
                  value="vulnerability"
                  checked={submissionType === 'vulnerability'}
                  onChange={(e) => setSubmissionType(e.target.value)}
                  className="mr-2"
                />
                Vulnerability
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="submissionType"
                  value="ofc"
                  checked={submissionType === 'ofc'}
                  onChange={(e) => setSubmissionType(e.target.value)}
                  className="mr-2"
                />
                Option for Consideration (OFC)
              </label>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="form-group">
              <label className="form-label">
                {submissionType === 'vulnerability' ? 'Vulnerability Description' : 'Option Text'} *
              </label>
              <textarea
                required
                value={submissionType === 'vulnerability' ? formData.vulnerability : formData.option_text}
                onChange={(e) => setFormData({...formData, 
                  [submissionType === 'vulnerability' ? 'vulnerability' : 'option_text']: e.target.value
                })}
                className="form-textarea"
                rows="4"
                placeholder={submissionType === 'vulnerability' 
                  ? 'Describe the vulnerability...' 
                  : 'Describe the option for consideration...'}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Discipline *</label>
              <select
                required
                value={formData.discipline_id}
                onChange={(e) => {
                  const selectedDiscipline = disciplines.find(d => d.id === e.target.value);
                  setFormData({
                    ...formData, 
                    discipline_id: e.target.value,
                    discipline: selectedDiscipline?.name || '',
                    subdiscipline: '',
                    discipline_subtype_id: ''
                  });
                }}
                className="form-select"
              >
                <option value="">Select a discipline...</option>
                {disciplines.map(discipline => (
                  <option key={discipline.id} value={discipline.id}>
                    {discipline.name}
                  </option>
                ))}
              </select>
            </div>

            {formData.discipline_id && subtypes.length > 0 && (
              <div className="form-group">
                <label className="form-label">Sub-discipline</label>
                <select
                  value={formData.discipline_subtype_id}
                  onChange={(e) => {
                    const selectedSubtype = subtypes.find(st => st.id === e.target.value);
                    setFormData({
                      ...formData, 
                      discipline_subtype_id: e.target.value,
                      subdiscipline: selectedSubtype?.name || ''
                    });
                  }}
                  className="form-select"
                >
                  <option value="">Select a sub-discipline...</option>
                  {subtypes.map(subtype => (
                    <option key={subtype.id} value={subtype.id}>
                      {subtype.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="row">
              <div className="col-md-6">
                <div className="form-group">
                  <label className="form-label">Sector *</label>
                  <select
                    required
                    value={formData.id}
                    onChange={(e) => setFormData({...formData, id: e.target.value, id: ''})}
                    className="form-select"
                  >
                    <option value="">Select a sector...</option>
                    {sectors.map(sector => (
                      <option key={sector.id} value={sector.id}>
                        {sector.sector_name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="col-md-6">
                <div className="form-group">
                  <label className="form-label">Subsector</label>
                  <select
                    value={formData.id}
                    onChange={(e) => setFormData({...formData, id: e.target.value})}
                    className="form-select"
                    disabled={!formData.id}
                  >
                    <option value="">Select a subsector...</option>
                    {filteredSubsectors.map(subsector => (
                      <option key={subsector.id} value={subsector.id}>
                        {subsector.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Source Citation</label>
              <input
                type="text"
                value={formData.source_citation}
                onChange={handleSourceChange}
                className="form-input"
                placeholder="e.g., Walsh, T.J., and R.J. Healy, 2011, Protection of Assets: Security Management"
              />
              <small className="text-secondary">
                Enter the full source citation. The system will automatically assign a citation number.
              </small>
              {citationStatus && (
                <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded text-sm text-blue-800">
                  {citationStatus}
                </div>
              )}
            </div>

            <div className="form-group">
              <label className="form-label">Your Email Address *</label>
              <input
                type="email"
                required
                value={formData.submitter_email}
                onChange={(e) => setFormData({...formData, submitter_email: e.target.value})}
                className="form-input"
                placeholder="your.email@example.com"
              />
              <small className="text-secondary">We'll use this to notify you about your submission status</small>
            </div>

            {submissionType === 'vulnerability' && (
              <div className="form-group">
                <label className="form-label">Associated Options for Consideration *</label>
                <div className="mb-3">
                  <div className="flex gap-2">
                    <textarea
                      value={currentOfc}
                      onChange={(e) => setCurrentOfc(e.target.value)}
                      className="form-textarea flex-1"
                      rows="2"
                      placeholder="Add an option for consideration..."
                    />
                    <button
                      type="button"
                      onClick={addOfc}
                      disabled={!currentOfc.trim()}
                      className="btn btn-outline-primary"
                    >
                      <i className="fas fa-plus mr-1"></i>
                      Add OFC
                    </button>
                  </div>
                </div>
                
                {options_for_consideration.length > 0 && (
                  <div className="space-y-2">
                    <h5 className="text-sm font-semibold">Added OFCs ({options_for_consideration.length}):</h5>
                    {options_for_consideration.map((ofc, index) => (
                      <div key={index} className="flex items-start gap-2 p-2 bg-light border rounded">
                        <div className="flex-1 text-sm">{ofc}</div>
                        <button
                          type="button"
                          onClick={() => removeOfc(index)}
                          className="btn btn-sm btn-outline-danger"
                        >
                          <i className="fas fa-trash"></i>
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}


            <div className="flex gap-2">
              <button
                type="submit"
                disabled={submitting}
                className="btn btn-primary"
              >
                {submitting ? 'Submitting...' : 'Submit'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setFormData({
                    vulnerability: '',
                    option_text: '',
                    discipline: '',
                    subdiscipline: '',
                    source_citation: '',
                    id: '',
                    id: ''
                  });
                  setOfcs([]);
                  setCurrentOfc('');
                }}
                className="btn btn-secondary"
              >
                Clear Form
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}