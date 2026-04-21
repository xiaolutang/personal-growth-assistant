import type { Task } from "@/types/task";
import { TaskCard } from "./TaskCard";
import { Inbox } from "lucide-react";

interface TaskListProps {
  tasks: Task[];
  emptyMessage?: string;
  emptyIcon?: React.ReactNode;
  emptyAction?: { label: string; onClick: () => void };
  highlightKeyword?: string;
  selectable?: boolean;
  selectedIds?: Set<string>;
  onSelect?: (id: string) => void;
}

export function TaskList({ tasks, emptyMessage = "暂无任务", emptyIcon, emptyAction, highlightKeyword, selectable = false, selectedIds, onSelect }: TaskListProps) {
  if (tasks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-3">
        {emptyIcon || <Inbox className="h-10 w-10 opacity-30" />}
        <p>{emptyMessage}</p>
        {emptyAction && (
          <button
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm hover:bg-primary/90 transition-colors"
            onClick={emptyAction.onClick}
          >
            {emptyAction.label}
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {tasks.map((task) => (
        <TaskCard key={task.id} task={task} highlightKeyword={highlightKeyword} selectable={selectable} selected={selectedIds?.has(task.id)} onSelect={onSelect} />
      ))}
    </div>
  );
}
