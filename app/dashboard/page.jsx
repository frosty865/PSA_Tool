import VOFCProcessingDashboard from "@/app/components/components/VOFCProcessingDashboard";

export default function DashboardPage() {
  return (
    <main className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Page Header */}
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            PSA Tool Processing Dashboard
          </h1>
          <p className="text-lg text-gray-600 max-w-3xl mx-auto">
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
