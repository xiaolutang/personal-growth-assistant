import type { Task } from "@/types/task";
import { TaskCard } from "./TaskCard";

interface TaskListProps {
  tasks: Task[];
  emptyMessage?: string;
  highlightKeyword?: string;
}

export function TaskList({ tasks, emptyMessage = "暂无任务", highlightKeyword }: TaskListProps) {
  if (tasks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <p>{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {tasks.map((task) => (
        <TaskCard key={task.id} task={task} highlightKeyword={highlightKeyword} />
      ))}
    </div>
  );
}
