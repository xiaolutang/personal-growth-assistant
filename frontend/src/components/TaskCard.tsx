import { Circle, CheckCircle, Clock, Trash2, Pause, XCircle, Folder } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Task } from "@/types/task";
import { useTaskStore } from "@/stores/taskStore";
import { statusConfig, nextStatusMap, priorityConfig } from "@/config/constants";

interface TaskCardProps {
  task: Task;
  showParent?: boolean;
}

export function TaskCard({ task, showParent = true }: TaskCardProps) {
  const navigate = useNavigate();
  const { updateTaskStatus, deleteTask, tasks } = useTaskStore();
  const status = statusConfig[task.status];
  const priority = task.priority ? priorityConfig[task.priority] : null;

  // 查找父项目
  const parentProject = showParent && task.parent_id
    ? tasks.find(t => t.id === task.parent_id && t.category === "project")
    : null;

  const handleStatusChange = (e: React.MouseEvent) => {
    e.stopPropagation(); // 阻止冒泡，避免触发卡片点击
    updateTaskStatus(task.id, nextStatusMap[task.status]);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation(); // 阻止冒泡，避免触发卡片点击
    deleteTask(task.id);
  };

  const handleCardClick = () => {
    navigate(`/entries/${task.id}`);
  };

  // 渲染状态图标
  const renderStatusIcon = () => {
    switch (task.status) {
      case "complete":
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case "doing":
        return <Clock className="h-5 w-5 text-yellow-500" />;
      case "paused":
        return <Pause className="h-5 w-5 text-orange-500" />;
      case "cancelled":
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Circle className="h-5 w-5" />;
    }
  };

  return (
    <Card
      className="flex items-center gap-4 p-4 cursor-pointer hover:bg-accent/50 transition-colors"
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
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p
            className={cn(
              "text-sm font-medium truncate",
              (task.status === "complete" || task.status === "cancelled") && "line-through text-muted-foreground"
            )}
          >
            {task.title}
          </p>
          {/* Priority Badge */}
          {priority && task.priority !== "medium" && (
            <Badge variant={priority.variant} className="text-xs px-1.5">
              {priority.label}
            </Badge>
          )}
        </div>
        {task.content && (
          <p className="text-xs text-muted-foreground truncate mt-0.5">
            {task.content}
          </p>
        )}
        <div className="flex items-center gap-2 mt-1">
          {/* Parent Project */}
          {parentProject && (
            <span className="text-xs text-purple-500 flex items-center gap-1">
              <Folder className="h-3 w-3" />
              {parentProject.title}
            </span>
          )}
          {task.planned_date && (
            <span className="text-xs text-muted-foreground">
              {new Date(task.planned_date).toLocaleDateString("zh-CN", {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          )}
          {task.time_spent !== undefined && task.time_spent > 0 && (
            <span className="text-xs text-muted-foreground">
              耗时 {task.time_spent} 分钟
            </span>
          )}
        </div>
        {/* Tags */}
        {task.tags && task.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {task.tags.map((tag) => (
              <Badge key={tag} variant="outline" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        )}
      </div>

      {/* Status Badge */}
      <Badge variant={status.variant} className="flex-shrink-0">
        {status.label}
      </Badge>

      {/* Delete Button */}
      <Button
        variant="ghost"
        size="icon"
        className="flex-shrink-0 text-muted-foreground hover:text-destructive"
        onClick={handleDelete}
      >
        <Trash2 className="h-4 w-4" />
      </Button>
    </Card>
  );
}
