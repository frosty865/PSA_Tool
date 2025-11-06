'use client';

import { useEffect, useState } from 'react';
import { fetchWithAuth } from '../../../lib/fetchWithAuth';
import { useRouter } from 'next/navigation';
import { getCurrentUser, canAccessAdmin } from '../../../lib/auth';
import '@/styles/cisa.css';

export default function ModelAnalyticsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const router = useRouter();

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const user = await getCurrentUser();
      if (!user) {
        router.push('/splash');
        return;
      }

      const canAccess = await canAccessAdmin();
      if (!canAccess) {
        router.push('/');
        return;
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      router.push('/splash');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="content-wrapper">
          <div className="text-center py-8">
            <div className="loading"></div>
            <p className="text-secondary mt-3">Loading...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="content-wrapper">
        <div className="card-header">
          <h1 className="card-title">Model Analytics</h1>
          <p className="card-subtitle">
            View model performance metrics including accept rate, edits, and softmatch ratio
          </p>
        </div>

        <div className="card">
          <div className="card-body">
            <p className="text-secondary">
              Model analytics data will be displayed here. This page shows performance metrics for different model versions.
            </p>
            <p className="text-secondary mt-4">
              <strong>Note:</strong> This feature is under development. Model performance data will appear here once processing begins.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

