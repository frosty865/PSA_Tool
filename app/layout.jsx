import '@/styles/cisa.css'
import './globals.css'
import Navigation from '../components/Navigation'
import AnalyticsProvider from '../components/AnalyticsProvider'
import AdvancedReturnToTop from '../components/AdvancedReturnToTop'
import SessionTimeoutWarning from '../components/SessionTimeoutWarning'

export const metadata = {
  title: 'VOFC Viewer',
  description: 'Vulnerability and Options for Consideration Viewer',
  icons: {
    icon: '/images/cisa-logo.png',
    shortcut: '/images/cisa-logo.png',
    apple: '/images/cisa-logo.png',
  },
}

// Force dynamic rendering to prevent build hangs
export const dynamic = 'force-dynamic'

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" />
        <link rel="icon" href="/images/cisa-logo.png" type="image/png" />
        <link rel="shortcut icon" href="/images/cisa-logo.png" type="image/png" />
      </head>
      <body className="antialiased">
        <div style={{minHeight: '100vh', backgroundColor: 'var(--cisa-gray-lighter)'}}>
          <Navigation />
          <main style={{width: '100%', paddingTop: 'var(--spacing-xl)', paddingBottom: 'var(--spacing-xl)'}}>
            {children}
          </main>
          <AdvancedReturnToTop />
        </div>
        <AnalyticsProvider />
        <SessionTimeoutWarning />
      </body>
    </html>
  )
}

