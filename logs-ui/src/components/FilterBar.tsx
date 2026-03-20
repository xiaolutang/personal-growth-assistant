import type { LogFilter, LogLevel } from '../types/log';
import { TimeRangePicker } from './TimeRangePicker';

interface Props {
  filter: LogFilter;
  onFilterChange: (filter: LogFilter) => void;
  onRefresh: () => void;
}

const LEVELS: (LogLevel | 'ALL')[] = ['ALL', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];
const PAGE_SIZES = [20, 50, 100, 200];
const ORDERS: { value: 'desc' | 'asc'; label: string }[] = [
  { value: 'desc', label: '最新优先' },
  { value: 'asc', label: '最早优先' },
];

export function FilterBar({ filter, onFilterChange, onRefresh }: Props) {
  const handleLevelChange = (level: LogLevel | 'ALL') => {
    onFilterChange({
      ...filter,
      level: level === 'ALL' ? undefined : level,
      offset: 0,
    });
  };

  const handleTimeChange = (start: string | undefined, end: string | undefined) => {
    onFilterChange({
      ...filter,
      start_time: start,
      end_time: end,
      offset: 0,
    });
  };

  const handleKeywordChange = (keyword: string) => {
    onFilterChange({
      ...filter,
      keyword: keyword || undefined,
      offset: 0,
    });
  };

  const handleRequestIdChange = (requestId: string) => {
    onFilterChange({
      ...filter,
      request_id: requestId || undefined,
      offset: 0,
    });
  };

  const handlePageSizeChange = (size: number) => {
    onFilterChange({
      ...filter,
      limit: size,
      offset: 0,
    });
  };

  const handleOrderChange = (order: 'desc' | 'asc') => {
    onFilterChange({
      ...filter,
      order,
      offset: 0,
    });
  };

  return (
    <div className="bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-6xl mx-auto px-4 py-3">
        {/* 第一行: 级别 + 时间 + 排序 */}
        <div className="flex flex-wrap items-center gap-4 mb-3">
          {/* 日志级别 */}
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-500 mr-1">级别:</span>
            {LEVELS.map((level) => (
              <button
                key={level}
                onClick={() => handleLevelChange(level)}
                className={`px-2 py-0.5 text-xs rounded transition-colors ${
                  (level === 'ALL' ? !filter.level : filter.level === level)
                    ? 'bg-indigo-500 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {level}
              </button>
            ))}
          </div>

          {/* 时间范围选择器 */}
          <TimeRangePicker
            startTime={filter.start_time}
            endTime={filter.end_time}
            onChange={handleTimeChange}
          />

          {/* 排序 */}
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-500 mr-1">排序:</span>
            {ORDERS.map((item) => (
              <button
                key={item.value}
                onClick={() => handleOrderChange(item.value)}
                className={`px-2 py-0.5 text-xs rounded transition-colors ${
                  filter.order === item.value
                    ? 'bg-indigo-500 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {/* 第二行: 搜索 + 每页数量 */}
        <div className="flex flex-wrap items-center gap-3">
          {/* 关键词搜索 */}
          <input
            type="text"
            placeholder="搜索关键词..."
            value={filter.keyword || ''}
            onChange={(e) => handleKeywordChange(e.target.value)}
            className="border rounded px-3 py-1.5 text-sm w-48"
          />

          {/* 请求 ID */}
          <input
            type="text"
            placeholder="请求 ID..."
            value={filter.request_id || ''}
            onChange={(e) => handleRequestIdChange(e.target.value)}
            className="border rounded px-3 py-1.5 text-sm w-40 font-mono"
          />

          {/* 每页数量 */}
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-500">每页:</span>
            <select
              value={filter.limit || 50}
              onChange={(e) => handlePageSizeChange(Number(e.target.value))}
              className="border rounded px-2 py-1 text-sm"
            >
              {PAGE_SIZES.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </div>

          {/* 刷新按钮 */}
          <button
            onClick={onRefresh}
            className="px-3 py-1.5 text-sm bg-indigo-500 text-white rounded hover:bg-indigo-600 transition-colors"
          >
            刷新
          </button>
        </div>
      </div>
    </div>
  );
}
