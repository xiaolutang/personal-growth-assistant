import type { TaskStatus, Priority, Category } from "@/types/task";

// 所有可选状态
export const STATUS_OPTIONS: TaskStatus[] = ["waitStart", "doing", "complete", "paused", "cancelled"];

// 默认查询参数 — F03: 使用 category_group=actionable 获取 task+decision+project
export const TASK_QUERY_PARAMS = { category_group: "actionable" as const, limit: 100 };

// 类型子 Tab 定义 — F03
export const TASK_SUB_TABS = [
  { key: "all" as const, label: "全部" },
  { key: "task" as const, label: "任务", category: "task" as Category },
  { key: "decision" as const, label: "决策", category: "decision" as Category },
  { key: "project" as const, label: "项目", category: "project" as Category },
];

export type SubTabKey = (typeof TASK_SUB_TABS)[number]["key"];

// 可执行的 category 集合 — F03: 用于本地过滤非 actionable 条目
export const ACTIONABLE_CATEGORIES: Category[] = ["task", "decision", "project"];

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
