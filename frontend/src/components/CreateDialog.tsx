import { useState, useRef, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { categoryConfig } from "@/config/constants";
import { useTaskStore } from "@/stores/taskStore";
import { useSmartSuggestions, createDateChangeHandler } from "@/lib/useSmartSuggestions";
import { BaseDialog } from "@/components/BaseDialog";
import { TaskFields } from "@/components/TaskFields";
import type { Task, Category, Priority, EntryCreate } from "@/types/task";

// 从 categoryConfig 派生全部分类，保持单一权威来源
const ALL_CATEGORIES: Category[] = Object.keys(categoryConfig) as Category[];

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

  // 智能提示 hook（日期解析 + 类型建议）
  const {
    suggestedDate,
    dateHint,
    typeSuggestion,
    autoFillEvent,
    onTitleChange: onSmartTitleChange,
    onDateCleared,
    onDateManuallyChanged,
    clearTypeSuggestion,
    reset: resetSmartSuggestions,
  } = useSmartSuggestions({ enableTypeSuggestion: true });

  // 响应日期自动填充/清除事件（仅在 task 类型下生效）
  useEffect(() => {
    if (!autoFillEvent) return;
    if (selectedType !== "task") return;
    if (autoFillEvent.date) {
      setPlannedDate(autoFillEvent.date);
    } else if (autoFillEvent.date === null) {
      setPlannedDate("");
    }
  }, [autoFillEvent, selectedType]);

  // 当 selectedType 变为 task 且已有建议日期时，应用建议日期
  // 处理"先输入标题后选类型"的场景
  useEffect(() => {
    if (selectedType === "task" && suggestedDate) {
      setPlannedDate(suggestedDate);
    }
  }, [selectedType, suggestedDate]);

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
      // 重置智能提示状态（包括 suppress）
      resetSmartSuggestions();
      // 延迟聚焦让 DOM 先渲染
      requestAnimationFrame(() => {
        titleRef.current?.focus();
      });
    }
  }, [open, resolvedDefaultType, resetSmartSuggestions]);

  // 当 allowedTypes 动态变化时，若 selectedType 不再有效则重置
  useEffect(() => {
    if (selectedType && !availableTypes.includes(selectedType)) {
      setSelectedType(null);
      setContent("");
      setPriority("");
      setPlannedDate("");
    }
  }, [availableTypes, selectedType]);

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
      try { onOpenChange(false); } catch { /* close error 不影响 UI */ }
      return;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "创建失败";
      setError(`创建失败：${msg}`);
    } finally {
      setSubmitting(false);
    }
  }, [title, content, selectedType, priority, plannedDate, createEntry, onSuccess, onOpenChange]);

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
    // 清除类型建议（避免与新选中类型冲突）
    clearTypeSuggestion();
  }, []);

  /** 标题变更处理 */
  const handleTitleChange = useCallback(
    (value: string) => {
      setTitle(value);
      if (validationError) setValidationError(null);
      onSmartTitleChange(value);
    },
    [validationError, onSmartTitleChange],
  );

  /** 计划日期变更处理 */
  const handlePlannedDateChange = useCallback(
    createDateChangeHandler(
      plannedDate,
      () => { setPlannedDate(""); onDateCleared(); },
      (v) => { setPlannedDate(v); onDateManuallyChanged(v); },
    ),
    [plannedDate, onDateCleared, onDateManuallyChanged],
  );

  /** 类型建议点击处理 */
  const handleTypeSuggestionClick = useCallback(
    (suggestedType: string) => {
      // 仅在建议类型与当前选中不同时才执行切换（避免清空已填写内容）
      if (
        availableTypes.includes(suggestedType as Category) &&
        suggestedType !== selectedType
      ) {
        // 复用 handleTypeChange 清理 content、priority、plannedDate、校验/错误状态
        handleTypeChange(suggestedType as Category);
      }
      clearTypeSuggestion();
    },
    [availableTypes, clearTypeSuggestion, handleTypeChange, selectedType],
  );

  // selectedType 为 null 时，动态字段和按钮不渲染

  const contentLabel = selectedType ? getContentLabel(selectedType) : null;
  const showTaskFields = selectedType === "task";

  return (
    <BaseDialog
      open={open}
      onOpenChange={onOpenChange}
      title="新建条目"
      confirmLabel="创建"
      loadingLabel="创建中..."
      onConfirm={handleSubmit}
      loading={submitting}
    >
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
          onChange={(e) => handleTitleChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入标题..."
          disabled={submitting}
          className="w-full px-3 py-2 rounded-lg border border-border bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
        {/* 类型建议（仅在建议类型可用时显示） */}
        {typeSuggestion && availableTypes.includes(typeSuggestion.type as Category) && (
          <p className="text-xs text-primary mt-1">
            <button
              type="button"
              onClick={() => handleTypeSuggestionClick(typeSuggestion.type)}
              className="hover:underline"
            >
              {typeSuggestion.label}
            </button>
          </p>
        )}
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

      {/* 优先级 + 计划日期（task 专属） */}
      {showTaskFields && (
        <TaskFields
          priority={priority}
          onPriorityChange={(v) => setPriority(v as Priority | "")}
          plannedDate={plannedDate}
          onPlannedDateChange={handlePlannedDateChange}
          dateHint={dateHint}
          disabled={submitting}
          idPrefix="create"
        />
      )}

      {/* 错误提示 */}
      {error && (
        <p className="text-sm text-red-500 dark:text-red-400 mb-3">{error}</p>
      )}
    </BaseDialog>
  );
}
