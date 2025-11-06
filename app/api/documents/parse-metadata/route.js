import { NextResponse } from 'next/server';
import { getFlaskUrl } from '@/app/lib/server-utils';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function OPTIONS(request) {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}

export async function POST(request) {
  try {
    const formData = await request.formData();
    const file = formData.get('file');

    if (!file) {
      return NextResponse.json(
        { success: false, error: 'No file provided' },
        { status: 400 }
      );
    }

    // Extract metadata from filename directly (no need to call Flask for this)
    // Flask processing is expensive, so we'll just do basic extraction
    return await extractBasicMetadata(file);
  } catch (error) {
    console.error('[parse-metadata] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to parse metadata' },
      { status: 500 }
    );
  }
}

async function extractBasicMetadata(file) {
  const filename = file.name || 'document';
  
  const parsedData = {
    title: extractTitleFromFilename(filename),
    organization: extractOrgFromFilename(filename),
    year: extractYearFromFilename(filename),
    sourceType: detectSourceType(filename),
    url: '',
  };

  return NextResponse.json({
    success: true,
    parsedData,
  });
}

function extractTitleFromFilename(filename) {
  // Remove extension
  const nameWithoutExt = filename.replace(/\.[^/.]+$/, '');
  // Remove common prefixes/suffixes
  let title = nameWithoutExt
    .replace(/^[0-9]+[-_]\s*/, '') // Remove leading numbers
    .replace(/[-_]/g, ' ') // Replace dashes/underscores with spaces
    .trim();
  
  // Capitalize first letter of each word
  title = title.split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
  
  return title || 'Untitled Document';
}

function extractOrgFromFilename(filename) {
  // Look for common organization patterns
  const orgPatterns = [
    /(?:^|[-_])([A-Z]{2,})[-_]/i, // Acronyms like "DHS", "NSA"
    /([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/, // Title case words
  ];
  
  for (const pattern of orgPatterns) {
    const match = filename.match(pattern);
    if (match && match[1]) {
      return match[1];
    }
  }
  
  return '';
}

function extractYearFromFilename(filename) {
  // Look for 4-digit year (1900-2100)
  const yearMatch = filename.match(/\b(19|20)\d{2}\b/);
  if (yearMatch) {
    return parseInt(yearMatch[0]);
  }
  
  // Default to current year
  return new Date().getFullYear();
}

function detectSourceType(filename) {
  const lower = filename.toLowerCase();
  
  if (lower.includes('report') || lower.includes('assessment')) {
    return 'report';
  }
  if (lower.includes('guide') || lower.includes('manual')) {
    return 'guide';
  }
  if (lower.includes('standard') || lower.includes('spec')) {
    return 'standard';
  }
  if (lower.includes('policy') || lower.includes('procedure')) {
    return 'policy';
  }
  if (lower.includes('advisory') || lower.includes('alert')) {
    return 'advisory';
  }
  
  return 'unknown';
}

