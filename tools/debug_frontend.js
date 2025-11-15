#!/usr/bin/env node
/**
 * Frontend Diagnostic Tool
 * Checks Next.js configuration, API routes, environment variables, and connections
 */

const fs = require('fs');
const path = require('path');

console.log('='.repeat(80));
console.log('FRONTEND DIAGNOSTIC TOOL');
console.log('='.repeat(80));
console.log();

// ============================================================
// 1. NEXT.JS CONFIGURATION
// ============================================================
console.log('⚙️  NEXT.JS CONFIGURATION');
console.log('-'.repeat(80));

try {
  const nextConfigPath = path.join(process.cwd(), 'next.config.mjs');
  if (fs.existsSync(nextConfigPath)) {
    console.log('  ✅ next.config.mjs: Found');
    const config = fs.readFileSync(nextConfigPath, 'utf-8');
    const hasWebpack = config.includes('webpack');
    const hasPythonIgnore = config.includes('.py') || config.includes('IgnorePlugin');
    console.log(`    Webpack config: ${hasWebpack ? '✅ Present' : '❌ Missing'}`);
    console.log(`    Python ignore: ${hasPythonIgnore ? '✅ Present' : '❌ Missing'}`);
  } else {
    console.log('  ❌ next.config.mjs: NOT FOUND');
  }
} catch (e) {
  console.log(`  ❌ Error reading config: ${e.message}`);
}

try {
  const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf-8'));
  console.log(`  Next.js version: ${packageJson.dependencies.next || 'NOT FOUND'}`);
  console.log(`  React version: ${packageJson.dependencies.react || 'NOT FOUND'}`);
} catch (e) {
  console.log(`  ❌ Error reading package.json: ${e.message}`);
}

console.log();

// ============================================================
// 2. ENVIRONMENT VARIABLES
// ============================================================
console.log('🔐 ENVIRONMENT VARIABLES');
console.log('-'.repeat(80));

// Check for .env files
const envFiles = ['.env.local', '.env', '.env.development', '.env.production'];
let envFileFound = null;
for (const envFile of envFiles) {
  if (fs.existsSync(envFile)) {
    envFileFound = envFile;
    break;
  }
}

if (envFileFound) {
  console.log(`  ✅ ${envFileFound}: Found`);
  
  // Try to load .env file (simple parsing, no dotenv dependency)
  try {
    const envContent = fs.readFileSync(envFileFound, 'utf-8');
    const envLines = envContent.split('\n').filter(line => line.trim() && !line.trim().startsWith('#'));
    
    const envVarsInFile = {};
    for (const line of envLines) {
      const match = line.match(/^([A-Z_]+)=(.+)$/);
      if (match) {
        const key = match[1];
        const value = match[2].replace(/^["']|["']$/g, ''); // Remove quotes
        envVarsInFile[key] = value;
      }
    }
    
    const criticalVars = [
      'NEXT_PUBLIC_SUPABASE_URL',
      'NEXT_PUBLIC_SUPABASE_ANON_KEY',
      'NEXT_PUBLIC_FLASK_API_URL',
      'NEXT_PUBLIC_FLASK_URL',
      'FLASK_URL',
      'NEXT_PUBLIC_OLLAMA_URL',
    ];
    
    console.log('  Variables in file:');
    for (const key of criticalVars) {
      if (envVarsInFile[key]) {
        if (key.includes('KEY') || key.includes('SECRET')) {
          console.log(`    ${key}: ✅ SET (${envVarsInFile[key].length} chars)`);
        } else {
          const displayValue = envVarsInFile[key].length > 50 ? envVarsInFile[key].substring(0, 50) + '...' : envVarsInFile[key];
          console.log(`    ${key}: ✅ ${displayValue}`);
        }
      } else {
        console.log(`    ${key}: ⚠️  NOT SET in ${envFileFound}`);
      }
    }
    
    // Also check process.env (loaded by Next.js)
    console.log('  Variables in process.env (loaded by Next.js):');
    const envVars = {
      'NEXT_PUBLIC_SUPABASE_URL': process.env.NEXT_PUBLIC_SUPABASE_URL,
      'NEXT_PUBLIC_SUPABASE_ANON_KEY': process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ? 'SET' : 'NOT SET',
      'NEXT_PUBLIC_FLASK_API_URL': process.env.NEXT_PUBLIC_FLASK_API_URL,
      'NEXT_PUBLIC_FLASK_URL': process.env.NEXT_PUBLIC_FLASK_URL,
      'FLASK_URL': process.env.FLASK_URL,
      'NEXT_PUBLIC_OLLAMA_URL': process.env.NEXT_PUBLIC_OLLAMA_URL,
      'VERCEL': process.env.VERCEL,
      'NODE_ENV': process.env.NODE_ENV,
    };
    
    for (const [key, value] of Object.entries(envVars)) {
      if (value) {
        if (key.includes('KEY') || key.includes('SECRET')) {
          console.log(`    ${key}: ✅ SET (${value.length} chars)`);
        } else {
          const displayValue = typeof value === 'string' && value.length > 50 ? value.substring(0, 50) + '...' : value;
          console.log(`    ${key}: ✅ ${displayValue}`);
        }
      } else {
        console.log(`    ${key}: ⚠️  NOT SET (will use fallback)`);
      }
    }
  } catch (e) {
    console.log(`  ⚠️  Error reading ${envFileFound}: ${e.message}`);
  }
} else {
  console.log('  ⚠️  No .env file found (.env.local, .env, .env.development, .env.production)');
  console.log('  Note: Variables may be set in Vercel or system environment');
  
  // Check process.env anyway
  const envVars = {
    'NEXT_PUBLIC_SUPABASE_URL': process.env.NEXT_PUBLIC_SUPABASE_URL,
    'NEXT_PUBLIC_SUPABASE_ANON_KEY': process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ? 'SET' : 'NOT SET',
    'NEXT_PUBLIC_FLASK_API_URL': process.env.NEXT_PUBLIC_FLASK_API_URL,
    'NEXT_PUBLIC_FLASK_URL': process.env.NEXT_PUBLIC_FLASK_URL,
    'FLASK_URL': process.env.FLASK_URL,
    'NEXT_PUBLIC_OLLAMA_URL': process.env.NEXT_PUBLIC_OLLAMA_URL,
    'VERCEL': process.env.VERCEL,
    'NODE_ENV': process.env.NODE_ENV,
  };
  
  for (const [key, value] of Object.entries(envVars)) {
    if (value) {
      if (key.includes('KEY') || key.includes('SECRET')) {
        console.log(`  ${key}: ✅ SET (${value.length} chars)`);
      } else {
        const displayValue = typeof value === 'string' && value.length > 50 ? value.substring(0, 50) + '...' : value;
        console.log(`  ${key}: ✅ ${displayValue}`);
      }
    } else {
      console.log(`  ${key}: ❌ NOT SET`);
    }
  }
}

console.log();

// ============================================================
// 3. API ROUTES
// ============================================================
console.log('🛣️  API ROUTES');
console.log('-'.repeat(80));

const apiDir = path.join(process.cwd(), 'app', 'api');
const routeFiles = [];

function findRoutes(dir, prefix = '') {
  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        findRoutes(fullPath, `${prefix}/${entry.name}`);
      } else if (entry.name === 'route.js' || entry.name === 'route.ts') {
        routeFiles.push(`${prefix}/${entry.name}`);
      }
    }
  } catch (e) {
    // Directory doesn't exist or can't be read
  }
}

