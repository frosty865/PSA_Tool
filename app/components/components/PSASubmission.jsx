"use client";

import { useState, useEffect } from "react";
import { useRouter } from 'next/navigation';
import { getCurrentUser, canSubmitVOFC } from '../lib/auth';
import { fetchWithAuth } from '../lib/fetchWithAuth';

export default function PSASubmission() {
  const [currentUser, setCurrentUser] = useState(null);
  const [userRole, setUserRole] = useState(null);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState({
    source_title: "",
    source_type: "unknown",
    source_url: "",
    author_org: "",
    publication_year: new Date().getFullYear(),
    content_restriction: "public",
    file: null
  });
  
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [parsing, setParsing] = useState(false);
  const [parsedData, setParsedData] = useState(null);
  const router = useRouter();

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const user = await getCurrentUser();
      if (!user) {
        router.push('/splash');
        return;
      }

      const canSubmit = await canSubmitVOFC();
      if (!canSubmit) {
        router.push('/login');
        return;
      }

      setCurrentUser(user);
      setUserRole(user.role);
    } catch (error) {
      console.error('Auth check failed:', error);
      router.push('/splash');
    } finally {
      setLoading(false);
    }
  };

  const sourceTypes = [
    { value: "government", label: "Government", description: "Federal, state, or local government documents" },
    { value: "academic", label: "Academic", description: "University research, studies, or papers" },
    { value: "corporate", label: "Corporate", description: "Industry reports, vendor documentation" },
    { value: "field_note", label: "Field Note", description: "Operational experience, lessons learned" },
    { value: "media", label: "Media", description: "News articles, press releases" },
    { value: "unknown", label: "Unknown", description: "Source type not specified" }
  ];

  const contentRestrictions = [
    { value: "public", label: "Public", description: "No restrictions, can be shared freely" },
    { value: "restricted", label: "Restricted", description: "Limited distribution, internal use" },
    { value: "confidential", label: "Confidential", description: "Sensitive information, authorized personnel only" },
    { value: "classified", label: "Classified", description: "Classified information, security clearance required" }
  ];

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (file) {
      // Validate file type
      const allowedTypes = ['.pdf', '.docx', '.txt', '.html', '.xlsx'];
      const fileExt = '.' + file.name.split('.').pop().toLowerCase();
      
      if (!allowedTypes.includes(fileExt)) {
        setMessage("❌ Unsupported file type. Please upload PDF, DOCX, TXT, HTML, or XLSX files.");
        return;
      }
      
      // Validate file size (10MB limit)
      if (file.size > 10 * 1024 * 1024) {
        setMessage("❌ File too large. Please upload files smaller than 10MB.");
        return;
      }
      
      setFormData(prev => ({
        ...prev,
        file: file
      }));
      setMessage("");
      
      // Parse document for auto-fill
      await parseDocument(file);
    }
  };

  const parseDocument = async (file) => {
    try {
      setParsing(true);
      setMessage("🔍 Analyzing document to auto-fill form fields...");
      
      // Create FormData for parsing
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch('/api/documents/parse-metadata', {
        method: 'POST',
        body: formData
      });
      
      const result = await response.json();
      
      if (result.success && result.parsedData) {
        setParsedData(result.parsedData);
        
        // Auto-populate form fields
        setFormData(prev => ({
          ...prev,
          source_title: result.parsedData.title || prev.source_title,
          author_org: result.parsedData.organization || prev.author_org,
          publication_year: result.parsedData.year || prev.publication_year,
          source_type: result.parsedData.sourceType || prev.source_type,
          source_url: result.parsedData.url || prev.source_url
        }));
        
        setMessage("✅ Document analyzed! Form fields have been auto-filled. Please review and adjust as needed.");
      } else {
        setMessage("⚠️ Could not auto-parse document. Please fill in the form fields manually.");
      }
    } catch (error) {
      console.error('Document parsing error:', error);
      setMessage("⚠️ Document parsing failed. Please fill in the form fields manually.");
    } finally {
      setParsing(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.file) {
      setMessage("❌ Please select a file to upload.");
      return;
    }
    
    if (!formData.source_title.trim()) {
      setMessage("❌ Please provide a source title.");
      return;
    }
    
    setSubmitting(true);
    setMessage("");
    
    try {
      // Create FormData for file upload
      const formDataToSend = new FormData();
      formDataToSend.append('file', formData.file);
      formDataToSend.append('source_title', formData.source_title);
      formDataToSend.append('source_type', formData.source_type);
      formDataToSend.append('source_url', formData.source_url);
      formDataToSend.append('author_org', formData.author_org);
      formDataToSend.append('publication_year', formData.publication_year.toString());
      formDataToSend.append('content_restriction', formData.content_restriction);
      
      // New pipeline: submit via tunnel endpoint which creates a submission and triggers process-one
      const response = await fetchWithAuth('/api/documents/submit', {
        method: 'POST',
        body: formDataToSend
      });
      
      const result = await response.json();
      
      if (result.success) {
        const submissionId = result.submission_id;
        setMessage(`✅ Document submitted! Submission ID: ${submissionId}. Processing has been triggered and results will appear after completion.`);
        setFormData({
          source_title: "",
          source_type: "unknown",
          source_url: "",
          author_org: "",
          publication_year: new Date().getFullYear(),
          content_restriction: "public",
          file: null
        });
        // Reset file input
        const fileInput = document.getElementById('file');
        if (fileInput) fileInput.value = '';
      } else {
        setMessage(`❌ Error: ${result.error}`);
      }
    } catch (error) {
      console.error('Submission error:', error);
      setMessage("❌ Error submitting document. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="content-wrapper">
          <div className="text-center py-8">
            <div className="loading"></div>
            <p className="text-secondary mt-3">Loading submission form...</p>
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
                PSA Document Submission
              </h1>
              <p className="card-subtitle">
                Submit documents containing security best practices or mitigations for automatic processing
              </p>
            </div>
            <div className="flex gap-3">
              <a href="/submit" className="btn btn-secondary">
                📝 Submit New Vulnerability
              </a>
              <a href="/profile" className="btn btn-secondary">
                👤 Profile
              </a>
            </div>
          </div>
        </div>

        {/* Information Card */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">What can you submit?</h2>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h3 className="font-semibold text-primary mb-2">Document Types</h3>
                <ul className="text-secondary space-y-1">
                  <li>• Government security guidelines and procedures</li>
                  <li>• Academic research on infrastructure protection</li>
                  <li>• Industry best practices and standards</li>
                </ul>
              </div>
              <div>
                <h3 className="font-semibold text-primary mb-2">Additional Sources</h3>
                <ul className="text-secondary space-y-1">
                  <li>• Field notes and operational lessons learned</li>
                  <li>• Vendor security documentation</li>
                  <li>• Any document with actionable security guidance</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          {/* File Upload - MOVED TO TOP */}
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">📄 Document Upload</h2>
              <p className="text-sm text-gray-600">Upload your document first to auto-fill the form fields</p>
            </div>
            <div className="card-body">
              <div className="form-group">
                <label htmlFor="file" className="form-label">
                  Select Document *
                </label>
                <input
                  type="file"
                  id="file"
                  name="file"
                  onChange={handleFileChange}
                  accept=".pdf,.docx,.txt,.html,.xlsx"
                  required
                  className="form-input"
                />
                <p className="form-help">
                  Supported formats: PDF, DOCX, TXT, HTML, XLSX (max 10MB)
                </p>
                {parsing && (
                  <div className="mt-2 flex items-center text-blue-600">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                    <span className="text-sm">Analyzing document...</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Document Information */}
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">📋 Document Information</h2>
              <p className="text-sm text-gray-600">Review and adjust the auto-filled information</p>
            </div>
            <div className="card-body">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="form-group">
                  <label htmlFor="source_title" className="form-label">
                    Document Title *
                    {parsedData?.title && formData.source_title === parsedData.title && (
                      <span className="ml-2 text-xs bg-green-100 text-green-800 px-2 py-1 rounded">Auto-filled</span>
                    )}
                  </label>
                  <input
                    type="text"
                    id="source_title"
                    name="source_title"
                    value={formData.source_title}
                    onChange={handleInputChange}
                    required
                    className={`form-input ${parsedData?.title && formData.source_title === parsedData.title ? 'border-green-300 bg-green-50' : ''}`}
                    placeholder="e.g., Stadium Security Best Practices"
                  />
                </div>
                
                <div className="form-group">
                  <label htmlFor="source_type" className="form-label">
                    Source Type *
                  </label>
                  <select
                    id="source_type"
                    name="source_type"
                    value={formData.source_type}
                    onChange={handleInputChange}
                    className="form-select"
                  >
                    {sourceTypes.map(type => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                  <p className="form-help">
                    {sourceTypes.find(t => t.value === formData.source_type)?.description}
                  </p>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                <div className="form-group">
                  <label htmlFor="author_org" className="form-label">
                    Authoring Organization
                    {parsedData?.organization && formData.author_org === parsedData.organization && (
                      <span className="ml-2 text-xs bg-green-100 text-green-800 px-2 py-1 rounded">Auto-filled</span>
                    )}
                  </label>
                  <input
                    type="text"
                    id="author_org"
                    name="author_org"
                    value={formData.author_org}
                    onChange={handleInputChange}
                    className={`form-input ${parsedData?.organization && formData.author_org === parsedData.organization ? 'border-green-300 bg-green-50' : ''}`}
                    placeholder="e.g., Department of Homeland Security"
                  />
                </div>
                
                <div className="form-group">
                  <label htmlFor="publication_year" className="form-label">
                    Publication Year
                    {parsedData?.year && formData.publication_year === parsedData.year && (
                      <span className="ml-2 text-xs bg-green-100 text-green-800 px-2 py-1 rounded">Auto-filled</span>
                    )}
                  </label>
                  <input
                    type="number"
                    id="publication_year"
                    name="publication_year"
                    value={formData.publication_year}
                    onChange={handleInputChange}
                    min="1900"
                    max={new Date().getFullYear()}
                    className={`form-input ${parsedData?.year && formData.publication_year === parsedData.year ? 'border-green-300 bg-green-50' : ''}`}
                  />
                </div>
              </div>
              
              <div className="form-group mt-4">
                <label htmlFor="source_url" className="form-label">
                  Source URL (Optional)
                </label>
                <input
                  type="url"
                  id="source_url"
                  name="source_url"
                  value={formData.source_url}
                  onChange={handleInputChange}
                  className="form-input"
                  placeholder="https://example.com/document"
                />
              </div>
            </div>
          </div>

          {/* Content Classification */}
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Content Classification</h2>
            </div>
            <div className="card-body">
              <div className="form-group">
                <label htmlFor="content_restriction" className="form-label">
                  Content Restriction Level *
                </label>
                <select
                  id="content_restriction"
                  name="content_restriction"
                  value={formData.content_restriction}
                  onChange={handleInputChange}
                  className="form-select"
                >
                  {contentRestrictions.map(restriction => (
                    <option key={restriction.value} value={restriction.value}>
                      {restriction.label}
                    </option>
                  ))}
                </select>
                <p className="form-help">
                  {contentRestrictions.find(r => r.value === formData.content_restriction)?.description}
                </p>
              </div>
            </div>
          </div>


          {/* Submission */}
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Review & Submit</h2>
            </div>
            <div className="card-body">
              <div className="alert alert-warning">
                <h3 className="font-semibold mb-2">Before submitting:</h3>
                <ul className="text-sm space-y-1">
                  <li>• Ensure the document contains actionable security guidance</li>
                  <li>• Verify the source is reputable and authoritative</li>
                  <li>• Confirm the content restriction level is appropriate</li>
                  <li>• Check that no classified or sensitive information is included</li>
                </ul>
              </div>
              
              {message && (
                <div className={`alert ${message.startsWith('✅') ? 'alert-success' : 'alert-error'} mb-4`}>
                  {message}
                </div>
              )}
              
              <div className="flex justify-end gap-3">
                <a href="/submit" className="btn btn-secondary">
                  Cancel
                </a>
                <button
                  type="submit"
                  disabled={submitting}
                  className="btn btn-primary"
                >
                  {submitting ? (
                    <>
                      <div className="loading loading-sm mr-2"></div>
                      Submitting...
                    </>
                  ) : (
                    'Submit Document for Processing'
                  )}
                </button>
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
