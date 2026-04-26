import type { TaskStatus, Priority } from "@/types/task";

// 所有可选状态
export const STATUS_OPTIONS: TaskStatus[] = ["waitStart", "doing", "complete", "paused", "cancelled"];

// 默认查询参数
export const TASK_QUERY_PARAMS = { type: "task" as const, limit: 100 };

// 快捷时间选项
export const QUICK_DATE_OPTIONS = [
  { label: "今天", value: "today" },
  { label: "本周", value: "week" },
  { label: "本月", value: "month" },
  { label: "全部", value: "all" },
];

// 优先级筛选选项
export const PRIORITY_OPTIONS: { label: string; value: Priority }[] = [
  { label: "高", value: "high" },
  { label: "中", value: "medium" },
  { label: "低", value: "low" },
];

// 排序选项
export const SORT_OPTIONS = [
  { label: "默认", value: "" },
  { label: "按优先级", value: "priority" },
  { label: "按创建时间", value: "created_at" },
] as const;

export type SortOption = (typeof SORT_OPTIONS)[number]["value"];
