'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser, canAccessAdmin } from '../lib/auth';
import LearningMonitor from '../components/components/LearningMonitor';
import '@/styles/cisa.css';

export default function LearningPage() {
  const [loading, setLoading] = useState(true);
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
        <LearningMonitor />
      </div>
    </div>
  );
}

