import { memo } from 'react';
import SafeHTML from './SafeHTML';

// Function to format option text with proper formatting
const formatOptionText = (text) => {
  if (!text) return '';
  
  let formattedText = text;
  
  // Convert URLs to clickable links
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  formattedText = formattedText.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:text-blue-800 underline">$1</a>');
  
  // Convert bullet points to proper HTML list
  // Split the text by bullet points and reconstruct as HTML
  const lines = formattedText.split(/(?=[a-z]\))/);
  let result = '';
  let inList = false;
  
  for (const line of lines) {
    const trimmedLine = line.trim();
    if (/^[a-z]\)/.test(trimmedLine)) {
      if (!inList) {
        result += '<ol>';
        inList = true;
      }
      // Extract the letter and the rest of the text
      const match = trimmedLine.match(/^([a-z])\)\s*(.*)$/);
      if (match) {
        result += `<li><strong>${match[1]})</strong> ${match[2]}</li>`;
      }
    } else if (inList && trimmedLine) {
      // This is continuation text for the previous list item
      result = result.replace(/<\/li>$/, ` ${trimmedLine}</li>`);
    } else if (!inList) {
      result += line;
    }
  }
  
  if (inList) {
    result += '</ol>';
  }
  
  // Convert line breaks to <br> tags
  result = result.replace(/\n/g, '<br>');
  
  return result;
};

const OFCCard = memo(({ ofc }) => {
  const formattedText = formatOptionText(ofc.option_text);
  
  // Check if sources are resolved or still contain citations
  const hasResolvedSources = ofc.sources && !ofc.sources.includes('[cite:');
  const hasCitations = ofc.sources && ofc.sources.includes('[cite:');
  
  // Parse citation numbers only if sources contain citations
  const parseCitations = (sourcesText) => {
    if (!sourcesText || !sourcesText.includes('[cite:')) return [];
    const citationRegex = /\[cite:\s*([^\]]+)\]/g;
    const citations = [];
    let match;
    
    while ((match = citationRegex.exec(sourcesText)) !== null) {
      // Split by comma and extract individual citation numbers
      const citationNumbers = match[1].split(',').map(num => num.trim());
      citations.push(...citationNumbers);
    }
    
    return citations;
  };
  
  const citationNumbers = hasCitations ? parseCitations(ofc.sources) : [];
  
  // Debug: Log if we have unresolved citations
  if (hasCitations && citationNumbers.length > 0) {
    console.log(`🔍 OFCCard: OFC ${ofc.id} has citations:`, citationNumbers);
  }
  
  return (
    <div className="card">
      <div className="card-body">
        <div className="flex justify-end items-start mb-3">
          <div className="flex gap-2">
            <span className="badge bg-primary text-white" style={{ color: 'white !important' }}>
              {ofc.discipline}
            </span>
            {ofc.sector_id && (
              <span className="badge bg-secondary text-white" style={{ color: 'white !important' }}>
                Sector {ofc.sector_id}
              </span>
            )}
          </div>
        </div>
        
        {/* Display formatted text */}
        <div className="text-gray-700 mb-3">
          <SafeHTML 
            content={formattedText}
            className="formatted-text"
            style={{
              lineHeight: '1.6',
              fontSize: '14px',
              wordWrap: 'break-word',
              wordBreak: 'break-word',
              overflowWrap: 'break-word',
              hyphens: 'auto',
              maxWidth: '100%',
              overflow: 'hidden'
            }}
          />
        </div>
        
        {(hasResolvedSources || citationNumbers.length > 0) && (
          <div className="text-sm text-secondary mb-2">
            <strong>Sources:</strong>
            <div className="mt-1 space-y-2">
              {hasResolvedSources ? (
                <div className="p-2 rounded border-l-2" style={{ 
                  backgroundColor: 'var(--cisa-gray-light)',
                  borderColor: 'var(--cisa-blue)',
                  color: 'var(--cisa-gray-dark)'
                }}>
                  <div className="text-xs text-gray-700">
                    <SafeHTML content={ofc.sources} />
                  </div>
                </div>
              ) : (
                citationNumbers.map((citationNum, idx) => {
                  return (
                    <div key={idx} className="p-2 rounded border-l-2" style={{ 
                      backgroundColor: 'var(--cisa-gray-light)',
                      borderColor: 'var(--cisa-blue)',
                      color: 'var(--cisa-gray-dark)'
                    }}>
                      <div className="text-xs text-gray-700">
                        <strong>Reference {citationNum}:</strong> Source details not available
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
});

OFCCard.displayName = 'OFCCard';

export default OFCCard;

