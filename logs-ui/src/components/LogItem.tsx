import type { LogEntry, LogLevel } from '../types/log';

interface Props {
  log: LogEntry;
  onClick: () => void;
  onRequestIdClick: (requestId: string) => void;
}

const levelColors: Record<LogLevel, string> = {
  DEBUG: 'bg-gray-100 text-gray-600',
  INFO: 'bg-blue-100 text-blue-700',
  WARNING: 'bg-orange-100 text-orange-700',
  ERROR: 'bg-red-100 text-red-700',
  CRITICAL: 'bg-red-200 text-red-800 font-bold',
};

const levelBorderColors: Record<LogLevel, string> = {
  DEBUG: 'border-l-gray-400',
  INFO: 'border-l-blue-500',
  WARNING: 'border-l-orange-500',
  ERROR: 'border-l-red-500',
  CRITICAL: 'border-l-red-700',
};

export function LogItem({ log, onClick, onRequestIdClick }: Props) {
  const time = new Date(log.timestamp).toLocaleString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  const truncateMessage = (msg: string, maxLen: number = 120) => {
    if (msg.length <= maxLen) return msg;
    return msg.slice(0, maxLen) + '...';
  };

  // 判断是否是 HTTP 请求日志
  const isHttpRequest = log.method && log.path;

  return (
    <div
      className={`bg-white rounded-lg p-3 shadow-sm border border-gray-100 border-l-4 cursor-pointer hover:shadow-md transition-shadow ${levelBorderColors[log.level]}`}
      onClick={onClick}
    >
      {/* 第一行：级别 + 时间 + Logger */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`px-2 py-0.5 rounded text-xs font-medium ${levelColors[log.level]}`}>
          {log.level}
        </span>
        <span className="text-xs text-gray-400">{time}</span>
        {log.logger_name && (
          <span className="text-xs text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
            {log.logger_name}
          </span>
        )}
      </div>

      {/* 第二行：消息内容 */}
      <div className="mt-1.5 text-sm text-gray-800 font-mono leading-relaxed">
        {truncateMessage(log.message)}
      </div>

      {/* 第三行：标签信息 */}
      <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-gray-500">
        {log.request_id && (
          <span
            className="bg-gray-100 px-1.5 py-0.5 rounded cursor-pointer hover:bg-gray-200 font-mono"
            onClick={(e) => {
              e.stopPropagation();
              onRequestIdClick(log.request_id!);
            }}
            title="点击筛选此请求"
          >
            #{log.request_id.slice(0, 8)}
          </span>
        )}
        {isHttpRequest && (
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
            {log.process_time_ms.toFixed(0)}ms
          </span>
        )}
        {log.client_ip && !isHttpRequest && (
          <span className="text-gray-400">
            {log.client_ip}
          </span>
        )}
      </div>
    </div>
  );
}
