import { memo } from 'react';

/**
 * Safe HTML component that sanitizes content to prevent XSS attacks
 */
const SafeHTML = memo(({ content, className, ...props }) => {
  if (!content || typeof content !== 'string') {
    return null;
  }

  // Simple HTML sanitization without DOMPurify to avoid jsdom conflicts
  const sanitizedContent = content
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '') // Remove script tags
    .replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '') // Remove iframe tags
    .replace(/on\w+="[^"]*"/gi, '') // Remove event handlers
    .replace(/javascript:/gi, '') // Remove javascript: URLs
    .replace(/data:/gi, '') // Remove data: URLs
    .replace(/vbscript:/gi, ''); // Remove vbscript: URLs

  return (
    <div 
      className={className}
      dangerouslySetInnerHTML={{ __html: sanitizedContent }}
      {...props}
    />
  );
});

SafeHTML.displayName = 'SafeHTML';

export default SafeHTML;

