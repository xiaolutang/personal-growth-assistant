import { useState, useRef, useEffect } from "react";
import { Circle, CheckCircle, Clock, Trash2, Pause, XCircle, Folder, ArrowRightCircle, Scale, CheckSquare, Square, Calendar, AlertTriangle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Task } from "@/types/task";
import { useTaskStore } from "@/stores/taskStore";
import { nextStatusMap, priorityConfig } from "@/config/constants";
import { getDueDateInfo } from "@/lib/dueDate";
import { ConvertDialog } from "@/pages/explore/ConvertDialog";
import { CompletionPrompt } from "@/pages/tasks/CompletionPrompt";

interface TaskCardProps {
  task: Task;
  showParent?: boolean;
  highlightKeyword?: string;
  selectable?: boolean;
  selected?: boolean;
  onSelect?: (id: string) => void;
  disableActions?: boolean;
  /** F06: 自定义卡片点击回调（搜索模式下用于 task 跳转到任务页） */
  onClickOverride?: (task: Task) => void;
  /** F07: 转化成功后的回调（用于从列表移除卡片） */
  onConvertSuccess?: (task: Task) => void;
}

/** UTF-8 安全截取：确保不在 surrogate pair 中间断断 */
export function safeTruncate(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text;
  // 使用 Array.from 按码点拆分，避免在 surrogate pair 中间截断
  const chars = Array.from(text);
  if (chars.length <= maxLen) return text;
  return chars.slice(0, maxLen).join("") + "...";
}

/** 高亮文本中所有匹配的关键词（大小写不敏感，索引安全） */
function HighlightText({ text, keyword }: { text: string; keyword: string }) {
  if (!keyword) return <>{text}</>;
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const regex = new RegExp(escaped, "gi");
  const matches = [...text.matchAll(regex)];
  if (matches.length === 0) return <>{text}</>;
  const parts: (string | React.ReactElement)[] = [];
  let lastIndex = 0;
  for (const m of matches) {
    if (m.index > lastIndex) parts.push(text.slice(lastIndex, m.index));
    parts.push(
      <mark key={m.index} className="bg-yellow-200 dark:bg-yellow-800 rounded px-0.5">
        {m[0]}
      </mark>
    );
    lastIndex = m.index + m[0].length;
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex));
  return <>{parts}</>;
}

