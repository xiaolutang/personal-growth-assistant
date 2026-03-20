import type { LogStats } from '../types/log';

interface Props {
  stats: LogStats | null;
}

export function StatsCard({ stats }: Props) {
  if (!stats) return null;

  const items = [
    { label: '总数', value: stats.total_count, color: 'text-gray-700' },
    { label: 'DEBUG', value: stats.count_by_level.DEBUG || 0, color: 'text-gray-500' },
    { label: 'INFO', value: stats.count_by_level.INFO || 0, color: 'text-blue-600' },
    { label: 'WARNING', value: stats.count_by_level.WARNING || 0, color: 'text-orange-500' },
    { label: 'ERROR', value: stats.count_by_level.ERROR || 0, color: 'text-red-600' },
    { label: 'CRITICAL', value: stats.count_by_level.CRITICAL || 0, color: 'text-red-700 font-bold' },
    { label: 'DB大小', value: `${(stats.db_size_mb ?? 0).toFixed(2)} MB`, color: 'text-gray-600' },
  ];

  return (
    <div className="grid grid-cols-4 md:grid-cols-7 gap-3 mb-4">
      {items.map((item) => (
        <div
          key={item.label}
          className="bg-white rounded-lg p-3 shadow-sm border border-gray-100"
        >
          <div className="text-xs text-gray-500">{item.label}</div>
          <div className={`text-lg font-semibold ${item.color}`}>{item.value}</div>
        </div>
      ))}
    </div>
  );
}
