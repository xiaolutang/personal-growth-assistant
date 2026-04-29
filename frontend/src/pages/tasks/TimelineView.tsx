import { useMemo } from "react";
import { Inbox } from "lucide-react";
import { TaskCard } from "@/components/TaskCard";
import { DecisionCard } from "./DecisionCard";
import { OverdueBanner } from "./OverdueBanner";
import { TIMELINE_GROUPS, type TimelineGroupKey } from "./constants";
import type { Task } from "@/types/task";

interface TimelineViewProps {
  tasks: Task[];
  selectable?: boolean;
  selectedIds?: Set<string>;
  onSelect?: (id: string) => void;
}

/** 判断一个日期字符串属于哪个时间线分组 */
function getTimelineGroup(plannedDate: string | undefined, taskStatus: string): TimelineGroupKey {
  // 已完成或已取消的不算逾期
  if (!plannedDate) return "noDate";

  const dateStr = plannedDate.split("T")[0];
  const now = new Date();
  const todayStr = now.toISOString().split("T")[0];

  // 逾期：日期 < 今天，且任务未完成
  if (dateStr < todayStr && taskStatus !== "complete" && taskStatus !== "cancelled") {
    return "overdue";
  }

  // 今天
  if (dateStr === todayStr) return "today";

  // 明天
  const tomorrow = new Date(now);
  tomorrow.setDate(now.getDate() + 1);
  const tomorrowStr = tomorrow.toISOString().split("T")[0];
  if (dateStr === tomorrowStr) return "tomorrow";

  // 本周（本周日 00:00 ~ 周六 23:59）
  const weekStart = new Date(now);
  weekStart.setDate(now.getDate() - now.getDay());
  weekStart.setHours(0, 0, 0, 0);
  const weekEnd = new Date(weekStart);
  weekEnd.setDate(weekStart.getDate() + 6);
  weekEnd.setHours(23, 59, 59, 999);

  const taskDate = new Date(dateStr + "T00:00:00");
  if (taskDate >= weekStart && taskDate <= weekEnd) return "thisWeek";

  // 下周
  const nextWeekStart = new Date(weekStart);
  nextWeekStart.setDate(weekStart.getDate() + 7);
  const nextWeekEnd = new Date(weekEnd);
  nextWeekEnd.setDate(weekEnd.getDate() + 7);
  if (taskDate >= nextWeekStart && taskDate <= nextWeekEnd) return "nextWeek";

  // 更远
  return "later";
}

/**
 * F09: 时间线视图 — 按 planned_date 分组显示任务
 * 分组：逾期 / 今天 / 明天 / 本周 / 下周 / 更远 / 未安排
 */
export function TimelineView({ tasks, selectable = false, selectedIds, onSelect }: TimelineViewProps) {
  // 过滤已取消的任务
  const activeTasks = useMemo(
    () => tasks.filter((t) => t.status !== "cancelled"),
    [tasks]
  );

  // 按 planned_date 分组
  const grouped = useMemo(() => {
    const map = new Map<TimelineGroupKey, Task[]>();
    for (const group of TIMELINE_GROUPS) {
      map.set(group.key, []);
    }

    for (const task of activeTasks) {
      const groupKey = getTimelineGroup(task.planned_date, task.status);
      map.get(groupKey)!.push(task);
    }

    return map;
  }, [activeTasks]);

  // 计算逾期数量
  const overdueCount = grouped.get("overdue")?.length ?? 0;

  // 过滤掉空分组，保留有任务的分组
  const visibleGroups = TIMELINE_GROUPS.filter(
    (g) => (grouped.get(g.key)?.length ?? 0) > 0
  );

  if (activeTasks.length === 0) {
    return (
      <div
        data-testid="timeline-empty"
        className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-3"
      >
        <Inbox className="h-10 w-10 opacity-30" />
        <p>暂无任务</p>
      </div>
    );
  }

  return (
    <div data-testid="timeline-view">
      {/* F09: 逾期提醒条 */}
      <OverdueBanner count={overdueCount} />

      {visibleGroups.map((group) => {
        const tasksInGroup = grouped.get(group.key) ?? [];
        const isOverdue = group.key === "overdue";

        return (
          <div
            key={group.key}
            data-testid={`timeline-group-${group.key}`}
            className="mb-4 last:mb-0"
          >
            {/* 分组标题 */}
            <div className="flex items-center gap-2 px-2 py-1.5 mb-1">
              <span
                className={
                  isOverdue
                    ? "text-sm font-medium text-red-500 dark:text-red-400"
                    : "text-sm font-medium text-muted-foreground"
                }
              >
                {group.label}
              </span>
              <span className="text-xs text-muted-foreground">
                {tasksInGroup.length}
              </span>
            </div>

            {/* 分组内容 */}
            <div className="space-y-1">
              {tasksInGroup.map((task) => {
                const cardContent =
                  task.category === "decision" ? (
                    <DecisionCard
                      key={task.id}
                      decision={task}
                      selectable={selectable}
                      selected={selectedIds?.has(task.id)}
                      onSelect={onSelect}
                    />
                  ) : (
                    <TaskCard
                      key={task.id}
                      task={task}
                      showParent={true}
                      selectable={selectable}
                      selected={selectedIds?.has(task.id)}
                      onSelect={onSelect}
                    />
                  );

                // 逾期条目红色左边框
                if (isOverdue) {
                  return (
                    <div
                      key={task.id}
                      data-testid="timeline-overdue-border"
                      className="border-l-4 border-red-500 dark:border-red-400 pl-2"
                    >
                      {cardContent}
                    </div>
                  );
                }

                return cardContent;
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
