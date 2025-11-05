'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser } from '../../lib/auth';
import { fetchWithAuth } from '../../lib/fetchWithAuth';

export default function OFCManagement() {
  const router = useRouter();
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [ofcs, setOfcs] = useState([]);
  const [filteredOfcs, setFilteredOfcs] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDiscipline, setSelectedDiscipline] = useState('');
  const [disciplines, setDisciplines] = useState([]);
  const [dataLoading, setDataLoading] = useState(false);
  const [error, setError] = useState('');
  const [editingOFC, setEditingOFC] = useState(null);
  const [editText, setEditText] = useState('');
  const [currentUser, setCurrentUser] = useState(null);
  const [mounted, setMounted] = useState(false);

  const checkAuth = async () => {
    try {
      const user = await getCurrentUser();
      if (user) {
        setAuthenticated(true);
        setCurrentUser(user);
      } else {
        router.push('/splash');
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      router.push('/splash');
    } finally {
      setLoading(false);
    }
  };

  const loadOFCs = async () => {
    try {
      setDataLoading(true);
      
      // Fetch OFCs from the API
      const response = await fetchWithAuth('/api/admin/ofcs', {
        method: 'GET'
      });

      if (!response.ok) {
        throw new Error('Failed to fetch OFCs');
      }

      const data = await response.json();
      setOfcs(data || []);
      setFilteredOfcs(data || []);
      
      // Extract unique disciplines
      const uniqueDisciplines = [...new Set(data?.map(ofc => ofc.discipline).filter(Boolean) || [])];
      setDisciplines(uniqueDisciplines.sort());
      
    } catch (error) {
      console.error('Error loading OFCs:', error);
      setError('Failed to load OFC data. Please try again.');
    } finally {
      setDataLoading(false);
    }
  };

  const handleEdit = (ofc) => {
    setEditingOFC(ofc);
    setEditText(ofc.option_text || '');
  };

  const handleSave = async () => {
    if (!editingOFC || !editText.trim()) return;
    
    try {
      const response = await fetchWithAuth('/api/admin/ofcs', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id: editingOFC.id,
          option_text: editText.trim()
        })
      });

      const result = await response.json();
      if (result.success) {
        // Update the local state
        setOfcs(ofcs.map(ofc => 
          ofc.id === editingOFC.id 
            ? { ...ofc, option_text: editText.trim() }
            : ofc
        ));
        setFilteredOfcs(filteredOfcs.map(ofc => 
          ofc.id === editingOFC.id 
            ? { ...ofc, option_text: editText.trim() }
            : ofc
        ));
        setEditingOFC(null);
        setEditText('');
      } else {
        alert(`Failed to update OFC: ${result.error}`);
      }
    } catch (error) {
      console.error('Error updating OFC:', error);
      alert('Error updating OFC. Please try again.');
    }
  };

  const handleDelete = async (ofcId) => {
    if (!confirm('Are you sure you want to delete this OFC?')) return;
    
    try {
      const response = await fetchWithAuth('/api/admin/ofcs', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id: ofcId })
      });

      const result = await response.json();
      if (result.success) {
        // Remove from local state
        setOfcs(ofcs.filter(ofc => ofc.id !== ofcId));
        setFilteredOfcs(filteredOfcs.filter(ofc => ofc.id !== ofcId));
      } else {
        alert(`Failed to delete OFC: ${result.error}`);
      }
    } catch (error) {
      console.error('Error deleting OFC:', error);
      alert('Error deleting OFC. Please try again.');
    }
  };

  useEffect(() => {
    setMounted(true);
    checkAuth();
  }, []);

  useEffect(() => {
    if (authenticated) {
      loadOFCs();
    }
  }, [authenticated]);

  useEffect(() => {
    let filtered = ofcs;

    if (searchTerm) {
      filtered = filtered.filter(ofc => 
        ofc.option_text?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        ofc.discipline?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (selectedDiscipline) {
      filtered = filtered.filter(ofc => ofc.discipline === selectedDiscipline);
    }

    setFilteredOfcs(filtered);
  }, [ofcs, searchTerm, selectedDiscipline]);

  if (!mounted) {
    return (
      <div className="page-container">
        <div className="content-wrapper">
          <div className="text-center py-8">
            <div className="loading"></div>
            <p className="text-secondary mt-3">Loading OFC Management...</p>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="page-container">
        <div className="content-wrapper">
          <div className="text-center py-8">
            <div className="loading"></div>
            <p className="text-secondary mt-3">Loading OFC Management...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="content-wrapper">
          <div className="error-message">
            {error}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="content-wrapper">
        {/* Header */}
        <div className="card-header">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="card-title">
                OFC Management
              </h1>
              <p className="card-subtitle">
                Showing {filteredOfcs.length} of {ofcs.length} Options for Consideration
              </p>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Filters</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Search */}
            <div className="form-group">
              <label className="form-label" htmlFor="search-input">
                Search
              </label>
              <input
                id="search-input"
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search OFCs..."
                className="form-input"
              />
            </div>

            {/* Discipline */}
            <div className="form-group">
              <label className="form-label" htmlFor="discipline-select">
                Discipline
              </label>
              <select
                id="discipline-select"
                value={selectedDiscipline}
                onChange={(e) => setSelectedDiscipline(e.target.value)}
                className="form-select"
              >
                <option value="">All Disciplines</option>
                {disciplines.map(discipline => (
                  <option key={discipline} value={discipline}>
                    {discipline}
                  </option>
                ))}
              </select>
            </div>

            {/* Clear Filters */}
            <div className="form-group">
              <label className="form-label">&nbsp;</label>
              <button
                onClick={() => {
                  setSearchTerm('');
                  setSelectedDiscipline('');
                }}
                className="btn btn-secondary w-full"
              >
                Clear Filters
              </button>
            </div>
          </div>
        </div>

        {/* Data Loading State */}
        {dataLoading && (
          <div className="card text-center">
            <div className="loading"></div>
            <p className="text-secondary mt-3">Loading OFC data...</p>
          </div>
        )}

        {/* OFCs List */}
        <div className="space-y-4">
          {filteredOfcs.length === 0 ? (
            <div className="card text-center py-8">
              <div className="text-secondary text-lg">
                {ofcs.length === 0 
                  ? "No OFCs found in database."
                  : "No OFCs found matching your filters"
                }
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredOfcs.map((ofc) => (
                <div key={ofc.id} className="card">
                  <div className="card-header">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        {editingOFC?.id === ofc.id ? (
                          <div className="space-y-3">
                            <textarea
                              value={editText}
                              onChange={(e) => setEditText(e.target.value)}
                              className="form-input w-full"
                              rows="3"
                            />
                            <div className="flex gap-2">
                              <button
                                onClick={handleSave}
                                className="btn btn-success btn-sm"
                              >
                                Save
                              </button>
                              <button
                                onClick={() => {
                                  setEditingOFC(null);
                                  setEditText('');
                                }}
                                className="btn btn-secondary btn-sm"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div>
                            <h3 className="card-title">
                              {ofc.option_text || `OFC ${ofc.id}`}
                            </h3>
                            {ofc.discipline && (
                              <span className="status-badge status-processing">
                                {ofc.discipline}
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                      <div className="ml-4 flex gap-2">
                        <button
                          onClick={() => handleEdit(ofc)}
                          className="btn btn-primary btn-sm"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(ofc.id)}
                          className="btn btn-danger btn-sm"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}