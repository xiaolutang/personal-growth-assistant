import { useState, useRef, useCallback, useEffect } from "react";
import { Send, ChevronDown, ChevronUp } from "lucide-react";
import { toast } from "sonner";
import { useTaskStore } from "@/stores/taskStore";
import { CreateDialog } from "@/components/CreateDialog";
import type { Priority, EntryCreate } from "@/types/task";

const PRIORITY_OPTIONS: { value: Priority | ""; label: string }[] = [
  { value: "", label: "不设置" },
  { value: "high", label: "高" },
  { value: "medium", label: "中" },
  { value: "low", label: "低" },
];

interface QuickCaptureBarProps {
  /** 外部聚焦触发，传入一个递增值即可触发聚焦 */
  focusTrigger?: number;
}

export function QuickCaptureBar({ focusTrigger }: QuickCaptureBarProps) {
  const [title, setTitle] = useState("");
  const [expanded, setExpanded] = useState(false);
  const [priority, setPriority] = useState<Priority | "">("");
  const [plannedDate, setPlannedDate] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);
  const createEntry = useTaskStore((s) => s.createEntry);

  const trimmed = title.trim();
  const canSubmit = trimmed.length > 0 && !submitting;

  // 外部聚焦
  useEffect(() => {
    if (focusTrigger !== undefined && focusTrigger > 0) {
      inputRef.current?.focus();
    }
  }, [focusTrigger]);

  const handleSubmit = useCallback(async () => {
    if (!trimmed || submitting) return;

    setSubmitting(true);
    try {
      let data: EntryCreate;
      if (expanded) {
        // 展开模式 -> task
        data = { type: "task", title: trimmed };
        if (priority) data.priority = priority;
        if (plannedDate) data.planned_date = plannedDate;
      } else {
        // 默认模式 -> inbox
        data = { type: "inbox", title: trimmed };
      }

      await createEntry(data);
      toast.success(expanded ? "已创建任务" : "已创建灵感");
      setTitle("");
      setPriority("");
      setPlannedDate("");
      // 展开模式提交后收起
      setExpanded(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "创建失败";
      toast.error(`创建失败：${msg}`);
    } finally {
      setSubmitting(false);
    }
  }, [trimmed, submitting, expanded, priority, plannedDate, createEntry]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
        e.preventDefault();
        if (canSubmit) {
          handleSubmit();
        }
      }
    },
    [canSubmit, handleSubmit],
  );

  const handleToggleExpand = useCallback(() => {
    setExpanded((prev) => !prev);
  }, []);

  const handleMoreTypes = useCallback(() => {
    setDialogOpen(true);
  }, []);

  return (
    <div className="space-y-2">
      {/* 输入栏主区域 */}
      <div className="flex items-center gap-2 rounded-xl border border-border bg-card p-2">
        <input
          ref={inputRef}
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="记录灵感或任务..."
          disabled={submitting}
          aria-label="输入内容"
          className="flex-1 px-2 py-1.5 text-sm bg-transparent focus:outline-none placeholder:text-muted-foreground disabled:opacity-50"
        />
        <button
          onClick={handleToggleExpand}
          disabled={submitting}
          aria-label={expanded ? "收起更多选项" : "展开更多选项"}
          className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors disabled:opacity-50"
        >
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          aria-label="发送"
          className="p-1.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting ? (
            <span className="block h-4 w-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* 展开区域 */}
      {expanded && (
        <div className="rounded-xl border border-border bg-card p-3 space-y-3">
          <div className="flex gap-3">
            <div className="flex-1">
              <label htmlFor="qcb-priority" className="text-xs text-muted-foreground mb-1 block">
                优先级
              </label>
              <select
                id="qcb-priority"
                aria-label="优先级"
                value={priority}
                onChange={(e) => setPriority(e.target.value as Priority | "")}
                disabled={submitting}
                className="w-full px-2 py-1.5 rounded-lg border border-border bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {PRIORITY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label htmlFor="qcb-planned-date" className="text-xs text-muted-foreground mb-1 block">
                计划日期
              </label>
              <input
                id="qcb-planned-date"
                type="date"
                aria-label="计划日期"
                value={plannedDate}
                onChange={(e) => setPlannedDate(e.target.value)}
                disabled={submitting}
                className="w-full px-2 py-1.5 rounded-lg border border-border bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              将创建为<b className="text-foreground">任务</b>
            </span>
            <button
              onClick={handleMoreTypes}
              className="text-xs text-primary hover:underline"
            >
              更多类型
            </button>
          </div>
        </div>
      )}

      {/* CreateDialog 用于更多类型 */}
      <CreateDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />
    </div>
  );
}
