import { useState, useEffect, useCallback } from "react";
import { FolderOpen, ChevronDown, ChevronUp, Clock, Loader2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Task } from "@/types/task";
import { useTaskStore } from "@/stores/taskStore";
import { getProjectProgress, type ProjectProgressResponse } from "@/services/api";
import { TaskCard } from "@/components/TaskCard";

interface ProjectCardProps {
  project: Task;
  layout?: "grid" | "compact";
  selectable?: boolean;
  selected?: boolean;
  onSelect?: (id: string) => void;
  /** F06: 自定义卡片点击回调（搜索模式下跳转到任务页） */
  onClickOverride?: (task: Task) => void;
}

/** 进度条颜色：>80% 绿色，30-80% 蓝色，<30% 灰色 */
function getProgressColor(percentage: number): string {
  if (percentage > 80) return "bg-green-500";
  if (percentage >= 30) return "bg-blue-500";
  return "bg-gray-400";
}

/** 格式化更新时间为可读字符串 */
function formatUpdatedTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "刚刚";
  if (diffMins < 60) return `${diffMins} 分钟前`;
  if (diffHours < 24) return `${diffHours} 小时前`;
  if (diffDays < 7) return `${diffDays} 天前`;
  return date.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
}

export function ProjectCard({ project, layout = "grid", selectable = false, selected = false, onSelect, onClickOverride }: ProjectCardProps) {
  const allTasks = useTaskStore((state) => state.tasks);
  const [expanded, setExpanded] = useState(false);
  const [progress, setProgress] = useState<ProjectProgressResponse | null>(null);
  const [progressError, setProgressError] = useState(false);
  const [progressLoading, setProgressLoading] = useState(true);

  // 获取进度数据
  useEffect(() => {
    let cancelled = false;
    setProgressLoading(true);
    setProgressError(false);
    getProjectProgress(project.id)
      .then((data) => {
        if (!cancelled) {
          setProgress(data);
          setProgressLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setProgressError(true);
          setProgressLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, [project.id]);

  // 从 store 中筛选子任务
  const subTasks = allTasks.filter((t) => t.parent_id === project.id);

  // 进度信息
  const completedCount = progress?.completed_tasks ?? 0;
  const totalCount = progress?.total_tasks ?? 0;
  const percentage = progress?.progress_percentage ?? 0;
  const hasNoSubTasks = totalCount === 0 && !progressLoading && !progressError;

  // 已加载不一致标注
  const loadedCount = subTasks.length;
  const showLoadedHint = !progressLoading && !progressError && totalCount > 0 && loadedCount !== totalCount && loadedCount > 0;

  const handleCardClick = useCallback(() => {
    if (selectable) {
      onSelect?.(project.id);
      return;
    }
    // F06: 搜索模式下支持自定义点击行为
    if (onClickOverride) {
      onClickOverride(project);
      return;
    }
  }, [selectable, onSelect, project.id, onClickOverride]);

  const handleToggleExpand = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setExpanded((prev) => !prev);
  }, []);

  // 渲染进度条区域
  const renderProgressBar = () => {
    if (progressLoading) {
      return (
        <div className="flex items-center gap-2 mt-2">
          <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
          <span className="text-xs text-muted-foreground">加载进度...</span>
        </div>
      );
    }

    if (progressError) {
      return (
        <div className="mt-2">
          <div className="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
            <div
              data-testid="progress-bar-fill"
              className="h-full rounded-full bg-gray-300 dark:bg-gray-600"
              style={{ width: "0%" }}
            />
          </div>
          <span className="text-xs text-muted-foreground mt-1">加载失败</span>
        </div>
      );
    }

    return (
      <div className="mt-2">
        <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
          <span>{completedCount}/{totalCount} 完成</span>
          <span>{percentage}%</span>
        </div>
        <div className="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
          <div
            data-testid="progress-bar-fill"
            className={cn("h-full rounded-full transition-all duration-300", getProgressColor(percentage))}
            style={{ width: `${Math.min(percentage, 100)}%` }}
          />
        </div>
      </div>
    );
  };

  // 共用的标题区域
  const renderHeader = () => (
    <div className="flex items-start gap-2">
      <FolderOpen className="h-4 w-4 text-purple-500 dark:text-purple-400 flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{project.title}</p>
      </div>
      {/* 更新时间 */}
      <div className="flex items-center gap-1 text-xs text-muted-foreground flex-shrink-0">
        <Clock className="h-3 w-3" />
        <span>{formatUpdatedTime(project.updated_at)}</span>
      </div>
    </div>
  );

  // 渲染展开的子任务列表
  const renderSubTasks = () => {
    if (!expanded) return null;

    return (
      <div className="mt-3 border-t pt-2 space-y-1">
        {hasNoSubTasks ? (
          <p className="text-xs text-muted-foreground text-center py-2">暂无子任务</p>
        ) : (
          <>
            {showLoadedHint && (
              <p className="text-xs text-muted-foreground mb-1">已加载 {loadedCount} 条</p>
            )}
            {subTasks.map((task) => (
              <TaskCard
                key={task.id}
                task={task}
                showParent={false}
                disableActions
              />
            ))}
            {subTasks.length === 0 && !hasNoSubTasks && (
              <p className="text-xs text-muted-foreground text-center py-2">暂无子任务</p>
            )}
          </>
        )}
      </div>
    );
  };

  // 展开/折叠按钮
  const renderExpandButton = () => (
    <button
      data-testid="expand-toggle"
      onClick={handleToggleExpand}
      className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors mt-1"
    >
      {expanded ? (
        <>
          <ChevronUp className="h-3 w-3" />
          <span>收起</span>
        </>
      ) : (
        <>
          <ChevronDown className="h-3 w-3" />
          <span>展开子任务</span>
        </>
      )}
    </button>
  );

  // ===== Grid 布局（项目子 Tab）=====
  if (layout === "grid") {
    return (
      <Card
        data-category="project"
        data-layout="grid"
        data-testid="project-card-body"
        className={cn(
          "px-4 py-3 cursor-pointer hover:bg-accent/50 transition-colors",
          selectable && selected && "bg-accent/30"
        )}
        onClick={handleCardClick}
      >
        {renderHeader()}
        {project.tags && project.tags.length > 0 && (
          <div className="flex items-center gap-1 mt-1 pl-6">
            {project.tags.slice(0, 3).map((tag) => (
              <Badge key={tag} variant="outline" className="text-[10px] px-1 h-4">
                {tag}
              </Badge>
            ))}
          </div>
        )}
        {renderProgressBar()}
        {renderExpandButton()}
        {renderSubTasks()}
      </Card>
    );
  }

  // ===== Compact 布局（全部子 Tab）=====
  return (
    <Card
      data-category="project"
      data-layout="compact"
      data-testid="project-card-body"
      className={cn(
        "px-3 py-2 cursor-pointer hover:bg-accent/50 transition-colors",
        selectable && selected && "bg-accent/30"
      )}
      onClick={handleCardClick}
    >
      <div className="flex items-center gap-3">
        <FolderOpen className="h-4 w-4 text-purple-500 dark:text-purple-400 flex-shrink-0" />
        <p className="text-sm font-medium truncate flex-1">{project.title}</p>

        {/* 紧凑进度 */}
        {progressLoading ? (
          <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
        ) : progressError ? (
          <span className="text-xs text-muted-foreground">加载失败</span>
        ) : (
          <div className="flex items-center gap-2 flex-shrink-0">
            <div className="h-1.5 w-16 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
              <div
                data-testid="progress-bar-fill"
                className={cn("h-full rounded-full transition-all duration-300", getProgressColor(percentage))}
                style={{ width: `${Math.min(percentage, 100)}%` }}
              />
            </div>
            <span className="text-xs text-muted-foreground whitespace-nowrap">
              {completedCount}/{totalCount}
            </span>
          </div>
        )}

        <div className="flex items-center gap-1 text-xs text-muted-foreground flex-shrink-0">
          <Clock className="h-3 w-3" />
          <span>{formatUpdatedTime(project.updated_at)}</span>
        </div>

        {/* 展开按钮 */}
        <button
          data-testid="expand-toggle"
          onClick={handleToggleExpand}
          className="flex-shrink-0 p-0.5 text-muted-foreground hover:text-primary transition-colors"
        >
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
      </div>

      {/* 展开的子任务 */}
      {expanded && (
        <div className="mt-2 border-t pt-2 space-y-1 ml-7">
          {hasNoSubTasks ? (
            <p className="text-xs text-muted-foreground text-center py-2">暂无子任务</p>
          ) : (
            <>
              {showLoadedHint && (
                <p className="text-xs text-muted-foreground mb-1">已加载 {loadedCount} 条</p>
              )}
              {subTasks.map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  showParent={false}
                  disableActions
                />
              ))}
              {subTasks.length === 0 && !hasNoSubTasks && (
                <p className="text-xs text-muted-foreground text-center py-2">暂无子任务</p>
              )}
            </>
          )}
        </div>
      )}
    </Card>
  );
}
