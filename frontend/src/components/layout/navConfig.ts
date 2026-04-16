import { Home, CheckCircle, BarChart3, Compass, Brain, Target } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface NavItem {
  to: string;
  icon: LucideIcon;
  label: string;
}

export const navItems: NavItem[] = [
  { to: "/", icon: Home, label: "今天" },
  { to: "/explore", icon: Compass, label: "探索" },
  { to: "/graph", icon: Brain, label: "图谱" },
  { to: "/goals", icon: Target, label: "目标" },
  { to: "/tasks", icon: CheckCircle, label: "任务" },
  { to: "/review", icon: BarChart3, label: "回顾" },
];
