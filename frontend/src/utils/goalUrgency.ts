import { AlertTriangle, Clock } from "lucide-react";

export type UrgencyLevel = "overdue" | "urgent" | "soon" | "safe";

export interface UrgencyInfo {
  level: UrgencyLevel;
  label: string;
  icon: typeof AlertTriangle;
  color: string;
}

export function getUrgency(endDate: string | null): UrgencyInfo | null {
  if (!endDate) return null;
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const end = new Date(endDate + "T00:00:00");
  const diffMs = end.getTime() - now.getTime();
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return { level: "overdue", label: "已逾期", icon: AlertTriangle, color: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300" };
  if (diffDays < 3) return { level: "urgent", label: `${diffDays}天后截止`, icon: AlertTriangle, color: "bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300" };
  if (diffDays < 7) return { level: "soon", label: `${diffDays}天后截止`, icon: Clock, color: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300" };
  return null;
}