if (fs.existsSync(apiDir)) {
  findRoutes(apiDir);
  console.log(`  Total API routes: ${routeFiles.length}`);
  console.log('  Sample routes:');
  routeFiles.slice(0, 10).forEach(route => {
    console.log(`    ✅ ${route}`);
  });
  if (routeFiles.length > 10) {
    console.log(`    ... and ${routeFiles.length - 10} more`);
  }
} else {
  console.log('  ❌ app/api directory not found');
}

console.log();

// ============================================================
// 4. PAGES
// ============================================================
console.log('📄 PAGES');
console.log('-'.repeat(80));

const pagesDir = path.join(process.cwd(), 'app');
const pageFiles = [];

function findPages(dir, prefix = '') {
  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory() && entry.name !== 'api' && entry.name !== 'components') {
        const pagePath = path.join(fullPath, 'page.jsx');
        if (fs.existsSync(pagePath) || fs.existsSync(path.join(fullPath, 'page.tsx'))) {
          pageFiles.push(`${prefix}/${entry.name}`);
        }
        findPages(fullPath, `${prefix}/${entry.name}`);
      } else if (entry.name === 'page.jsx' || entry.name === 'page.tsx') {
        if (prefix === '') {
          pageFiles.push('/');
        } else {
          pageFiles.push(prefix);
        }
      }
    }
  } catch (e) {
    // Directory doesn't exist or can't be read
  }
}

if (fs.existsSync(pagesDir)) {
  findPages(pagesDir);
  console.log(`  Total pages: ${pageFiles.length}`);
  console.log('  Sample pages:');
  pageFiles.slice(0, 10).forEach(page => {
    console.log(`    ✅ ${page || '/'}`);
  });
  if (pageFiles.length > 10) {
    console.log(`    ... and ${pageFiles.length - 10} more`);
  }
} else {
  console.log('  ❌ app directory not found');
}

console.log();

// ============================================================
// 5. CRITICAL FILES
// ============================================================
console.log('📁 CRITICAL FILES');
console.log('-'.repeat(80));

const criticalFiles = [
  'app/layout.jsx',
  'app/page.jsx',
  'app/lib/server-utils.js',
  'app/lib/supabase-client.js',
  'app/lib/supabase-server.js',
  'next.config.mjs',
  'package.json',
  'tailwind.config.js',
  '.vercelignore',
];

