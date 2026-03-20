import { useState, useEffect, useRef } from 'react';
import { isoToDateTimeLocal, dateTimeLocalToISO } from '../lib/dateUtils';

interface Props {
  startTime: string | undefined;
  endTime: string | undefined;
  onChange: (start: string | undefined, end: string | undefined) => void;
}

type QuickRange = 'today' | 'yesterday' | 'week' | 'month';

export function TimeRangePicker({ startTime, endTime, onChange }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [tempStart, setTempStart] = useState('');
  const [tempEnd, setTempEnd] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);
  const isInteractingRef = useRef(false);

  // 同步外部值
  useEffect(() => {
    setTempStart(startTime ? isoToDateTimeLocal(startTime) : '');
    setTempEnd(endTime ? isoToDateTimeLocal(endTime) : '');
  }, [startTime, endTime]);

  // 点击外部关闭
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (isInteractingRef.current) {
        isInteractingRef.current = false;
        return;
      }
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  // 确认应用
  const handleConfirm = () => {
    const start = tempStart ? dateTimeLocalToISO(tempStart) : undefined;
    const end = tempEnd ? dateTimeLocalToISO(tempEnd) : undefined;
    onChange(start, end);
    setIsOpen(false);
  };

  // 快捷选择
  const handleQuickRange = (range: QuickRange) => {
    const now = new Date();
    let start: Date, end: Date;

    switch (range) {
      case 'today':
        start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
        end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
        break;
      case 'yesterday':
        start = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1, 0, 0, 0);
        end = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1, 23, 59, 59);
        break;
      case 'week':
        const dayOfWeek = now.getDay();
        const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
        start = new Date(now.getFullYear(), now.getMonth(), now.getDate() + mondayOffset, 0, 0, 0);
        end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
        break;
      case 'month':
        start = new Date(now.getFullYear(), now.getMonth(), 1, 0, 0, 0);
        end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
        break;
    }

    onChange(start.toISOString(), end.toISOString());
    setIsOpen(false);
  };

  // 清除
  const handleClear = () => {
    setTempStart('');
    setTempEnd('');
    onChange(undefined, undefined);
    setIsOpen(false);
  };

  // 显示文本
  const displayText = () => {
    if (!startTime && !endTime) return '选择时间范围';
    const start = startTime ? formatTime(startTime) : '不限';
    const end = endTime ? formatTime(endTime) : '不限';
    return `${start} - ${end}`;
  };

  return (
    <div ref={containerRef} className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1 border rounded px-2 py-1 text-xs bg-white hover:border-indigo-300 transition-colors"
      >
        <span>📅</span>
        <span>{displayText()}</span>
      </button>

      {isOpen && <div className="fixed inset-0 z-40" />}

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 bg-white border rounded-lg shadow-lg p-3 z-50 w-96">
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">开始时间</label>
              <input
                type="datetime-local"
                value={tempStart}
                onChange={(e) => setTempStart(e.target.value)}
                onFocus={() => { isInteractingRef.current = true; }}
                className="border rounded px-2 py-1 text-xs w-full relative z-50"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">结束时间</label>
              <input
                type="datetime-local"
                value={tempEnd}
                onChange={(e) => setTempEnd(e.target.value)}
                onFocus={() => { isInteractingRef.current = true; }}
                className="border rounded px-2 py-1 text-xs w-full relative z-50"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-1 relative z-50">
            <button onClick={() => handleQuickRange('today')} className="px-2 py-1 text-xs bg-gray-100 rounded hover:bg-gray-200">今天</button>
            <button onClick={() => handleQuickRange('yesterday')} className="px-2 py-1 text-xs bg-gray-100 rounded hover:bg-gray-200">昨天</button>
            <button onClick={() => handleQuickRange('week')} className="px-2 py-1 text-xs bg-gray-100 rounded hover:bg-gray-200">本周</button>
            <button onClick={() => handleQuickRange('month')} className="px-2 py-1 text-xs bg-gray-100 rounded hover:bg-gray-200">本月</button>
            <button onClick={handleClear} className="px-2 py-1 text-xs text-red-500 hover:text-red-600">清除</button>
            <button onClick={handleConfirm} className="ml-auto px-3 py-1 text-xs bg-indigo-500 text-white rounded hover:bg-indigo-600">确认</button>
          </div>
        </div>
      )}
    </div>
  );
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  const month = d.getMonth() + 1;
  const day = d.getDate();
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  return `${month}/${day} ${hours}:${minutes}`;
}
