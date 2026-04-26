import { Calendar, Tag, X } from "lucide-react";
import { TIME_RANGE_LABELS } from "./utils";
import type { TimeRange } from "./utils";

interface FilterBarProps {
  timeRange: TimeRange;
  setTimeRange: (r: TimeRange) => void;
  selectedTags: string[];
  onTagFilter: (tag: string) => void;
  onClearFilters: () => void;
  hasActiveFilters: boolean;
}

export function FilterBar({
  timeRange,
  setTimeRange,
  selectedTags,
  onTagFilter,
  onClearFilters,
  hasActiveFilters,
}: FilterBarProps) {
  return (
    <div className="mb-4 space-y-2">
      {/* 时间快选按钮组 */}
      <div className="flex items-center gap-1.5">
        <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
        {(["", "today", "week", "month"] as TimeRange[]).map((range) => (
          <button
            key={range}
            onClick={() => setTimeRange(range)}
            className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
              timeRange === range
                ? "bg-indigo-500 text-white"
                : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
            }`}
          >
            {TIME_RANGE_LABELS[range]}
          </button>
        ))}
      </div>

      {/* 过滤条件 chip */}
      {hasActiveFilters && (
        <div className="flex items-center gap-1.5 flex-wrap">
          {timeRange && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-xs font-medium">
              <Calendar className="h-3 w-3" />
              {TIME_RANGE_LABELS[timeRange]}
              <button onClick={() => setTimeRange("")} className="hover:text-indigo-800 dark:hover:text-indigo-200">
                <X className="h-3 w-3" />
              </button>
            </span>
          )}
          {selectedTags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 text-xs font-medium"
            >
              <Tag className="h-3 w-3" />
              #{tag}
              <button onClick={() => onTagFilter(tag)} className="hover:text-emerald-800 dark:hover:text-emerald-200">
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
          <button
            onClick={onClearFilters}
            className="px-2 py-0.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            全部清除
          </button>
        </div>
      )}
    </div>
  );
}
