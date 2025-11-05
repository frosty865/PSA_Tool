'use client';

import { useState, useEffect } from 'react';

export default function ProcessFlowDiagram() {
  const [flowData, setFlowData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadFlowData();
  }, []);

  const loadFlowData = async () => {
    try {
      const response = await fetch('/api/monitor/process-flow');
      const data = await response.json();
      
      if (data.success) {
        setFlowData(data.flow);
      }
    } catch (error) {
      console.error('Error loading flow data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow-lg">
      <h3 className="text-lg font-semibold mb-4">PSA Tool Processing Flow</h3>
      
      {/* Main Process Flow */}
      <div className="relative">
        {/* Flow Steps */}
        <div className="flex justify-between items-center mb-8">
          {/* Step 1: Document Upload */}
          <div className="text-center">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-2">
              <i className="fas fa-upload text-blue-600 text-xl"></i>
            </div>
            <p className="text-sm font-medium">Document Upload</p>
            <p className="text-xs text-gray-600">User submits document</p>
            <div className="mt-1 text-xs text-green-600">✅ Active</div>
          </div>
          
          <div className="flex-1 h-1 bg-blue-200 mx-4 relative">
            <div className="absolute inset-0 bg-blue-500 rounded-full animate-pulse"></div>
          </div>
          
          {/* Step 2: File Processing */}
          <div className="text-center">
            <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-2">
              <i className="fas fa-file-alt text-yellow-600 text-xl"></i>
            </div>
            <p className="text-sm font-medium">File Processing</p>
            <p className="text-xs text-gray-600">Document saved to docs/</p>
            <div className="mt-1 text-xs text-green-600">✅ Active</div>
          </div>
          
          <div className="flex-1 h-1 bg-yellow-200 mx-4 relative">
            <div className="absolute inset-0 bg-yellow-500 rounded-full animate-pulse"></div>
          </div>
          
          {/* Step 3: Ollama Analysis */}
          <div className="text-center">
            <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-2">
              <i className="fas fa-brain text-purple-600 text-xl"></i>
            </div>
            <p className="text-sm font-medium">AI Analysis</p>
            <p className="text-xs text-gray-600">Ollama processes content</p>
            <div className="mt-1 text-xs text-yellow-600">⏳ Processing</div>
          </div>
          
          <div className="flex-1 h-1 bg-purple-200 mx-4 relative">
            <div className="absolute inset-0 bg-purple-500 rounded-full animate-pulse"></div>
          </div>
          
          {/* Step 4: Data Extraction */}
          <div className="text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-2">
              <i className="fas fa-search text-green-600 text-xl"></i>
            </div>
            <p className="text-sm font-medium">Data Extraction</p>
            <p className="text-xs text-gray-600">Vulnerabilities & OFCs</p>
            <div className="mt-1 text-xs text-blue-600">🔄 Queued</div>
          </div>
          
          <div className="flex-1 h-1 bg-green-200 mx-4 relative">
            <div className="absolute inset-0 bg-green-500 rounded-full animate-pulse"></div>
          </div>
          
          {/* Step 5: Database Storage */}
          <div className="text-center">
            <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-2">
              <i className="fas fa-database text-indigo-600 text-xl"></i>
            </div>
            <p className="text-sm font-medium">Database Storage</p>
            <p className="text-xs text-gray-600">Results stored</p>
            <div className="mt-1 text-xs text-green-600">✅ Complete</div>
          </div>
        </div>

        {/* Detailed Process Steps */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
            <h4 className="font-medium text-sm mb-2 text-blue-900">1. Document Reception</h4>
            <ul className="text-xs text-blue-800 space-y-1">
              <li>• File validation</li>
              <li>• Size checking</li>
              <li>• Format verification</li>
              <li>• Security scanning</li>
            </ul>
            <div className="mt-2 text-xs text-green-600">✅ Active</div>
          </div>
          
          <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
            <h4 className="font-medium text-sm mb-2 text-yellow-900">2. File Processing</h4>
            <ul className="text-xs text-yellow-800 space-y-1">
              <li>• Text extraction</li>
              <li>• Content parsing</li>
              <li>• Metadata extraction</li>
              <li>• Format conversion</li>
            </ul>
            <div className="mt-2 text-xs text-green-600">✅ Active</div>
          </div>
          
          <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
            <h4 className="font-medium text-sm mb-2 text-purple-900">3. AI Analysis</h4>
            <ul className="text-xs text-purple-800 space-y-1">
              <li>• Ollama processing</li>
              <li>• Content analysis</li>
              <li>• Pattern recognition</li>
              <li>• Context understanding</li>
            </ul>
            <div className="mt-2 text-xs text-yellow-600">⏳ Processing</div>
          </div>
          
          <div className="bg-green-50 p-4 rounded-lg border border-green-200">
            <h4 className="font-medium text-sm mb-2 text-green-900">4. Data Extraction</h4>
            <ul className="text-xs text-green-800 space-y-1">
              <li>• Vulnerability detection</li>
              <li>• OFC identification</li>
              <li>• Source attribution</li>
              <li>• Confidence scoring</li>
            </ul>
            <div className="mt-2 text-xs text-blue-600">🔄 Queued</div>
          </div>
          
          <div className="bg-indigo-50 p-4 rounded-lg border border-indigo-200">
            <h4 className="font-medium text-sm mb-2 text-indigo-900">5. Database Storage</h4>
            <ul className="text-xs text-indigo-800 space-y-1">
              <li>• Supabase insertion</li>
              <li>• Relationship mapping</li>
              <li>• Index updating</li>
              <li>• Status tracking</li>
            </ul>
            <div className="mt-2 text-xs text-green-600">✅ Complete</div>
          </div>
        </div>

        {/* Process Metrics */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-50 p-4 rounded-lg">
            <h5 className="font-medium text-sm mb-2">Processing Queue</h5>
            <div className="text-2xl font-bold text-blue-600">{flowData?.queue_size || 0}</div>
            <div className="text-xs text-gray-600">Documents waiting</div>
          </div>
          
          <div className="bg-gray-50 p-4 rounded-lg">
            <h5 className="font-medium text-sm mb-2">Active Processing</h5>
            <div className="text-2xl font-bold text-yellow-600">{flowData?.active_processing || 0}</div>
            <div className="text-xs text-gray-600">Currently processing</div>
          </div>
          
          <div className="bg-gray-50 p-4 rounded-lg">
            <h5 className="font-medium text-sm mb-2">Completed Today</h5>
            <div className="text-2xl font-bold text-green-600">{flowData?.completed_today || 0}</div>
            <div className="text-xs text-gray-600">Successfully processed</div>
          </div>
        </div>
      </div>
    </div>
  );
}
