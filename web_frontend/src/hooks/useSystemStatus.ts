import { useState, useEffect } from 'react';
import { api } from '../services/api';
import type { SystemStatusResponse } from '../types/attocore';

export const useSystemStatus = () => {
  const [status, setStatus] = useState<SystemStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await api.getSystemStatus();
        setStatus(response);
        setError(null);
      } catch (err) {
        setError('Failed to fetch system status');
        console.error('Error fetching system status:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
    
    // Poll every 30 seconds
    const interval = setInterval(fetchStatus, 30000);
    
    return () => clearInterval(interval);
  }, []);

  return { status, loading, error };
};