export function TaskCard({ task, showParent = true, highlightKeyword, selectable = false, selected = false, onSelect, disableActions = false, onClickOverride, onConvertSuccess }: TaskCardProps) {
  const navigate = useNavigate();
  const updateTaskStatus = useTaskStore((state) => state.updateTaskStatus);
  const deleteTask = useTaskStore((state) => state.deleteTask);
  const tasks = useTaskStore((state) => state.tasks);
  const priority = task.priority ? priorityConfig[task.priority] : null;

  // F07: ConvertDialog 状态
  const [convertDialogOpen, setConvertDialogOpen] = useState(false);
  const [convertTarget, setConvertTarget] = useState<"task" | "decision">("task");
  // 条目消失动画
  const [isVisible, setIsVisible] = useState(true);
  const animTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  // F10: 复盘提示状态 — 记录已跳过提示的 task id，避免重复弹出
  const [dismissedPromptIds, setDismissedPromptIds] = useState<Set<string>>(new Set());
  const showCompletionPrompt = task.status === "complete" && !dismissedPromptIds.has(task.id);

  // 清理动画 timer
  useEffect(() => {
    return () => {
      if (animTimerRef.current) clearTimeout(animTimerRef.current);
    };
  }, []);

  // 查找父项目
  const parentProject = showParent && task.parent_id
    ? tasks.find(t => t.id === task.parent_id && t.category === "project")
    : null;

  // 搜索模式下展示内容摘要（截取前 100 字符）
  const snippetText = highlightKeyword
    ? safeTruncate(task.content_snippet || task.content || "", 100)
    : null;

  const handleStatusChange = (e: React.MouseEvent) => {
    e.stopPropagation();
    updateTaskStatus(task.id, nextStatusMap[task.status]);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    deleteTask(task.id);
  };

  const handleCardClick = () => {
    if (selectable) {
      onSelect?.(task.id);
      return;
    }
    // F06: 搜索模式下支持自定义点击行为（如 task 类型跳转到任务页）
    if (onClickOverride) {
      onClickOverride(task);
      return;
    }
    navigate(`/entries/${task.id}`);
  };

  // F07: 打开 ConvertDialog
  const handleOpenConvert = (e: React.MouseEvent, target: "task" | "decision") => {
    e.stopPropagation();
    setConvertTarget(target);
    setConvertDialogOpen(true);
  };

  const handleConvertSuccess = () => {
    setIsVisible(false);
    // 动画后通知父组件移除
    animTimerRef.current = setTimeout(() => {
      onConvertSuccess?.(task);
    }, 300);
  };

  // 渲染状态图标
  const renderStatusIcon = () => {
    switch (task.status) {
      case "complete":
        return <CheckCircle className="h-4 w-4 text-green-500 dark:text-green-400" />;
      case "doing":
        return <Clock className="h-4 w-4 text-yellow-500 dark:text-yellow-400" />;
      case "paused":
        return <Pause className="h-4 w-4 text-orange-500 dark:text-orange-400" />;
      case "cancelled":
        return <XCircle className="h-4 w-4 text-red-500 dark:text-red-400" />;
      default:
        return <Circle className="h-4 w-4" />;
    }
  };

  // 截止日期状态判断
  const dueDateResult = getDueDateInfo(task.planned_date);
  const dueDateInfo = dueDateResult.status !== "none"
    ? { isOverdue: dueDateResult.status === "overdue", isDueToday: dueDateResult.status === "today", displayText: dueDateResult.label, plannedDateStr: dueDateResult.dateStr! }
    : null;

  // 标签最多显示2个
  const displayTags = task.tags?.slice(0, 2) || [];
  const remainingTags = (task.tags?.length || 0) - 2;

  return (
    <>
    <Card
      className={cn(
        "flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-accent/50 transition-colors",
        selectable && selected && "bg-accent/30",
        !isVisible && "opacity-0 scale-95 transition-all duration-300"
      )}
      onClick={handleCardClick}
    >
      {/* Selection checkbox (only in selectable mode) */}
      {selectable && (
        <div className="flex-shrink-0 flex items-center justify-center min-h-[44px] min-w-[32px]">
          {selected ? (
            <CheckSquare className="h-5 w-5 text-primary" />
          ) : (
            <Square className="h-5 w-5 text-muted-foreground" />
          )}
        </div>
      )}

      {/* Status Toggle */}
      <button
        onClick={handleStatusChange}
        className="flex-shrink-0 text-muted-foreground hover:text-primary transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center -m-1 p-1"
        aria-label="切换状态"
        disabled={disableActions}
      >
        {renderStatusIcon()}
      </button>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          {/* Title */}
          <p
            className={cn(
              "text-sm truncate flex-shrink-0 max-w-[200px]",
              (task.status === "complete" || task.status === "cancelled") && "line-through text-muted-foreground"
            )}
          >
            {highlightKeyword
              ? <HighlightText text={task.title} keyword={highlightKeyword} />
              : task.title
            }
          </p>
        </div>
        {/* Content snippet (search results only) */}
        {snippetText && (
          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
            <HighlightText text={snippetText} keyword={highlightKeyword!} />
          </p>
        )}

        {/* Meta Info: parent, date, tags */}
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground flex-wrap">
          {parentProject && (
            <span className="flex items-center gap-0.5 text-purple-500 dark:text-purple-400">
              <Folder className="h-3 w-3" />
              <span className="truncate max-w-[80px]">{parentProject.title}</span>
            </span>
          )}
          {dueDateInfo && (
            <span
              className={cn(
                "flex items-center gap-0.5",
                dueDateInfo.isOverdue && "text-red-500 dark:text-red-400",
                dueDateInfo.isDueToday && "text-amber-500 dark:text-amber-400",
                !dueDateInfo.isOverdue && !dueDateInfo.isDueToday && "text-muted-foreground"
              )}
              data-testid="due-date-badge"
            >
              {dueDateInfo.isOverdue ? (
                <AlertTriangle className="h-3 w-3" />
              ) : (
                <Calendar className="h-3 w-3" />
              )}
              {dueDateInfo.displayText}
            </span>
          )}
          {displayTags.map((tag) => (
            <Badge key={tag} variant="outline" className="text-[10px] px-1 h-4">
              {tag}
            </Badge>
          ))}
          {remainingTags > 0 && (
            <span className="text-[10px]">+{remainingTags}</span>
          )}
        </div>
      </div>

      {/* Priority & Actions */}
      <div className="flex items-center gap-1 flex-shrink-0">
        {priority && (
          <Badge variant={priority.variant} className="text-[10px] px-1 h-4">
            {priority.label}
          </Badge>
        )}
        {/* F07: Inbox 转化快捷按钮 */}
        {!disableActions && task.category === "inbox" && (
          <>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 min-h-[44px] min-w-[44px] text-muted-foreground hover:text-blue-500 dark:hover:text-blue-400"
              onClick={(e) => handleOpenConvert(e, "task")}
              title="转为任务"
            >
              <ArrowRightCircle className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 min-h-[44px] min-w-[44px] text-muted-foreground hover:text-amber-500 dark:hover:text-amber-400"
              onClick={(e) => handleOpenConvert(e, "decision")}
              title="转为决策"
            >
              <Scale className="h-3.5 w-3.5" />
            </Button>
          </>
        )}
        {!disableActions && (
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 min-h-[44px] min-w-[44px] text-muted-foreground hover:text-destructive"
            onClick={handleDelete}
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        )}
      </div>

      {/* F07: ConvertDialog */}
      {task.category === "inbox" && (
        <ConvertDialog
          open={convertDialogOpen}
          onClose={() => setConvertDialogOpen(false)}
          onSuccess={handleConvertSuccess}
          entry={task}
          defaultTarget={convertTarget}
        />
      )}
    </Card>

      {/* F10: 完成复盘提示 */}
      {showCompletionPrompt && (
        <CompletionPrompt
          task={task}
          onDismiss={() => {
            setDismissedPromptIds((prev) => new Set(prev).add(task.id));
          }}
        />
      )}
    </>
  );
}
