import { Wrench, Sparkles, Loader2, CheckCircle } from "lucide-react";
import type { Intent } from "@/lib/intentDetection";
import { intentConfig, intentIcons } from "@/lib/intentDetection";

export type ActionType = "intent" | "tool" | "skill";

/**
 * 获取操作标签
 */
export function getActionLabel(type: ActionType, name: string): string {
  if (type === "intent" && intentConfig[name as Intent]) {
    return intentConfig[name as Intent].label;
  }
  switch (type) {
    case "tool":
      return `使用工具-${name}`;
    case "skill":
      return `使用 skill-${name}`;
    default:
      return name || "操作";
  }
}

/**
 * 获取操作图标组件
 */
export function getActionIcon(type: ActionType, name: string): typeof Loader2 {
  if (type === "intent") {
    return intentIcons[name as Intent] || CheckCircle;
  }
  switch (type) {
    case "tool":
      return Wrench;
    case "skill":
      return Sparkles;
    default:
      return CheckCircle;
  }
}

/**
 * 获取操作颜色
 */
export function getActionColor(type: ActionType, name: string): string {
  if (type === "intent" && intentConfig[name as Intent]) {
    return intentConfig[name as Intent].color;
  }
  switch (type) {
    case "tool":
      return "text-blue-500 dark:text-blue-400";
    case "skill":
      return "text-purple-500 dark:text-purple-400";
    default:
      return "text-muted-foreground";
  }
}
