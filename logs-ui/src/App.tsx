import { useState, useEffect, useCallback } from 'react';
import { useLogs } from './hooks/useLogs';
import { FilterBar } from './components/FilterBar';
import { LogList } from './components/LogList';
import { StatsCard } from './components/StatsCard';
import { LogDetail } from './components/LogDetail';
import type { LogFilter, LogEntry } from './types/log';
import { getTodayISORange } from './lib/dateUtils';

const DEFAULT_PAGE_SIZE = 50;

function App() {
  const { logs, stats, total, loading, error, fetchLogs, fetchStats } = useLogs();

  // 默认选中今天的时间范围
  const [filter, setFilter] = useState<LogFilter>(() => {
    const today = getTodayISORange();
    return {
      limit: DEFAULT_PAGE_SIZE,
      offset: 0,
      order: 'desc',
      start_time: today.start_time,
      end_time: today.end_time,
    };
  });
  const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null);
  const [jumpPage, setJumpPage] = useState('');

  const loadData = useCallback(() => {
    fetchLogs(filter);
    fetchStats();
  }, [filter, fetchLogs, fetchStats]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleFilterChange = (newFilter: LogFilter) => {
    setFilter(newFilter);
  };

  const handleRequestIdClick = (requestId: string) => {
    setFilter((prev) => ({
      ...prev,
      request_id: requestId,
      offset: 0,
    }));
  };

  const currentPage = Math.floor(filter.offset / filter.limit) + 1;
  const totalPages = Math.ceil(total / filter.limit);

  const handlePageChange = (page: number) => {
    const offset = (page - 1) * filter.limit;
    setFilter((prev) => ({ ...prev, offset }));
  };

  const handleJumpPage = () => {
    const page = parseInt(jumpPage, 10);
    if (page >= 1 && page <= totalPages) {
      handlePageChange(page);
      setJumpPage('');
    }
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* 固定头部区域 */}
      <div className="flex-shrink-0">
        {/* 标题 */}
        <div className="bg-white border-b border-gray-200">
          <div className="max-w-6xl mx-auto px-4 py-3">
            <h1 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
              <span>📋</span>
              日志监控
            </h1>
          </div>
        </div>

        {/* 统计卡片 */}
        <div className="max-w-6xl mx-auto px-4 pt-4">
          <StatsCard stats={stats} />
        </div>

        {/* 筛选栏 */}
        <FilterBar
          filter={filter}
          onFilterChange={handleFilterChange}
          onRefresh={loadData}
        />
      </div>

      {/* 可滚动内容区域 */}
      <div className="flex-1 overflow-auto">
        <div className="max-w-6xl mx-auto px-4 pb-4">
          {/* 日志列表 */}
          <LogList
            logs={logs}
            loading={loading}
            error={error}
            onLogClick={setSelectedLog}
            onRequestIdClick={handleRequestIdClick}
          />
        </div>
      </div>

      {/* 固定底部 - 分页控制 */}
      {totalPages > 1 && (
        <div className="flex-shrink-0 bg-white border-t border-gray-200 shadow-lg">
          <div className="max-w-6xl mx-auto px-4 py-3">
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={() => handlePageChange(1)}
                disabled={currentPage === 1}
                className="px-2 py-1 text-sm bg-white border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                首页
              </button>
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="px-3 py-1 text-sm bg-white border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                上一页
              </button>

              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">
                  {currentPage} / {totalPages}
                </span>
                <span className="text-gray-300">|</span>
                <span className="text-sm text-gray-500">共 {total} 条</span>
              </div>

              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="px-3 py-1 text-sm bg-white border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                下一页
              </button>
              <button
                onClick={() => handlePageChange(totalPages)}
                disabled={currentPage === totalPages}
                className="px-2 py-1 text-sm bg-white border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                末页
              </button>

              {/* 跳转指定页 */}
              <div className="flex items-center gap-1 ml-2">
                <input
                  type="number"
                  min={1}
                  max={totalPages}
                  value={jumpPage}
                  onChange={(e) => setJumpPage(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleJumpPage()}
                  placeholder="页码"
                  className="w-14 border rounded px-2 py-1 text-sm text-center"
                />
                <button
                  onClick={handleJumpPage}
                  className="px-2 py-1 text-sm bg-indigo-500 text-white rounded hover:bg-indigo-600"
                >
                  跳转
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 日志详情弹窗 */}
      <LogDetail log={selectedLog} onClose={() => setSelectedLog(null)} />
    </div>
  );
}

export default App;
