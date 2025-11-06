/**
 * Cache middleware for Next.js API routes
 * Provides caching strategies for API responses
 */

import { NextResponse } from 'next/server'

/**
 * Cache strategies with different TTL values
 */
export const CacheStrategies = {
  SHORT: {
    maxAge: 60, // 1 minute
    sMaxAge: 60,
    staleWhileRevalidate: 300 // 5 minutes
  },
  MEDIUM: {
    maxAge: 300, // 5 minutes
    sMaxAge: 300,
    staleWhileRevalidate: 600 // 10 minutes
  },
  LONG: {
    maxAge: 3600, // 1 hour
    sMaxAge: 3600,
    staleWhileRevalidate: 86400 // 24 hours
  },
  VERY_LONG: {
    maxAge: 86400, // 24 hours
    sMaxAge: 86400,
    staleWhileRevalidate: 604800 // 7 days
  }
}

/**
 * Apply cache headers to a NextResponse
 * @param {NextResponse} response - The Next.js response object
 * @param {Object} strategy - Cache strategy from CacheStrategies
 * @returns {NextResponse} Response with cache headers applied
 */
export function applyCacheHeaders(response, strategy) {
  if (!response || !strategy) {
    return response
  }

  // Set Cache-Control header
  const cacheControl = [
    `public`,
    `max-age=${strategy.maxAge}`,
    `s-maxage=${strategy.sMaxAge}`,
    `stale-while-revalidate=${strategy.staleWhileRevalidate}`
  ].join(', ')

  response.headers.set('Cache-Control', cacheControl)
  
  return response
}

