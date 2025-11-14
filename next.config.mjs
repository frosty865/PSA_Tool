import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  staticPageGenerationTimeout: 60,
  
  // Minimal webpack config - essential aliases only
  webpack: (config, { isServer, webpack }) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': __dirname,
    };
    
    // Exclude Python files and services from webpack processing
    // This prevents webpack from trying to process Python files during build
    // webpack is provided by Next.js in the function parameters
    config.plugins = config.plugins || [];
    config.plugins.push(
      new webpack.IgnorePlugin({
        resourceRegExp: /\.(py|pyc|pyo|pyd)$/,
      })
    );
    
    // Reduce webpack processing time
    if (!isServer) {
      config.optimization = {
        ...config.optimization,
        moduleIds: 'deterministic',
      };
    }
    
    return config;
  },
  
  // Set output tracing root to prevent warnings
  outputFileTracingRoot: __dirname,
  
  // Rewrite favicon.ico to CISA logo to prevent 404 errors
  async rewrites() {
    return [
      {
        source: '/favicon.ico',
        destination: '/images/cisa-logo.png',
      },
    ];
  },
}

export default nextConfig
