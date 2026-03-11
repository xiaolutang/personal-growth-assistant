import { Circle, CheckCircle, Clock, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { Task, TaskStatus } from "@/types/task";
import { useTaskStore } from "@/stores/taskStore";

const statusConfig: Record<TaskStatus, { label: string; color: string }> = {
  waitStart: { label: "待开始", color: "bg-muted text-muted-foreground" },
  doing: { label: "进行中", color: "bg-warning/20 text-warning" },
  complete: { label: "已完成", color: "bg-success/20 text-success" },
};

interface TaskCardProps {
  task: Task;
}

export function TaskCard({ task }: TaskCardProps) {
  const { updateTaskStatus, deleteTask } = useTaskStore();
  const status = statusConfig[task.status];

  const handleStatusChange = () => {
    const nextStatus: Record<TaskStatus, TaskStatus> = {
      waitStart: "doing",
      doing: "complete",
      complete: "waitStart",
    };
    updateTaskStatus(task.id, nextStatus[task.status]);
  };

  return (
    <Card className="flex items-center gap-4 p-4">
      {/* Status Toggle */}
      <button
        onClick={handleStatusChange}
        className="flex-shrink-0 text-muted-foreground hover:text-primary transition-colors"
        aria-label="切换状态"
      >
        {task.status === "complete" ? (
          <CheckCircle className="h-5 w-5 text-success" />
        ) : task.status === "doing" ? (
          <Clock className="h-5 w-5 text-warning" />
        ) : (
          <Circle className="h-5 w-5" />
        )}
      </button>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p
          className={cn(
            "text-sm font-medium truncate",
            task.status === "complete" && "line-through text-muted-foreground"
          )}
        >
          {task.name}
        </p>
        {task.description && (
          <p className="text-xs text-muted-foreground truncate">
            {task.description}
          </p>
        )}
        {task.planned_date && (
          <p className="text-xs text-muted-foreground mt-1">
            {new Date(task.planned_date).toLocaleDateString("zh-CN", {
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        )}
      </div>

      {/* Status Badge */}
      <span
        className={cn(
          "flex-shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium",
          status.color
        )}
      >
        {status.label}
      </span>

      {/* Delete Button */}
      <Button
        variant="ghost"
        size="icon"
        className="flex-shrink-0 text-muted-foreground hover:text-destructive"
        onClick={() => deleteTask(task.id)}
      >
        <Trash2 className="h-4 w-4" />
      </Button>
    </Card>
  );
}
