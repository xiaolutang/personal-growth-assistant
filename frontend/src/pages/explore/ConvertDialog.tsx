import { useState, useRef, useEffect } from "react";
import { X, Loader2, CheckCircle, Scale } from "lucide-react";
import { convertEntry } from "@/services/api";
import { toast } from "sonner";
import type { Task } from "@/types/task";

type TargetCategory = "task" | "decision";

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
];

const PRIORITY_OPTIONS = [
  { value: "", label: "不设置" },
  { value: "high", label: "高" },
  { value: "medium", label: "中" },
  { value: "low", label: "低" },
];

export function ConvertDialog({ open, onClose, onSuccess, entry, defaultTarget = "task" }: ConvertDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [targetCategory, setTargetCategory] = useState<TargetCategory>(defaultTarget);
  const [priority, setPriority] = useState("");
  const [plannedDate, setPlannedDate] = useState("");
  const [converting, setConverting] = useState(false);

  // 同步对话框开关
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

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

  if (!open) return null;

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      className="rounded-xl p-0 bg-transparent backdrop:bg-black/40 max-w-md w-full"
    >
      <div className="bg-card rounded-xl p-6 shadow-lg">
        {/* 标题 */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">转化条目</h2>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground transition-colors"
            disabled={converting}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

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

        {/* 优先级 */}
        <div className="mb-4">
          <label htmlFor="convert-priority" className="text-sm font-medium mb-2 block">优先级</label>
          <select
            id="convert-priority"
            aria-label="优先级"
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            disabled={converting}
            className="w-full px-3 py-2 rounded-lg border border-border bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          >
            {PRIORITY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* 计划日期 */}
        <div className="mb-4">
          <label htmlFor="convert-planned-date" className="text-sm font-medium mb-2 block">计划日期</label>
          <input
            id="convert-planned-date"
            aria-label="计划日期"
            type="date"
            value={plannedDate}
            onChange={(e) => setPlannedDate(e.target.value)}
            disabled={converting}
            className="w-full px-3 py-2 rounded-lg border border-border bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        {/* 操作按钮 */}
        <div className="flex gap-3 mt-4">
          <button
            onClick={onClose}
            disabled={converting}
            className="flex-1 px-4 py-2 rounded-lg text-sm font-medium border border-border hover:bg-accent transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleConvert}
            disabled={converting}
            className="flex-1 px-4 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {converting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                转化中...
              </>
            ) : (
              "确认转化"
            )}
          </button>
        </div>
      </div>
    </dialog>
  );
}
