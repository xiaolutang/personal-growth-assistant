import { useState, useCallback, useMemo, useEffect } from "react";
import { ChevronDown, ChevronRight, FolderOpen, Inbox, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { TaskCard } from "@/components/TaskCard";
import { DecisionCard } from "./DecisionCard";
import type { Task } from "@/types/task";
import { getProjectProgress, type ProjectProgressResponse } from "@/services/api";

interface GroupDef {
  id: string;
  project?: Task;
  title: string;
  tasks: Task[];
}

interface GroupedViewProps {
  tasks: Task[];
  selectable?: boolean;
  selectedIds?: Set<string>;
  onSelect?: (id: string) => void;
}

/** 进度条颜色 */
function getProgressColor(percentage: number): string {
  if (percentage > 80) return "bg-green-500";
  if (percentage >= 30) return "bg-blue-500";
  return "bg-gray-400";
}

/** Project group header with inline progress bar */
function ProjectGroupHeader({ project, taskCount }: { project: Task; taskCount: number }) {
  const [progress, setProgress] = useState<ProjectProgressResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getProjectProgress(project.id)
      .then((data) => { if (!cancelled) { setProgress(data); setLoading(false); } })
      .catch(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [project.id]);

  const completed = progress?.completed_tasks ?? 0;
  const total = progress?.total_tasks ?? 0;
  const pct = progress?.progress_percentage ?? 0;

  return (
    <div className="flex items-center gap-2 flex-1 min-w-0">
      <FolderOpen className="h-4 w-4 text-purple-500 dark:text-purple-400 flex-shrink-0" />
      <span className="text-sm font-medium truncate">{project.title}</span>
      {loading ? (
        <Loader2 className="h-3 w-3 animate-spin text-muted-foreground flex-shrink-0" />
      ) : total > 0 ? (
        <div className="flex items-center gap-2 flex-shrink-0">
          <div className="h-1.5 w-16 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
            <div
              className={cn("h-full rounded-full transition-all duration-300", getProgressColor(pct))}
              style={{ width: `${Math.min(pct, 100)}%` }}
            />
          </div>
          <span className="text-xs text-muted-foreground whitespace-nowrap">
            {completed}/{total}
          </span>
        </div>
      ) : null}
      <span className="text-xs text-muted-foreground ml-auto flex-shrink-0">
        {taskCount} 条
      </span>
    </div>
  );
}

/**
 * F08: Grouped view — groups entries by parent_id.
 * Project entries serve as group headers (with progress bar).
 * Entries without parent_id go into "独立任务".
 */
export function GroupedView({ tasks, selectable = false, selectedIds, onSelect }: GroupedViewProps) {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());

  // Build group definitions from the provided tasks
  const groups = useMemo<GroupDef[]>(() => {
    // Find all project entries from the given tasks
    const projectMap = new Map<string, Task>();

    // First pass: collect projects
    for (const task of tasks) {
      if (task.category === "project") {
        projectMap.set(task.id, task);
      }
    }

    const result: GroupDef[] = [];

    // Create project groups (only for projects that appear in tasks)
    for (const [projectId, project] of projectMap) {
      const children = tasks.filter(
        (t) => t.parent_id === projectId && t.category !== "project"
      );
      result.push({
        id: projectId,
        project,
        title: project.title,
        tasks: children,
      });
    }

    // Collect standalone tasks (no parent_id or parent not in current view)
    const standalone = tasks.filter(
      (t) => t.category !== "project" && (!t.parent_id || !projectMap.has(t.parent_id))
    );

    if (standalone.length > 0) {
      result.push({
        id: "__standalone__",
        title: "独立任务",
        tasks: standalone,
      });
    }

    return result;
  }, [tasks]);

  const toggleGroup = useCallback((groupId: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) next.delete(groupId);
      else next.add(groupId);
      return next;
    });
  }, []);

  if (tasks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-3">
        <Inbox className="h-10 w-10 opacity-30" />
        <p>暂无任务</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {groups.map((group) => {
        const isCollapsed = collapsed.has(group.id);
        return (
          <div key={group.id} data-testid="grouped-view-group">
            {/* Group header */}
            <button
              data-testid="grouped-view-toggle"
              onClick={() => toggleGroup(group.id)}
              className="w-full flex items-center gap-2 px-2 py-2 rounded-lg hover:bg-muted/50 transition-colors text-left"
            >
              {isCollapsed ? (
                <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
              ) : (
                <ChevronDown className="h-4 w-4 text-muted-foreground flex-shrink-0" />
              )}
              {group.project ? (
                <ProjectGroupHeader project={group.project} taskCount={group.tasks.length} />
              ) : (
                <>
                  <Inbox className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  <span className="text-sm font-medium truncate">{group.title}</span>
                  <span className="text-xs text-muted-foreground ml-auto flex-shrink-0">
                    {group.tasks.length} 条
                  </span>
                </>
              )}
            </button>

            {/* Group content */}
            {!isCollapsed && (
              <div className="ml-3 space-y-1 mt-1">
                {group.tasks.length === 0 && (
                  <p className="text-xs text-muted-foreground text-center py-2">暂无条目</p>
                )}
                {group.tasks.map((task) => {
                  if (task.category === "decision") {
                    return (
                      <DecisionCard
                        key={task.id}
                        decision={task}
                        selectable={selectable}
                        selected={selectedIds?.has(task.id)}
                        onSelect={onSelect}
                      />
                    );
                  }
                  return (
                    <TaskCard
                      key={task.id}
                      task={task}
                      showParent={false}
                      selectable={selectable}
                      selected={selectedIds?.has(task.id)}
                      onSelect={onSelect}
                      disableActions={false}
                    />
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
