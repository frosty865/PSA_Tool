'use client';

import { useState, useEffect } from 'react';

export default function DomainFilter({ 
  selectedDomains, 
  onDomainChange, 
  userRole = null,
  className = "" 
}) {
  const [localSelectedDomains, setLocalSelectedDomains] = useState(selectedDomains || []);

  // Set default domains based on user role
  useEffect(() => {
    if (userRole && localSelectedDomains.length === 0) {
      let defaultDomains = [];
      
      if (userRole === 'psa' || userRole === 'spsa') {
        // PSA dashboards default to Physical + Converged
        defaultDomains = ['Physical', 'Converged'];
      } else if (userRole === 'analyst' || userRole === 'admin') {
        // CSA dashboards default to Cyber + Converged
        defaultDomains = ['Cyber', 'Converged'];
      } else {
        // Default to all domains
        defaultDomains = ['Physical', 'Cyber', 'Converged'];
      }
      
      setLocalSelectedDomains(defaultDomains);
      onDomainChange(defaultDomains);
    }
  }, [userRole, onDomainChange]);

  const domainOptions = [
    { value: 'Physical', label: 'Physical', color: 'bg-blue-100 text-blue-800 border-blue-200' },
    { value: 'Cyber', label: 'Cyber', color: 'bg-green-100 text-green-800 border-green-200' },
    { value: 'Converged', label: 'Converged', color: 'bg-purple-100 text-purple-800 border-purple-200' },
    { value: 'All', label: 'All', color: 'bg-gray-100 text-gray-800 border-gray-200' }
  ];

  const handleDomainToggle = (domain) => {
    let newSelectedDomains;
    
    if (domain === 'All') {
      // If "All" is selected, select all domains
      newSelectedDomains = ['Physical', 'Cyber', 'Converged'];
    } else {
      // Toggle individual domain
      if (localSelectedDomains.includes(domain)) {
        newSelectedDomains = localSelectedDomains.filter(d => d !== domain);
      } else {
        newSelectedDomains = [...localSelectedDomains, domain];
      }
      
      // If all domains are selected, show "All" as selected
      if (newSelectedDomains.length === 3) {
        newSelectedDomains = ['Physical', 'Cyber', 'Converged'];
      }
    }
    
    setLocalSelectedDomains(newSelectedDomains);
    onDomainChange(newSelectedDomains);
  };

  const isAllSelected = localSelectedDomains.length === 3 || 
    (localSelectedDomains.includes('Physical') && 
     localSelectedDomains.includes('Cyber') && 
     localSelectedDomains.includes('Converged'));

  return (
    <div className={`domain-filter ${className}`}>
      <div className="flex flex-wrap gap-2">
        <span className="text-sm font-medium text-gray-700 mr-2">Domain Filter:</span>
        {domainOptions.map((option) => {
          const isSelected = option.value === 'All' ? isAllSelected : localSelectedDomains.includes(option.value);
          
          return (
            <button
              key={option.value}
              onClick={() => handleDomainToggle(option.value)}
              className={`px-3 py-1 text-sm font-medium rounded-full border transition-all duration-200 ${
                isSelected
                  ? `${option.color} border-2 shadow-sm`
                  : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
              }`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
      
      {localSelectedDomains.length > 0 && localSelectedDomains.length < 3 && (
        <div className="mt-2 text-xs text-gray-500">
          Showing {localSelectedDomains.length} domain{localSelectedDomains.length > 1 ? 's' : ''}: {localSelectedDomains.join(', ')}
        </div>
      )}
    </div>
  );
}
