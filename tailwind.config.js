/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#004B87',
        accent: '#C9B037',
        bg: '#F5F7FA',
        surface: '#FFFFFF',
        border: '#E5E8EB',
        text: '#1E1E1E',
        textSecondary: '#4B5563',
        success: '#118A3C',
        warning: '#B45309',
        error: '#DC2626'
      },
      fontFamily: {
        sans: ['Inter', 'Source Sans Pro', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace']
      },
      fontSize: {
        xs: ['13px', { lineHeight: '1.5' }],
        sm: ['15px', { lineHeight: '1.5' }],
        base: ['16px', { lineHeight: '1.6' }],
        lg: ['20px', { lineHeight: '1.5' }],
        xl: ['24px', { lineHeight: '1.4' }],
        '2xl': ['28px', { lineHeight: '1.4' }]
      },
      borderRadius: {
        sm: '6px',
        md: '10px',
        lg: '16px',
        xl: '24px'
      },
      boxShadow: {
        card: '0 2px 4px rgba(0, 0, 0, 0.05)',
        elevated: '0 4px 8px rgba(0, 0, 0, 0.08)'
      },
      spacing: {
        xs: '4px',
        sm: '8px',
        md: '16px',
        lg: '24px',
        xl: '32px'
      }
    },
  },
  plugins: [require('@tailwindcss/forms')],
};