// Monitoring service for system health checks
import { supabaseAdmin } from '@/app/lib/supabase-admin.js';

const OLLAMA_BASE_URL = process.env.OLLAMA_HOST || 
                        process.env.OLLAMA_URL || 
                        'http://127.0.0.1:11434';

export const monitoring = {
  /**
   * Get system status
   */
  async getSystemStatus() {
    const supabaseCheck = await this.checkSupabase();
    const ollamaCheck = await this.checkOllama();
    
    const checks = {
      supabase: supabaseCheck,
      ollama: ollamaCheck
    };

    const healthyCount = Object.values(checks).filter(c => c.status === 'healthy').length;
    const totalChecks = Object.keys(checks).length;
    
    let status = 'healthy';
    if (healthyCount < totalChecks * 0.5) {
      status = 'critical';
    } else if (healthyCount < totalChecks) {
      status = 'degraded';
    }

    return {
      status,
      checks,
      timestamp: new Date().toISOString()
    };
  },

  /**
   * Check Supabase connection
   */
  async checkSupabase() {
    try {
      if (!supabaseAdmin) {
        return { status: 'error', message: 'Supabase admin client not configured' };
      }
      
      // Simple query to test connection
      const { error } = await supabaseAdmin
        .from('users_profiles')
        .select('count')
        .limit(1);
      
      if (error) {
        return { status: 'error', message: error.message };
      }
      
      return { status: 'healthy', message: 'Connected' };
    } catch (error) {
      return { status: 'error', message: error.message };
    }
  },

  /**
   * Check Ollama connection
   */
  async checkOllama() {
    try {
      const url = `${OLLAMA_BASE_URL.replace(/\/$/, '')}/api/tags`;
      
      // Create timeout controller
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      
      const response = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        return { status: 'error', message: `HTTP ${response.status}` };
      }
      
      return { status: 'healthy', message: 'Connected' };
    } catch (error) {
      if (error.name === 'AbortError') {
        return { status: 'error', message: 'Connection timeout' };
      }
      return { status: 'error', message: error.message || 'Connection failed' };
    }
  }
};

