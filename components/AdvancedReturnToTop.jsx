'use client';
import { useState, useEffect } from 'react';

export default function AdvancedReturnToTop() {
  const [isVisible, setIsVisible] = useState(false);
  const [scrollProgress, setScrollProgress] = useState(0);

  // Show button when page is scrolled down and track scroll progress
  useEffect(() => {
    const toggleVisibility = () => {
      const scrollTop = window.pageYOffset;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const scrollPercent = (scrollTop / docHeight) * 100;
      
      setScrollProgress(scrollPercent);
      
      if (scrollTop > 300) {
        setIsVisible(true);
      } else {
        setIsVisible(false);
      }
    };

    window.addEventListener('scroll', toggleVisibility);
    return () => window.removeEventListener('scroll', toggleVisibility);
  }, []);

  // Scroll to top smoothly
  const scrollToTop = () => {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  };

  if (!isVisible) {
    return null;
  }

  return (
    <div className="return-to-top-container">
      {/* Progress indicator */}
      <div className="return-to-top-progress">
        <div
          className="return-to-top-progress-bar"
          style={{ height: `${scrollProgress}%` }}
        />
      </div>

      {/* Return to top button */}
      <button
        onClick={scrollToTop}
        className="return-to-top-button"
        aria-label="Return to top"
        title={`Return to top (${Math.round(scrollProgress)}% scrolled)`}
      >
        <svg 
          className="return-to-top-icon"
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24" 
          xmlns="http://www.w3.org/2000/svg"
        >
          <path 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={2} 
            d="M5 10l7-7m0 0l7 7m-7-7v18" 
          />
        </svg>
      </button>
    </div>
  );
}
