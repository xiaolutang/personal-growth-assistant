export type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';

export interface LogEntry {
  id: number;
  timestamp: string;
  level: LogLevel;
  message: string;
  logger_name?: string;
  request_id?: string;
  method?: string;
  path?: string;
  status_code?: number;
  client_ip?: string;
  process_time_ms?: number;
  stack_trace?: string;
  exception_type?: string;
  exception_message?: string;
  extra?: Record<string, unknown>;
}

export interface LogStats {
  total_count: number;
  count_by_level: {
    DEBUG: number;
    INFO: number;
    WARNING: number;
    ERROR: number;
    CRITICAL: number;
  };
  oldest_log?: string;
  newest_log?: string;
  db_size_mb: number;
}

export interface LogFilter {
  level?: LogLevel;
  request_id?: string;
  keyword?: string;
  start_time?: string;
  end_time?: string;
  limit: number;
  offset: number;
  order: 'desc' | 'asc';
}

// 后端响应格式
export interface LogsResponse {
  items: LogEntry[];
  total: number;
  limit: number;
  offset: number;
}