for (const file of criticalFiles) {
  const filePath = path.join(process.cwd(), file);
  if (fs.existsSync(filePath)) {
    const stat = fs.statSync(filePath);
    console.log(`  ✅ ${file} (${(stat.size / 1024).toFixed(1)} KB)`);
  } else {
    console.log(`  ❌ ${file}: NOT FOUND`);
  }
}

console.log();

// ============================================================
// 6. BUILD STATUS
// ============================================================
console.log('🏗️  BUILD STATUS');
console.log('-'.repeat(80));

const buildDir = path.join(process.cwd(), '.next');
if (fs.existsSync(buildDir)) {
  console.log('  ✅ .next directory exists (app has been built)');
  try {
    const buildIdPath = path.join(buildDir, 'BUILD_ID');
    if (fs.existsSync(buildIdPath)) {
      const buildId = fs.readFileSync(buildIdPath, 'utf-8').trim();
      console.log(`    Build ID: ${buildId}`);
    }
  } catch (e) {
    // Can't read build ID
  }
} else {
  console.log('  ⚠️  .next directory not found (app needs to be built)');
  console.log('    Run: npm run build');
}

console.log();

// ============================================================
// 7. DEPENDENCIES
// ============================================================
console.log('📦 DEPENDENCIES');
console.log('-'.repeat(80));

try {
  const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf-8'));
  const deps = packageJson.dependencies || {};
  const criticalDeps = [
    'next',
    'react',
    'react-dom',
    '@supabase/supabase-js',
  ];
  
  for (const dep of criticalDeps) {
    if (deps[dep]) {
      console.log(`  ✅ ${dep}: ${deps[dep]}`);
    } else {
      console.log(`  ❌ ${dep}: NOT FOUND`);
    }
  }
} catch (e) {
  console.log(`  ❌ Error reading dependencies: ${e.message}`);
}

console.log();

// ============================================================
// 8. VERCEL CONFIGURATION
// ============================================================
console.log('🚀 VERCEL CONFIGURATION');
console.log('-'.repeat(80));

const vercelIgnorePath = path.join(process.cwd(), '.vercelignore');
if (fs.existsSync(vercelIgnorePath)) {
  console.log('  ✅ .vercelignore: Found');
  const content = fs.readFileSync(vercelIgnorePath, 'utf-8');
  const hasPython = content.includes('.py') || content.includes('*.py');
  const hasServices = content.includes('services/') || content.includes('routes/');
  console.log(`    Python files ignored: ${hasPython ? '✅' : '❌'}`);
  console.log(`    Services ignored: ${hasServices ? '✅' : '❌'}`);
} else {
  console.log('  ⚠️  .vercelignore: NOT FOUND (Python files may be deployed)');
}

const vercelJsonPath = path.join(process.cwd(), 'vercel.json');
if (fs.existsSync(vercelJsonPath)) {
  console.log('  ✅ vercel.json: Found');
} else {
  console.log('  ⚠️  vercel.json: NOT FOUND (using defaults)');
}

console.log();

// ============================================================
// 9. SUMMARY
// ============================================================
console.log('='.repeat(80));
console.log('SUMMARY');
console.log('='.repeat(80));

const issues = [];
const warnings = [];

// Check environment variables (only warn if .env file doesn't exist)
if (!envFileFound) {
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL) {
    warnings.push('NEXT_PUBLIC_SUPABASE_URL not set (check .env file)');
  }
  if (!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY && !process.env.SUPABASE_ANON_KEY) {
    warnings.push('Supabase anon key not set (check .env file)');
  }
} else {
  // .env file exists, variables are likely there (Next.js will load them)
  // Only check process.env if we're in a Next.js context
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NODE_ENV) {
    warnings.push('NEXT_PUBLIC_SUPABASE_URL not in process.env (may need Next.js to load .env)');
  }
}

// Check build
if (!fs.existsSync(buildDir)) {
  warnings.push('App needs to be built (run: npm run build)');
}

// Check critical files
if (!fs.existsSync(path.join(process.cwd(), 'app/layout.jsx'))) {
  issues.push('app/layout.jsx not found');
}

if (issues.length > 0) {
  console.log('❌ CRITICAL ISSUES:');
  issues.forEach(issue => console.log(`  - ${issue}`));
  console.log();
}

if (warnings.length > 0) {
  console.log('⚠️  WARNINGS:');
  warnings.forEach(warning => console.log(`  - ${warning}`));
  console.log();
}

if (issues.length === 0 && warnings.length === 0) {
  console.log('✅ No critical issues found!');
  console.log();
  console.log('Frontend configuration looks good.');
} else {
  console.log('🔧 RECOMMENDED ACTIONS:');
  if (issues.some(i => i.includes('SUPABASE'))) {
    console.log('  1. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY');
  }
  if (warnings.some(w => w.includes('build'))) {
    console.log('  1. Run: npm run build');
  }
}

console.log('='.repeat(80));

