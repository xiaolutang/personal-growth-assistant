import { useState, useCallback } from 'react';
import type { LogEntry, LogStats, LogFilter, LogsResponse } from '../types/log';

const API_BASE = '/api/logs';

export function useLogs() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [stats, setStats] = useState<LogStats | null>(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = useCallback(async (filter: LogFilter) => {
    setLoading(true);
    setError(null);

    const params = new URLSearchParams();
    if (filter.level) params.set('level', filter.level);
    if (filter.request_id) params.set('request_id', filter.request_id);
    if (filter.keyword) params.set('keyword', filter.keyword);
    if (filter.start_time) params.set('start_time', filter.start_time);
    if (filter.end_time) params.set('end_time', filter.end_time);
    params.set('limit', String(filter.limit));
    params.set('offset', String(filter.offset));
    params.set('order', filter.order || 'desc');

    try {
      const response = await fetch(`${API_BASE}?${params}`);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }
      const data: LogsResponse = await response.json();
      setLogs(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : '未知错误');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/stats`);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }
      const data: LogStats = await response.json();
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  }, []);

  return {
    logs,
    stats,
    total,
    loading,
    error,
    fetchLogs,
    fetchStats,
  };
}
