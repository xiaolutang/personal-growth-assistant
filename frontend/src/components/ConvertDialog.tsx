import { useState, useEffect } from "react";
import { CheckCircle, Scale, FileText } from "lucide-react";
import { convertEntry, type ConvertRequest } from "@/services/api";
import { toast } from "sonner";
import { BaseDialog } from "@/components/BaseDialog";
import { TaskFields } from "@/components/TaskFields";
import type { Task } from "@/types/task";

type TargetCategory = ConvertRequest["target_category"];

interface ConvertDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  entry: Task;
  /** 预选的目标类型 */
  defaultTarget?: TargetCategory;
}

const TARGET_OPTIONS: { value: TargetCategory; label: string; icon: typeof CheckCircle; color: string }[] = [
  { value: "task", label: "任务", icon: CheckCircle, color: "text-green-500 dark:text-green-400" },
  { value: "decision", label: "决策", icon: Scale, color: "text-amber-600 dark:text-amber-400" },
  { value: "note", label: "笔记", icon: FileText, color: "text-blue-500 dark:text-blue-400" },
];

export function ConvertDialog({ open, onClose, onSuccess, entry, defaultTarget = "task" }: ConvertDialogProps) {
  const [targetCategory, setTargetCategory] = useState<TargetCategory>(defaultTarget);
  const [priority, setPriority] = useState("");
  const [plannedDate, setPlannedDate] = useState("");
  const [converting, setConverting] = useState(false);

  // 重置表单
  useEffect(() => {
    if (open) {
      setTargetCategory(defaultTarget);
      setPriority("");
      setPlannedDate("");
      setConverting(false);
    }
  }, [open, defaultTarget]);

  const handleConvert = async () => {
    setConverting(true);
    try {
      await convertEntry(entry.id, {
        target_category: targetCategory,
        priority: priority || null,
        planned_date: plannedDate || null,
        parent_id: entry.parent_id ?? null,
      });
      const label = targetCategory === "task" ? "任务" : "决策";
      toast.success(`已转为${label}：${entry.title}`);
      onSuccess();
      onClose();
    } catch {
      toast.error("转化失败，请重试");
    } finally {
      setConverting(false);
    }
  };

  return (
    <BaseDialog
      open={open}
      onOpenChange={(isOpen) => { if (!isOpen) onClose(); }}
      title="转化条目"
      confirmLabel="确认转化"
      loadingLabel="转化中..."
      onConfirm={handleConvert}
      loading={converting}
    >
      {/* 目标类型选择 */}
      <div className="mb-4">
        <label className="text-sm font-medium mb-2 block">目标类型</label>
        <div className="flex gap-2">
          {TARGET_OPTIONS.map((opt) => {
            const Icon = opt.icon;
            const isSelected = targetCategory === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => setTargetCategory(opt.value)}
                disabled={converting}
                className={`flex-1 flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
                  isSelected
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-card border-border hover:bg-accent"
                }`}
              >
                <Icon className={`h-4 w-4 ${isSelected ? "" : opt.color}`} />
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* 标题（预填，只读） */}
      <div className="mb-4">
        <label className="text-sm font-medium mb-2 block">标题</label>
        <input
          type="text"
          value={entry.title}
          readOnly
          className="w-full px-3 py-2 rounded-lg border border-border bg-muted text-sm text-muted-foreground"
        />
      </div>

      {/* 优先级 + 计划日期 */}
      <TaskFields
        priority={priority}
        onPriorityChange={setPriority}
        plannedDate={plannedDate}
        onPlannedDateChange={setPlannedDate}
        disabled={converting}
        idPrefix="convert"
      />
    </BaseDialog>
  );
}
