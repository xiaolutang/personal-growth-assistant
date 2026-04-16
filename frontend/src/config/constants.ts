import type { TaskStatus, Category, Priority } from "@/types/task";
import { CheckCircle, FileText, Lightbulb, Folder, Scale, RotateCcw, HelpCircle } from "lucide-react";

// 状态配置
export const statusConfig: Record<TaskStatus, { label: string; color: string; variant: "secondary" | "warning" | "success" | "destructive" | "outline" }> = {
  waitStart: { label: "待开始", color: "bg-gray-500 dark:bg-gray-600", variant: "secondary" },
  doing: { label: "进行中", color: "bg-blue-500 dark:bg-blue-600", variant: "warning" },
  complete: { label: "已完成", color: "bg-green-500 dark:bg-green-600", variant: "success" },
  paused: { label: "已挂起", color: "bg-orange-500 dark:bg-orange-600", variant: "outline" },
  cancelled: { label: "已取消", color: "bg-red-500 dark:bg-red-600", variant: "destructive" },
};

// 状态图标颜色
export const statusIconColor: Record<TaskStatus, string> = {
  waitStart: "",
  doing: "text-yellow-500 dark:text-yellow-400",
  complete: "text-green-500 dark:text-green-400",
  paused: "text-orange-500 dark:text-orange-400",
  cancelled: "text-red-500 dark:text-red-400",
};

// 状态转换映射
export const nextStatusMap: Record<TaskStatus, TaskStatus> = {
  waitStart: "doing",
  doing: "complete",
  complete: "waitStart",
  paused: "doing",
  cancelled: "waitStart",
};

// 优先级配置
export const priorityConfig: Record<Priority, { label: string; color: string; variant: "destructive" | "warning" | "secondary" }> = {
  high: { label: "高", color: "bg-red-500 dark:bg-red-600", variant: "destructive" },
  medium: { label: "中", color: "bg-yellow-500 dark:bg-yellow-600", variant: "warning" },
  low: { label: "低", color: "bg-gray-500 dark:bg-gray-600", variant: "secondary" },
};

// 分类配置
export const categoryConfig: Record<Category, { label: string; icon: typeof FileText; color: string }> = {
  task: { label: "任务", icon: CheckCircle, color: "text-green-500 dark:text-green-400" },
  inbox: { label: "灵感", icon: Lightbulb, color: "text-yellow-500 dark:text-yellow-400" },
  note: { label: "笔记", icon: FileText, color: "text-blue-500 dark:text-blue-400" },
  project: { label: "项目", icon: Folder, color: "text-purple-500 dark:text-purple-400" },
  decision: { label: "决策", icon: Scale, color: "text-amber-600 dark:text-amber-400" },
  reflection: { label: "复盘", icon: RotateCcw, color: "text-teal-500 dark:text-teal-400" },
  question: { label: "疑问", icon: HelpCircle, color: "text-rose-500 dark:text-rose-400" },
};

// 分类目录映射（与后端 MarkdownStorage.CATEGORY_DIRS 一致）
export const categoryDirs: Record<Category, string> = {
  project: "projects",
  task: "tasks",
  note: "notes",
  inbox: "",
  decision: "decisions",
  reflection: "reflections",
  question: "questions",
};

// 分类背景颜色（用于 Badge 样式）
export const categoryBgColors: Record<Category, string> = {
  task: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
  project: "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300",
  note: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
  inbox: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300",
  decision: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300",
  reflection: "bg-teal-100 text-teal-700 dark:bg-teal-900 dark:text-teal-300",
  question: "bg-rose-100 text-rose-700 dark:bg-rose-900 dark:text-rose-300",
};
