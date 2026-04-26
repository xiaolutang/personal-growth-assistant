import { useState, useRef, useEffect } from "react";
import { Circle, CheckCircle, Clock, Trash2, Pause, XCircle, Folder, MoreHorizontal, Loader2, ArrowRightCircle, FileText, CheckSquare, Square } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Task, Category } from "@/types/task";
import { useTaskStore } from "@/stores/taskStore";
import { nextStatusMap, priorityConfig } from "@/config/constants";
import { toast } from "sonner";

interface TaskCardProps {
  task: Task;
  showParent?: boolean;
  highlightKeyword?: string;
  selectable?: boolean;
  selected?: boolean;
  onSelect?: (id: string) => void;
  disableActions?: boolean;
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

export function TaskCard({ task, showParent = true, highlightKeyword, selectable = false, selected = false, onSelect, disableActions = false }: TaskCardProps) {
  const navigate = useNavigate();
  const updateTaskStatus = useTaskStore((state) => state.updateTaskStatus);
  const deleteTask = useTaskStore((state) => state.deleteTask);
  const storeUpdateEntry = useTaskStore((state) => state.updateEntry);
  const tasks = useTaskStore((state) => state.tasks);
  const priority = task.priority ? priorityConfig[task.priority] : null;

  // 灵感转化相关状态（条目级）
  const [menuOpen, setMenuOpen] = useState(false);
  const [converting, setConverting] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // 点击外部关闭菜单
  useEffect(() => {
    if (!menuOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [menuOpen]);

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
    navigate(`/entries/${task.id}`);
  };

  // 灵感转化处理
  const handleConvert = async (e: React.MouseEvent, targetCategory: Category) => {
    e.stopPropagation();
    setMenuOpen(false);
    setConverting(true);
    try {
      await storeUpdateEntry(task.id, { category: targetCategory });
      const label = targetCategory === "task" ? "任务" : "笔记";
      toast.success(`已转为${label}：${task.title}`);
    } catch {
      toast.error("转化失败，请重试");
      setConverting(false);
    }
  };

  const handleMenuToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    setMenuOpen((prev) => !prev);
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

  // 格式化日期
  const formatDate = () => {
    if (!task.planned_date) return null;
    const date = new Date(task.planned_date);
    const today = new Date();
    const isToday = date.toDateString() === today.toDateString();
    if (isToday) {
      return date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
    }
    return date.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
  };

  // 标签最多显示2个
  const displayTags = task.tags?.slice(0, 2) || [];
  const remainingTags = (task.tags?.length || 0) - 2;

  return (
    <Card
      className={cn(
        "flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-accent/50 transition-colors",
        selectable && selected && "bg-accent/30"
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
          {formatDate() && <span>{formatDate()}</span>}
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
        {priority && task.priority !== "medium" && (
          <Badge variant={priority.variant} className="text-[10px] px-1 h-4">
            {priority.label}
          </Badge>
        )}
        {/* Inbox 转化菜单 */}
        {!disableActions && task.category === "inbox" && (
          <div className="relative" ref={menuRef}>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 text-muted-foreground hover:text-primary"
              onClick={handleMenuToggle}
              disabled={converting}
            >
              {converting ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <MoreHorizontal className="h-3 w-3" />
              )}
            </Button>
            {menuOpen && !converting && (
              <div className="absolute right-0 top-full mt-1 z-50 min-w-[140px] rounded-lg border bg-popover p-1 shadow-md">
                <button
                  className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent transition-colors"
                  onClick={(e) => handleConvert(e, "task")}
                >
                  <ArrowRightCircle className="h-3.5 w-3.5 text-blue-500 dark:text-blue-400" />
                  <span>转为任务</span>
                </button>
                <button
                  className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent transition-colors"
                  onClick={(e) => handleConvert(e, "note")}
                >
                  <FileText className="h-3.5 w-3.5 text-green-500 dark:text-green-400" />
                  <span>转为笔记</span>
                </button>
              </div>
            )}
          </div>
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
    </Card>
  );
}
