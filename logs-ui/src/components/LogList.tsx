import type { LogEntry } from '../types/log';

interface Props {
  logs: LogEntry[];
  loading: boolean;
  error: string | null;
  onLogClick: (log: LogEntry) => void;
  onRequestIdClick: (requestId: string) => void;
}

export function LogList({ logs, loading, error, onLogClick, onRequestIdClick }: Props) {
  if (error) {
    return (
      <div className="bg-red-50 text-red-600 p-4 rounded-lg text-center">
        加载失败: {error}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="text-center py-8 text-gray-500">
        加载中...
      </div>
    );
  }

  if (logs.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        暂无日志
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {logs.map((log) => (
        <div
          key={log.id}
          onClick={() => onLogClick(log)}
          className="bg-white rounded-lg p-3 shadow-sm border border-gray-100 cursor-pointer hover:shadow-md transition-shadow"
        >
          {/* 第一行: 级别 + 时间 + Logger */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${
              log.level === 'ERROR' ? 'bg-red-100 text-red-700' :
              log.level === 'WARNING' ? 'bg-orange-100 text-orange-700' :
              log.level === 'INFO' ? 'bg-blue-100 text-blue-700' :
              log.level === 'DEBUG' ? 'bg-gray-100 text-gray-600' :
              'bg-red-200 text-red-800'
            }`}>
              {log.level}
            </span>
            <span className="text-xs text-gray-400">
              {new Date(log.timestamp).toLocaleString('zh-CN', {
                month: 'numeric',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              })}
            </span>
            {log.logger_name && (
              <span className="text-xs text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                {log.logger_name}
              </span>
            )}
          </div>

          {/* 第二行: 消息 */}
          <div className="mt-1.5 text-sm text-gray-800 font-mono leading-relaxed line-clamp-2">
            {log.message}
          </div>

          {/* 第三行: 标签 */}
          <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-gray-500">
            {log.request_id && (
              <span
                onClick={(e) => {
                  e.stopPropagation();
                  onRequestIdClick(log.request_id!);
                }}
                className="bg-gray-100 px-1.5 py-0.5 rounded cursor-pointer hover:bg-gray-200 font-mono"
                title="点击筛选此请求"
              >
                #{log.request_id.slice(0, 8)}
              </span>
            )}
            {log.method && log.path && (
              <span className={`px-1.5 py-0.5 rounded ${
                log.status_code && log.status_code >= 400
                  ? 'bg-red-50 text-red-600'
                  : 'bg-green-50 text-green-600'
              }`}>
                {log.method} {log.path} {log.status_code}
              </span>
            )}
            {log.process_time_ms != null && (
              <span className="text-gray-400">
                {log.process_time_ms}ms
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
