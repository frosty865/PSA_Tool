'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { fetchVulnerabilities, fetchVOFC } from '../lib/fetchVOFC';
import { getCurrentUser, getUserProfile, canAccessAdmin } from '../lib/auth';
import { supabase } from '../lib/supabaseClient';

export default function AdminPage() {
  const [stats, setStats] = useState({
    vulnerabilities: 0,
    ofcs: 0,
    users: 0,
    pendingVulnerabilities: 0,
    pendingOFCs: 0
  });
  const [dbHealth, setDbHealth] = useState({
    connection: 'Unknown',
    responseTime: 0,
    lastChecked: null
  });
  const [loading, setLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState(null);
  const [userRole, setUserRole] = useState(null);
  const [showBackToTop, setShowBackToTop] = useState(false);
  const router = useRouter();

  useEffect(() => {
    checkAuth();
    loadStats();
    checkDatabaseHealth();
  }, []);

  useEffect(() => {
    const handleScroll = () => {
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      setShowBackToTop(scrollTop > 300);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        loadStats();
        checkDatabaseHealth();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  const checkAuth = async () => {
    try {
      const user = await getCurrentUser();
      if (!user) {
        router.push('/login');
        return;
      }

      const profile = await getUserProfile(user.id);
      const canAccess = await canAccessAdmin(user.id);

      if (!canAccess) {
        alert('You do not have admin access');
        router.push('/');
        return;
      }

      setCurrentUser(user);
      setUserRole(profile?.role || 'user');
    } catch (error) {
      console.error('Auth check failed:', error);
      router.push('/login');
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const [vulnerabilities, ofcs, users] = await Promise.all([
        fetchVulnerabilities(),
        fetchVOFC(),
        supabase.from('profiles').select('*')
      ]);

      setStats({
        vulnerabilities: vulnerabilities?.length || 0,
        ofcs: ofcs?.length || 0,
        users: users.data?.length || 0,
        pendingVulnerabilities: 0,
        pendingOFCs: 0
      });
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const checkDatabaseHealth = async () => {
    const startTime = Date.now();
    try {
      const { data, error } = await supabase.from('vulnerabilities').select('count').limit(1);
      const responseTime = Date.now() - startTime;
      
      setDbHealth({
        connection: error ? 'Error' : 'Connected',
        responseTime: responseTime,
        lastChecked: new Date().toLocaleTimeString()
      });
    } catch (error) {
      setDbHealth({
        connection: 'Error',
        responseTime: 0,
        lastChecked: new Date().toLocaleTimeString()
      });
    }
  };

  const handleSignOut = async () => {
    try {
      const { error } = await supabase.auth.signOut();
      if (error) {
        console.error('Error signing out:', error);
      } else {
        router.push('/');
      }
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading admin panel...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-blue-900 text-white p-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold">Admin Panel</h1>
            <p className="text-blue-200">System Administration and Management</p>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm">Welcome, {currentUser?.email}</span>
            <button
              onClick={handleSignOut}
              className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded text-sm"
            >
              Sign Out
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6">
        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-red-100 text-red-600">
                <i className="fas fa-shield-alt text-xl"></i>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Vulnerabilities</p>
                <p className="text-2xl font-bold text-gray-900">{stats.vulnerabilities}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-blue-100 text-blue-600">
                <i className="fas fa-lightbulb text-xl"></i>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">OFCs</p>
                <p className="text-2xl font-bold text-gray-900">{stats.ofcs}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-green-100 text-green-600">
                <i className="fas fa-users text-xl"></i>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Users</p>
                <p className="text-2xl font-bold text-gray-900">{stats.users}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-yellow-100 text-yellow-600">
                <i className="fas fa-clock text-xl"></i>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Pending</p>
                <p className="text-2xl font-bold text-gray-900">{stats.pendingVulnerabilities + stats.pendingOFCs}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Database Health and Status */}
        <div className="card mb-6">
          <div className="card-header">
            <div className="flex justify-between items-center">
              <h2 className="card-title">Database Health and Status</h2>
              <div className="flex gap-2">
                <Link href="/admin/users" className="btn btn-primary btn-sm">
                  <i className="fas fa-users mr-2"></i>
                  Manage Users
                </Link>
                <Link href="/admin/ofcs" className="btn btn-success btn-sm">
                  <i className="fas fa-lightbulb mr-2"></i>
                  Manage OFCs
                </Link>
              </div>
            </div>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center">
                <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                  dbHealth.connection === 'Connected' 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-red-100 text-red-800'
                }`}>
                  <div className={`w-2 h-2 rounded-full mr-2 ${
                    dbHealth.connection === 'Connected' ? 'bg-green-500' : 'bg-red-500'
                  }`}></div>
                  {dbHealth.connection}
                </div>
                <p className="text-sm text-gray-600 mt-1">Database Status</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-gray-900">{dbHealth.responseTime}ms</p>
                <p className="text-sm text-gray-600">Response Time</p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-600">Last Checked</p>
                <p className="text-sm font-medium text-gray-900">{dbHealth.lastChecked}</p>
              </div>
            </div>
            <div className="mt-4 flex justify-center">
              <button
                onClick={() => {
                  loadStats();
                  checkDatabaseHealth();
                }}
                className="btn btn-secondary btn-sm"
              >
                <i className="fas fa-sync-alt mr-2"></i>
                Refresh Status
              </button>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="card mb-6">
          <div className="card-header">
            <h2 className="card-title">Quick Actions</h2>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Link href="/review" className="btn btn-primary">
                <i className="fas fa-clipboard-check mr-2"></i>
                Review Submissions
              </Link>
              <Link href="/admin/users" className="btn btn-secondary">
                <i className="fas fa-users mr-2"></i>
                Manage Users
              </Link>
              <Link href="/admin/ofcs" className="btn btn-success">
                <i className="fas fa-lightbulb mr-2"></i>
                Manage OFCs
              </Link>
              <Link href="/admin/disciplines" className="btn btn-warning">
                <i className="fas fa-tags mr-2"></i>
                Manage Disciplines
              </Link>
            </div>
          </div>
        </div>

        {/* Back to Top Button */}
        {showBackToTop && (
          <button
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            className="fixed bottom-6 right-6 bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-full shadow-lg transition-all duration-200 z-50"
          >
            <i className="fas fa-arrow-up"></i>
          </button>
        )}
      </div>
    </div>
  );
}
