'use client';
import { useState } from 'react';

export default function AIToolsPanel({ vulnerability, onClose }) {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('analyze');

  const callAITool = async (endpoint, data) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/ai-tools/${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error(`AI tool error: ${response.status}`);
      }

      const result = await response.json();
      setResults(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const analyzeVulnerability = () => {
    callAITool('analyze-vulnerability', {
      vulnerabilityText: vulnerability.vulnerability,
      discipline: vulnerability.discipline
    });
  };

  const generateOFCs = () => {
    callAITool('generate-ofcs', {
      vulnerabilityText: vulnerability.vulnerability,
      discipline: vulnerability.discipline,
      count: 3
    });
  };

  const testConnection = () => {
    callAITool('test-connection', {});
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="bg-blue-600 text-white p-4 flex justify-between items-center">
          <h2 className="text-xl font-semibold">AI Tools - {vulnerability.discipline}</h2>
          <button
            onClick={onClose}
            className="text-white hover:text-gray-200 text-2xl"
          >
            ×
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b">
          <div className="flex">
            <button
              onClick={() => setActiveTab('analyze')}
              className={`px-4 py-2 ${activeTab === 'analyze' ? 'bg-blue-50 text-blue-600 border-b-2 border-blue-600' : 'text-gray-600'}`}
            >
              Analyze Vulnerability
            </button>
            <button
              onClick={() => setActiveTab('generate')}
              className={`px-4 py-2 ${activeTab === 'generate' ? 'bg-blue-50 text-blue-600 border-b-2 border-blue-600' : 'text-gray-600'}`}
            >
              Generate OFCs
            </button>
            <button
              onClick={() => setActiveTab('test')}
              className={`px-4 py-2 ${activeTab === 'test' ? 'bg-blue-50 text-blue-600 border-b-2 border-blue-600' : 'text-gray-600'}`}
            >
              Test Connection
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Vulnerability Context */}
          <div className="mb-6 p-4 bg-gray-50 rounded-lg">
            <h3 className="font-semibold mb-2">Vulnerability Context:</h3>
            <p className="text-sm text-gray-700">{vulnerability.vulnerability}</p>
            <span className="inline-block mt-2 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
              {vulnerability.discipline}
            </span>
          </div>

          {/* Action Buttons */}
          <div className="mb-6">
            {activeTab === 'analyze' && (
              <button
                onClick={analyzeVulnerability}
                disabled={loading}
                className="btn bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Analyzing...' : 'Analyze Vulnerability'}
              </button>
            )}

            {activeTab === 'generate' && (
              <button
                onClick={generateOFCs}
                disabled={loading}
                className="btn bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
              >
                {loading ? 'Generating...' : 'Generate New OFCs'}
              </button>
            )}

            {activeTab === 'test' && (
              <button
                onClick={testConnection}
                disabled={loading}
                className="btn bg-gray-600 text-white hover:bg-gray-700 disabled:opacity-50"
              >
                {loading ? 'Testing...' : 'Test Ollama Connection'}
              </button>
            )}
          </div>

          {/* Loading State */}
          {loading && (
            <div className="text-center py-8">
              <div className="text-blue-600 text-lg mb-2">🤖 AI is working...</div>
              <div className="text-gray-600">This may take a few moments</div>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
              <div className="text-red-800 font-semibold">Error:</div>
              <div className="text-red-700">{error}</div>
            </div>
          )}

          {/* Results */}
          {results && !loading && (
            <div className="space-y-4">
              {results.success ? (
                <div>
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
                    <div className="text-green-800 font-semibold">✅ AI Analysis Complete</div>
                  </div>

                  {/* Vulnerability Analysis Results */}
                  {results.analysis && (
                    <div className="card p-4">
                      <h4 className="font-semibold mb-3">Vulnerability Analysis</h4>
                      
                      {results.analysis.clarity_score && (
                        <div className="mb-3">
                          <div className="text-sm text-gray-600">Clarity Score: {results.analysis.clarity_score}/10</div>
                          <div className="text-sm text-gray-600">Specificity Score: {results.analysis.specificity_score}/10</div>
                        </div>
                      )}

                      {results.analysis.improvements && results.analysis.improvements.length > 0 && (
                        <div className="mb-3">
                          <div className="font-semibold text-sm mb-2">Suggested Improvements:</div>
                          <ul className="list-disc list-inside text-sm text-gray-700">
                            {results.analysis.improvements.map((improvement, index) => (
                              <li key={index}>{improvement}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {results.analysis.enhanced_text && (
                        <div className="mb-3">
                          <div className="font-semibold text-sm mb-2">Enhanced Text:</div>
                          <div className="bg-blue-50 p-3 rounded text-sm text-gray-700">
                            {results.analysis.enhanced_text}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Generated OFCs */}
                  {results.ofcs && results.ofcs.length > 0 && (
                    <div className="card p-4">
                      <h4 className="font-semibold mb-3">Generated OFCs</h4>
                      <div className="space-y-3">
                        {results.ofcs.map((ofc, index) => (
                          <div key={index} className="bg-gray-50 p-3 rounded">
                            <div className="font-semibold text-sm mb-1">OFC {index + 1}:</div>
                            <div className="text-sm text-gray-700 mb-2">{ofc.option_text}</div>
                            <div className="flex gap-2 text-xs">
                              <span className="badge">{ofc.priority}</span>
                              <span className="badge">{ofc.implementation_difficulty}</span>
                              <span className="badge">{ofc.estimated_cost}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Connection Test Results */}
                  {results.response && (
                    <div className="card p-4">
                      <h4 className="font-semibold mb-3">Connection Test</h4>
                      <div className="text-green-600">✅ {results.response}</div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="text-red-800">❌ AI Analysis Failed</div>
                  <div className="text-red-700 text-sm mt-1">{results.error}</div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
