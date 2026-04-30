import { useState, useRef, useEffect, useCallback } from "react";
import { X, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { categoryConfig } from "@/config/constants";
import { useTaskStore } from "@/stores/taskStore";
import type { Task, Category, Priority, EntryCreate } from "@/types/task";

// 从 categoryConfig 派生全部分类，保持单一权威来源
const ALL_CATEGORIES: Category[] = Object.keys(categoryConfig) as Category[];

const PRIORITY_OPTIONS: { value: Priority | ""; label: string }[] = [
  { value: "", label: "不设置" },
  { value: "high", label: "高" },
  { value: "medium", label: "中" },
  { value: "low", label: "低" },
];

/** 是否为快速创建类型（仅标题字段，支持回车提交） */
function isQuickCreateCategory(category: Category): boolean {
  return category === "inbox" || category === "task";
}

/** 获取二级文本字段的 label */
function getContentLabel(category: Category): string | null {
  switch (category) {
    case "project":
      return "描述";
    case "decision":
      return "选项描述";
    case "note":
    case "reflection":
      return "内容";
    case "question":
      return "描述";
    default:
      return null;
  }
}

interface CreateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultType?: Category;
  allowedTypes?: Category[];
  onSuccess?: (entry: Task) => void;
}

export function CreateDialog({
  open,
  onOpenChange,
  defaultType,
  allowedTypes,
  onSuccess,
}: CreateDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleRef = useRef<HTMLInputElement>(null);

  const availableTypes = allowedTypes ?? ALL_CATEGORIES;

  // 将 defaultType 约束到 allowedTypes 内，若未传或不在范围内则为 null（不预选）
  const resolvedDefaultType =
    defaultType && availableTypes.includes(defaultType) ? defaultType : null;

  const [selectedType, setSelectedType] = useState<Category | null>(resolvedDefaultType);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [priority, setPriority] = useState<Priority | "">("");
  const [plannedDate, setPlannedDate] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const createEntry = useTaskStore((s) => s.createEntry);

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

  // 打开时重置表单
  useEffect(() => {
    if (open) {
      setSelectedType(resolvedDefaultType);
      setTitle("");
      setContent("");
      setPriority("");
      setPlannedDate("");
      setSubmitting(false);
      setError(null);
      setValidationError(null);
      // 延迟聚焦让 DOM 先渲染
      requestAnimationFrame(() => {
        titleRef.current?.focus();
      });
    }
  }, [open, resolvedDefaultType]);

  // 当 allowedTypes 动态变化时，若 selectedType 不再有效则重置
  useEffect(() => {
    if (selectedType && !availableTypes.includes(selectedType)) {
      setSelectedType(null);
      setContent("");
      setPriority("");
      setPlannedDate("");
    }
  }, [availableTypes, selectedType]);

  const handleClose = useCallback(() => {
    onOpenChange(false);
  }, [onOpenChange]);

  const handleSubmit = useCallback(async () => {
    // 校验
    if (!selectedType) {
      setValidationError("请选择类型");
      return;
    }
    if (!title.trim()) {
      setValidationError("请输入标题");
      return;
    }
    setValidationError(null);
    setError(null);
    setSubmitting(true);

    try {
      const data: EntryCreate = {
        type: selectedType,
        title: title.trim(),
      };

      // 二级文本字段统一映射到 content
      if (content.trim()) {
        data.content = content.trim();
      }

      // task 特有字段
      if (selectedType === "task") {
        if (priority) {
          data.priority = priority;
        }
        if (plannedDate) {
          data.planned_date = plannedDate;
        }
      }

      const entry = await createEntry(data);
      // 创建成功 — 后续回调异常不应影响成功状态
      setSubmitting(false);
      toast.success("创建成功");
      // onSuccess 和关闭分别处理，互不影响
      try { onSuccess?.(entry); } catch { /* callback error 不影响 UI */ }
      try { handleClose(); } catch { /* close error 不影响 UI */ }
      return;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "创建失败";
      setError(`创建失败：${msg}`);
    } finally {
      setSubmitting(false);
    }
  }, [title, content, selectedType, priority, plannedDate, createEntry, onSuccess, handleClose]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        // 仅在快速创建类型（inbox/task 单字段场景）的标题输入框中回车提交
        const target = e.target as HTMLElement;
        const isTitleInput = target.tagName === "INPUT" && target === titleRef.current;
        if (isTitleInput && selectedType && isQuickCreateCategory(selectedType)) {
          e.preventDefault();
          handleSubmit();
        }
      }
    },
    [handleSubmit, selectedType],
  );

  const handleTypeChange = useCallback((cat: Category) => {
    setSelectedType(cat);
    // 切换类型时清空类型特有字段
    setContent("");
    setPriority("");
    setPlannedDate("");
    setValidationError(null);
    setError(null);
  }, []);

  // selectedType 为 null 时，动态字段和按钮不渲染

  if (!open) return null;

  const contentLabel = selectedType ? getContentLabel(selectedType) : null;
  const showPriority = selectedType === "task";
  const showPlannedDate = selectedType === "task";

  return (
    <dialog
      ref={dialogRef}
      onClose={handleClose}
      className="rounded-xl p-0 bg-transparent backdrop:bg-black/40 max-w-md w-full max-sm:max-w-full max-sm:m-0 max-sm:mt-auto max-sm:rounded-b-none max-sm:h-[90vh] max-sm:rounded-t-xl"
    >
      <div className="bg-card rounded-xl p-6 shadow-lg flex flex-col max-sm:h-full max-sm:rounded-b-none">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">新建条目</h2>
          <button
            onClick={handleClose}
            className="text-muted-foreground hover:text-foreground transition-colors"
            disabled={submitting}
            aria-label="关闭"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* 类型选择器 */}
        <div className="mb-4">
          <label className="text-sm font-medium mb-2 block">类型</label>
          <div className="flex flex-wrap gap-2">
            {availableTypes.map((cat) => {
              const config = categoryConfig[cat];
              const Icon = config.icon;
              const isSelected = selectedType === cat;
              return (
                <button
                  key={cat}
                  type="button"
                  onClick={() => handleTypeChange(cat)}
                  disabled={submitting}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                    isSelected
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-card border-border hover:bg-accent"
                  }`}
                >
                  <Icon className={`h-4 w-4 ${isSelected ? "" : config.color}`} />
                  {config.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* 标题 */}
        <div className="mb-4">
          <label htmlFor="create-title" className="text-sm font-medium mb-2 block">
            标题
          </label>
          <input
            ref={titleRef}
            id="create-title"
            aria-label="标题"
            type="text"
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              if (validationError) setValidationError(null);
            }}
            onKeyDown={handleKeyDown}
            placeholder="输入标题..."
            disabled={submitting}
            className="w-full px-3 py-2 rounded-lg border border-border bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
          {validationError && (
            <p className="text-sm text-red-500 dark:text-red-400 mt-1">{validationError}</p>
          )}
        </div>

        {/* 二级文本字段（content） */}
        {contentLabel && (
          <div className="mb-4">
            <label htmlFor="create-content" className="text-sm font-medium mb-2 block">
              {contentLabel}
            </label>
            <textarea
              id="create-content"
              aria-label={contentLabel}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder={`输入${contentLabel}...`}
              disabled={submitting}
              rows={3}
              className="w-full px-3 py-2 rounded-lg border border-border bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-none"
            />
          </div>
        )}

        {/* 优先级（task 专属） */}
        {showPriority && (
          <div className="mb-4">
            <label htmlFor="create-priority" className="text-sm font-medium mb-2 block">
              优先级
            </label>
            <select
              id="create-priority"
              aria-label="优先级"
              value={priority}
              onChange={(e) => setPriority(e.target.value as Priority | "")}
              disabled={submitting}
              className="w-full px-3 py-2 rounded-lg border border-border bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            >
              {PRIORITY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* 计划日期（task 专属） */}
        {showPlannedDate && (
          <div className="mb-4">
            <label htmlFor="create-planned-date" className="text-sm font-medium mb-2 block">
              计划日期
            </label>
            <input
              id="create-planned-date"
              aria-label="计划日期"
              type="date"
              value={plannedDate}
              onChange={(e) => setPlannedDate(e.target.value)}
              disabled={submitting}
              className="w-full px-3 py-2 rounded-lg border border-border bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        )}

        {/* 错误提示 */}
        {error && (
          <p className="text-sm text-red-500 dark:text-red-400 mb-3">{error}</p>
        )}

        {/* 操作按钮 */}
        <div className="flex gap-3 mt-4 max-sm:mt-auto max-sm:pt-4">
          <button
            onClick={handleClose}
            disabled={submitting}
            className="flex-1 px-4 py-2 rounded-lg text-sm font-medium border border-border hover:bg-accent transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="flex-1 px-4 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                创建中...
              </>
            ) : (
              "创建"
            )}
          </button>
        </div>
      </div>
    </dialog>
  );
}
