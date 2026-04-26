import { CheckCircle, Circle, Clock } from "lucide-react";
import type { TaskStatus } from "@/types/task";

interface TodayTaskItemProps {
  task: {
    id: string;
    title: string;
    status: TaskStatus;
  };
  isToggling: boolean;
  onToggle: (taskId: string, status: TaskStatus) => void;
}

export function TodayTaskItem({ task, isToggling, onToggle }: TodayTaskItemProps) {
  const isComplete = task.status === "complete";

  return (
    <div className="flex items-center gap-3 rounded-lg px-2 py-2 hover:bg-accent/30 transition-colors">
      <button
        onClick={() => onToggle(task.id, task.status)}
        disabled={isToggling}
        className={`shrink-0 transition-colors ${
          isToggling
            ? "opacity-50 cursor-not-allowed"
            : "cursor-pointer hover:scale-110"
        }`}
        aria-label={isComplete ? "标为未完成" : "标为完成"}
      >
        {isComplete ? (
          <CheckCircle className="h-5 w-5 text-green-500 dark:text-green-400" />
        ) : task.status === "doing" ? (
          <Clock className="h-5 w-5 text-yellow-500 dark:text-yellow-400" />
        ) : (
          <Circle className="h-5 w-5 text-muted-foreground" />
        )}
      </button>
      <span
        className={`text-sm flex-1 truncate ${
          isComplete ? "line-through text-muted-foreground" : ""
        }`}
      >
        {task.title}
      </span>
      {isToggling && (
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      )}
    </div>
  );
}
