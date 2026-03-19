import { Circle, CheckCircle, Clock, Trash2, Pause, XCircle, Folder } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Task } from "@/types/task";
import { useTaskStore } from "@/stores/taskStore";
import { nextStatusMap, priorityConfig } from "@/config/constants";

interface TaskCardProps {
  task: Task;
  showParent?: boolean;
}

export function TaskCard({ task, showParent = true }: TaskCardProps) {
  const navigate = useNavigate();
  const updateTaskStatus = useTaskStore((state) => state.updateTaskStatus);
  const deleteTask = useTaskStore((state) => state.deleteTask);
  const tasks = useTaskStore((state) => state.tasks);
  const priority = task.priority ? priorityConfig[task.priority] : null;

  // 查找父项目
  const parentProject = showParent && task.parent_id
    ? tasks.find(t => t.id === task.parent_id && t.category === "project")
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
    navigate(`/entries/${task.id}`);
  };

  // 渲染状态图标
  const renderStatusIcon = () => {
    switch (task.status) {
      case "complete":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "doing":
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case "paused":
        return <Pause className="h-4 w-4 text-orange-500" />;
      case "cancelled":
        return <XCircle className="h-4 w-4 text-red-500" />;
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
      className="flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-accent/50 transition-colors"
      onClick={handleCardClick}
    >
      {/* Status Toggle */}
      <button
        onClick={handleStatusChange}
        className="flex-shrink-0 text-muted-foreground hover:text-primary transition-colors"
        aria-label="切换状态"
      >
        {renderStatusIcon()}
      </button>

      {/* Content */}
      <div className="flex-1 min-w-0 flex items-center gap-2">
        {/* Title */}
        <p
          className={cn(
            "text-sm truncate flex-shrink-0 max-w-[200px]",
            (task.status === "complete" || task.status === "cancelled") && "line-through text-muted-foreground"
          )}
        >
          {task.title}
        </p>

        {/* Meta Info: parent, date, tags */}
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground flex-wrap">
          {parentProject && (
            <span className="flex items-center gap-0.5 text-purple-500">
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

      {/* Priority & Delete */}
      <div className="flex items-center gap-1 flex-shrink-0">
        {priority && task.priority !== "medium" && (
          <Badge variant={priority.variant} className="text-[10px] px-1 h-4">
            {priority.label}
          </Badge>
        )}
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 text-muted-foreground hover:text-destructive"
          onClick={handleDelete}
        >
          <Trash2 className="h-3 w-3" />
        </Button>
      </div>
    </Card>
  );
}
