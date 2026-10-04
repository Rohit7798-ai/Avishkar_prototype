import { useState, useEffect, useCallback } from 'react';
import { checkHealth } from '../services/api';

/**
 * Custom hook to monitor backend health connectivity.
 * @param {boolean} autoPoll - Whether to poll periodically
 * @param {number} intervalMs - Polling interval in ms (default 30000)
 */
export function useHealth(autoPoll = false, intervalMs = 30000) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchHealth = useCallback(async () => {
    try {
      const res = await checkHealth();
      setData(res);
      setError(null);
    } catch (err) {
      setError(err.message || 'Backend service unreachable');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    if (!autoPoll) return;

    const timer = setInterval(fetchHealth, intervalMs);
    return () => clearInterval(timer);
  }, [fetchHealth, autoPoll, intervalMs]);

  return {
    isHealthy: data?.status === 'ok',
    service: data?.service || null,
    loading,
    error,
    refetch: fetchHealth,
  };
}
