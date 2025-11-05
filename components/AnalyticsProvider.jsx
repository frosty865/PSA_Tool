'use client';

import { Analytics } from '@vercel/analytics/react';
import { SpeedInsights } from '@vercel/speed-insights/next';

/**
 * Analytics Provider Component
 * Provides Vercel Analytics and Speed Insights for the VOFC Engine
 * Conditionally renders only if analytics is enabled
 */
export default function AnalyticsProvider() {
  // Only enable analytics in production and if explicitly enabled
  const enableAnalytics = process.env.NODE_ENV === 'production' && 
    (process.env.NEXT_PUBLIC_VERCEL_ANALYTICS_ENABLED === 'true' || 
     process.env.NEXT_PUBLIC_ENABLE_ANALYTICS === 'true');

  if (!enableAnalytics) {
    return null;
  }

  return (
    <>
      <Analytics />
      <SpeedInsights />
    </>
  );
}

/**
 * Custom Analytics Events for VOFC Engine
 * Use these functions to track specific user actions
 */
export const trackEvent = (eventName, properties = {}) => {
  if (typeof window !== 'undefined' && window.va) {
    window.va('track', eventName, properties);
  }
};

/**
 * Track VOFC-specific events
 */
export const trackVOFCEvent = {
  // Authentication events
  login: (role) => trackEvent('vofc_login', { role }),
  logout: () => trackEvent('vofc_logout'),
  
  // VOFC submission events
  submitVOFC: (type) => trackEvent('vofc_submit', { type }),
  bulkSubmit: (count) => trackEvent('vofc_bulk_submit', { count }),
  
  // Navigation events
  viewDashboard: () => trackEvent('vofc_view_dashboard'),
  viewVulnerabilities: () => trackEvent('vofc_view_vulnerabilities'),
  viewOFCS: () => trackEvent('vofc_view_ofcs'),
  
  // Admin events
  adminAction: (action) => trackEvent('vofc_admin_action', { action }),
  userManagement: (action) => trackEvent('vofc_user_management', { action }),
  
  // Error tracking
  error: (error, context) => trackEvent('vofc_error', { error, context }),
  
  // Performance events
  pageLoad: (page, loadTime) => trackEvent('vofc_page_load', { page, loadTime }),
  apiCall: (endpoint, duration) => trackEvent('vofc_api_call', { endpoint, duration })
};

/**
 * Track page views with custom properties
 */
export const trackPageView = (page, properties = {}) => {
  trackEvent('page_view', { page, ...properties });
};

/**
 * Track user engagement
 */
export const trackEngagement = (action, details = {}) => {
  trackEvent('user_engagement', { action, ...details });
};
