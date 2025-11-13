import VOFCProcessingDashboard from "@/app/components/components/VOFCProcessingDashboard";
import '@/styles/cisa.css'

export default function DashboardPage() {
  return (
    <main style={{ minHeight: '100vh', backgroundColor: 'var(--cisa-gray-lighter)', padding: 'var(--spacing-xl)' }}>
      <div className="container" style={{ maxWidth: '1280px', margin: '0 auto' }}>
        {/* Page Header */}
        <div style={{ textAlign: 'center', marginBottom: 'var(--spacing-xl)' }}>
          <h1 style={{ fontSize: 'var(--font-size-xxl)', fontWeight: 700, color: 'var(--cisa-blue)', marginBottom: 'var(--spacing-md)' }}>
            PSA Tool Processing Dashboard
          </h1>
          <p style={{ fontSize: 'var(--font-size-lg)', color: 'var(--cisa-gray)', maxWidth: '768px', margin: '0 auto' }}>
            Real-time monitoring of document processing, service health, and pipeline status.
            Monitor Flask server, Ollama API, Supabase, and active processing jobs.
          </p>
        </div>

        {/* Main Dashboard */}
        <VOFCProcessingDashboard />
      </div>
    </main>
  );
}
