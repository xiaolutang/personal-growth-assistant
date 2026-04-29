import { AlertTriangle } from "lucide-react";

interface OverdueBannerProps {
  count: number;
}

/**
 * F09: 逾期提醒条 — 显示在时间线视图顶部
 * 仅在有逾期任务时显示
 */
export function OverdueBanner({ count }: OverdueBannerProps) {
  if (count === 0) return null;

  return (
    <div
      data-testid="overdue-banner"
      className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-50 dark:bg-red-950/50 text-red-600 dark:text-red-400 text-sm mb-3"
    >
      <AlertTriangle className="h-4 w-4 flex-shrink-0" />
      <span>{count} 个任务已逾期</span>
    </div>
  );
}
