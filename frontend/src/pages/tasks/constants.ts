import type { TaskStatus } from "@/types/task";

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
