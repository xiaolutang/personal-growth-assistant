import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { RotateCcw, Loader2 } from "lucide-react";
import { useTaskStore } from "@/stores/taskStore";
import type { Task } from "@/types/task";

interface CompletionPromptProps {
  task: Task;
  onDismiss: () => void;
}

export function CompletionPrompt({ task, onDismiss }: CompletionPromptProps) {
  const navigate = useNavigate();
  const createEntry = useTaskStore((state) => state.createEntry);
  const [isCreating, setIsCreating] = useState(false);

  // 仅在 task 状态为 complete 时显示
  if (task.status !== "complete") return null;

  const handleWriteReflection = async () => {
    setIsCreating(true);
    try {
      const reflection = await createEntry({
        type: "reflection",
        title: `关于「${task.title}」的复盘`,
        parent_id: task.id,
      });
      toast.success("复盘已创建");
      onDismiss();
      navigate(`/explore?type=reflection&entry_id=${reflection.id}`);
    } catch {
      toast.error("创建复盘失败，请重试");
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="fixed inset-x-0 bottom-20 z-50 flex justify-center pointer-events-none px-4">
      <div className="pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl bg-white dark:bg-gray-800 shadow-lg border border-gray-200 dark:border-gray-700">
        <RotateCcw className="h-5 w-5 text-teal-500 dark:text-teal-400 shrink-0" />
        <span className="text-sm font-medium">写个复盘？</span>
        <div className="flex gap-2">
          <button
            onClick={handleWriteReflection}
            disabled={isCreating}
            className="px-3 py-1.5 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isCreating ? (
              <span className="flex items-center gap-1">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                创建中...
              </span>
            ) : (
              "写复盘"
            )}
          </button>
          <button
            onClick={onDismiss}
            disabled={isCreating}
            className="px-3 py-1.5 text-sm font-medium rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            跳过
          </button>
        </div>
      </div>
    </div>
  );
}
