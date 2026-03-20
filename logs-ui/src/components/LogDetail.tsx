import type { LogEntry, LogLevel } from '../types/log';

interface Props {
  log: LogEntry | null;
  onClose: () => void;
}

const levelColors: Record<LogLevel, string> = {
  DEBUG: 'bg-gray-100 text-gray-600',
  INFO: 'bg-blue-100 text-blue-700',
  WARNING: 'bg-orange-100 text-orange-700',
  ERROR: 'bg-red-100 text-red-700',
  CRITICAL: 'bg-red-200 text-red-800 font-bold',
};

export function LogDetail({ log, onClose }: Props) {
  if (!log) return null;

  const copyToClipboard = () => {
    const text = JSON.stringify(log, null, 2);
    navigator.clipboard.writeText(text);
  };

  const formatTime = (ts: string) => {
    return new Date(ts).toLocaleString('zh-CN');
  };

  // 判断是否是 HTTP 请求日志
  const isHttpRequest = log.method && log.path;

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 头部 */}
        <div className="flex items-center justify-between p-4 border-b bg-gray-50">
          <div className="flex items-center gap-2">
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${levelColors[log.level]}`}>
              {log.level}
            </span>
            <span className="text-sm text-gray-500">{formatTime(log.timestamp)}</span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={copyToClipboard}
              className="text-sm text-gray-500 hover:text-gray-700 px-2 py-1 rounded hover:bg-gray-100"
            >
              复制 JSON
            </button>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-xl leading-none"
            >
              ×
            </button>
          </div>
        </div>

        {/* 内容 */}
        <div className="p-4 overflow-auto flex-1">
          {/* 消息 */}
          <div className="mb-4">
            <div className="text-xs text-gray-500 mb-1 font-medium">消息</div>
            <div className="bg-gray-50 p-3 rounded font-mono text-sm whitespace-pre-wrap break-all">
              {log.message}
            </div>
          </div>

          {/* HTTP 请求信息 */}
          {isHttpRequest && (
            <div className="mb-4 p-3 bg-indigo-50 rounded-lg">
              <div className="text-xs text-indigo-600 font-medium mb-2">HTTP 请求</div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-gray-500">方法:</span>
                  <span className="ml-1 font-mono font-medium">{log.method}</span>
                </div>
                <div>
                  <span className="text-gray-500">状态:</span>
                  <span className={`ml-1 font-medium ${log.status_code && log.status_code >= 400 ? 'text-red-600' : 'text-green-600'}`}>
                    {log.status_code}
                  </span>
                </div>
                <div className="col-span-2">
                  <span className="text-gray-500">路径:</span>
                  <span className="ml-1 font-mono">{log.path}</span>
                </div>
                {log.client_ip && (
                  <div>
                    <span className="text-gray-500">客户端:</span>
                    <span className="ml-1 font-mono">{log.client_ip}</span>
                  </div>
                )}
                {log.process_time_ms != null && (
                  <div>
                    <span className="text-gray-500">耗时:</span>
                    <span className="ml-1">{log.process_time_ms.toFixed(2)}ms</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 堆栈信息 */}
          {log.stack_trace && (
            <div className="mb-4">
              <div className="text-xs text-red-600 mb-1 font-medium">堆栈信息</div>
              <div className="bg-red-50 p-3 rounded font-mono text-xs text-red-700 whitespace-pre-wrap overflow-x-auto max-h-48">
                {log.stack_trace}
              </div>
            </div>
          )}

          {/* 基本信息 */}
          <div className="grid grid-cols-2 gap-3 text-sm mb-4">
            {log.logger_name && (
              <div>
                <span className="text-gray-500">Logger:</span>
                <span className="ml-1 font-mono text-xs bg-gray-100 px-1 py-0.5 rounded">{log.logger_name}</span>
              </div>
            )}
            {log.request_id && (
              <div>
                <span className="text-gray-500">Request ID:</span>
                <span className="ml-1 font-mono text-xs">{log.request_id}</span>
              </div>
            )}
          </div>

          {/* 额外信息 */}
          {log.extra && Object.keys(log.extra).length > 0 && (
            <div>
              <div className="text-xs text-gray-500 mb-1 font-medium">额外信息</div>
              <div className="bg-gray-50 p-3 rounded font-mono text-xs overflow-x-auto">
                <pre>{JSON.stringify(log.extra, null, 2)}</pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
