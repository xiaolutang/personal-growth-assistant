import { useState } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";

export type DecisionChoice = "YES" | "NO";

interface DecisionResultDialogProps {
  open: boolean;
  choice: DecisionChoice;
  onConfirm: (data: {
    reason: string;
    createTask: boolean;
    taskTitle: string;
  }) => Promise<void>;
  onCancel: () => void;
}

export function DecisionResultDialog({ open, choice, onConfirm, onCancel }: DecisionResultDialogProps) {
  const [reason, setReason] = useState("");
  const [createTask, setCreateTask] = useState(false);
  const [taskTitle, setTaskTitle] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (!open) return null;

  const handleConfirm = async () => {
    setSubmitting(true);
    try {
      await onConfirm({
        reason,
        createTask,
        taskTitle: createTask ? taskTitle : "",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const choiceColor = choice === "YES" ? "text-green-600" : "text-red-600";
  const choiceLabel = choice === "YES" ? "YES" : "NO";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onCancel}>
      <div
        className="bg-background rounded-xl shadow-lg w-full max-w-md mx-4 p-5"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-semibold">
            决策结果：<span className={choiceColor}>{choiceLabel}</span>
          </h3>
          <button onClick={onCancel} className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Reason input */}
        <div className="mb-4">
          <label className="text-sm font-medium mb-1.5 block">决策理由</label>
          <Textarea
            placeholder="可选：输入决策理由"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            className="resize-none"
          />
        </div>

        {/* Create task toggle */}
        <div className="mb-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              role="checkbox"
              aria-label="同时创建任务"
              checked={createTask}
              onChange={(e) => setCreateTask(e.target.checked)}
              className="h-4 w-4 rounded border-input"
            />
            <span className="text-sm">同时创建任务</span>
          </label>

          {createTask && (
            <div className="mt-2">
              <Input
                placeholder="输入任务标题"
                value={taskTitle}
                onChange={(e) => setTaskTitle(e.target.value)}
              />
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={onCancel}>
            取消
          </Button>
          <Button size="sm" onClick={handleConfirm} disabled={submitting}>
            {submitting ? "提交中..." : "确认"}
          </Button>
        </div>
      </div>
    </div>
  );
}
