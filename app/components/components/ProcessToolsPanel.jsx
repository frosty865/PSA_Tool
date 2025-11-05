'use client';
import { useState } from 'react';

export default function ProcessToolsPanel({ onClose }) {
  const [activeTab, setActiveTab] = useState('parse-pdf');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const callTool = async (endpoint, data) => {
    setLoading(true);
    setError(null);
    setResults(null);
    
    try {
      const response = await fetch(`/api/tools/${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `Tool error: ${response.status}`);
      }

      const result = await response.json();
      setResults(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleParsePDF = () => {
    const pdfPath = document.getElementById('pdf-path').value;
    if (!pdfPath) {
      setError('Please enter a PDF path');
      return;
    }
    callTool('parse-pdf', { pdfPath });
  };

  const handleNormalizeData = () => {
    const jsonPath = document.getElementById('json-path').value;
    if (!jsonPath) {
      setError('Please enter a JSON path');
      return;
    }
    callTool('normalize-data', { jsonPath });
  };

  const handleLinkToSupabase = () => {
    const jsonPath = document.getElementById('link-json-path').value;
    if (!jsonPath) {
      setError('Please enter a JSON path');
      return;
    }
    callTool('link-to-supabase', { jsonPath });
  };

  const handleRunAnalysis = () => {
    const jarPath = document.getElementById('jar-path').value;
    const args = document.getElementById('java-args').value.split(',').map(arg => arg.trim()).filter(arg => arg);
    if (!jarPath) {
      setError('Please enter a JAR path');
      return;
    }
    callTool('run-analysis', { jarPath, args });
  };

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex justify-end">
      <div className="relative p-8 border w-full md:w-1/2 lg:w-1/3 shadow-lg rounded-l-lg bg-white flex flex-col">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-2xl font-bold text-gray-900">Process Tools</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700 text-2xl">
            &times;
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8" aria-label="Tabs">
            <button
              onClick={() => setActiveTab('parse-pdf')}
              className={`${
                activeTab === 'parse-pdf'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-3 px-1 border-b-2 font-medium text-sm`}
            >
              Parse PDF
            </button>
            <button
              onClick={() => setActiveTab('normalize')}
              className={`${
                activeTab === 'normalize'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-3 px-1 border-b-2 font-medium text-sm`}
            >
              Normalize Data
            </button>
            <button
              onClick={() => setActiveTab('link')}
              className={`${
                activeTab === 'link'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-3 px-1 border-b-2 font-medium text-sm`}
            >
              Link to DB
            </button>
            <button
              onClick={() => setActiveTab('analysis')}
              className={`${
                activeTab === 'analysis'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-3 px-1 border-b-2 font-medium text-sm`}
            >
              Run Analysis
            </button>
          </nav>
        </div>

        {/* Tab Content */}
        <div className="flex-1">
          {activeTab === 'parse-pdf' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  PDF File Path
                </label>
                <input
                  id="pdf-path"
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="/path/to/document.pdf"
                />
              </div>
              <button
                onClick={handleParsePDF}
                disabled={loading}
                className="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Parsing...' : 'Parse PDF'}
              </button>
            </div>
          )}

          {activeTab === 'normalize' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  JSON File Path
                </label>
                <input
                  id="json-path"
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="/path/to/data.json"
                />
              </div>
              <button
                onClick={handleNormalizeData}
                disabled={loading}
                className="w-full bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                {loading ? 'Normalizing...' : 'Normalize Data'}
              </button>
            </div>
          )}

          {activeTab === 'link' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  JSON File Path
                </label>
                <input
                  id="link-json-path"
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="/path/to/normalized-data.json"
                />
              </div>
              <button
                onClick={handleLinkToSupabase}
                disabled={loading}
                className="w-full bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700 disabled:opacity-50"
              >
                {loading ? 'Linking...' : 'Link to Supabase'}
              </button>
            </div>
          )}

          {activeTab === 'analysis' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  JAR File Path
                </label>
                <input
                  id="jar-path"
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="/path/to/analysis.jar"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Arguments (comma-separated)
                </label>
                <input
                  id="java-args"
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="arg1, arg2, arg3"
                />
              </div>
              <button
                onClick={handleRunAnalysis}
                disabled={loading}
                className="w-full bg-orange-600 text-white px-4 py-2 rounded-md hover:bg-orange-700 disabled:opacity-50"
              >
                {loading ? 'Running...' : 'Run Analysis'}
              </button>
            </div>
          )}
        </div>

        {/* Results */}
        {error && (
          <div className="mt-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
            <strong>Error:</strong> {error}
          </div>
        )}

        {results && (
          <div className="mt-4 p-4 bg-green-100 border border-green-400 text-green-700 rounded">
            <strong>Success!</strong>
            <pre className="mt-2 text-xs overflow-auto max-h-40">
              {JSON.stringify(results, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
