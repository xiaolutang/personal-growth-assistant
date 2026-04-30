import { PRIORITY_OPTIONS } from "@/config/constants";

interface TaskFieldsProps {
  priority: string;
  onPriorityChange: (value: string) => void;
  plannedDate: string;
  onPlannedDateChange: (value: string) => void;
  dateHint?: string | null;
  disabled?: boolean;
  /** 优先级字段的 id 前缀，用于生成唯一 id */
  idPrefix?: string;
  /** 紧凑模式：水平并排布局，更小的标签（适用于 QuickCaptureBar 等场景） */
  compact?: boolean;
}

export function TaskFields({
  priority,
  onPriorityChange,
  plannedDate,
  onPlannedDateChange,
  dateHint,
  disabled = false,
  idPrefix = "task-fields",
  compact = false,
}: TaskFieldsProps) {
  const labelClass = compact
    ? "text-xs text-muted-foreground mb-1 block"
    : "text-sm font-medium mb-2 block";
  const inputClass = compact
    ? "w-full px-2 py-1.5 rounded-lg border border-border bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary"
    : "w-full px-3 py-2 rounded-lg border border-border bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary";

  const priorityField = (
    <div className={compact ? "flex-1" : "mb-4"}>
      <label htmlFor={`${idPrefix}-priority`} className={labelClass}>
        优先级
      </label>
      <select
        id={`${idPrefix}-priority`}
        aria-label="优先级"
        value={priority}
        onChange={(e) => onPriorityChange(e.target.value)}
        disabled={disabled}
        className={inputClass}
      >
        {PRIORITY_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );

  const dateField = (
    <div className={compact ? "flex-1" : "mb-4"}>
      <label htmlFor={`${idPrefix}-planned-date`} className={labelClass}>
        计划日期
      </label>
      <input
        id={`${idPrefix}-planned-date`}
        aria-label="计划日期"
        type="date"
        value={plannedDate}
        onChange={(e) => onPlannedDateChange(e.target.value)}
        disabled={disabled}
        className={inputClass}
      />
      {dateHint && plannedDate && (
        <p className="text-xs text-primary/80 mt-1">{dateHint}</p>
      )}
    </div>
  );

  if (compact) {
    return (
      <div className="flex gap-3">
        {priorityField}
        {dateField}
      </div>
    );
  }

  return (
    <>
      {priorityField}
      {dateField}
    </>
  );
}
