import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** 获取本地日期字符串 YYYY-MM-DD */
export function toLocalDateString(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/** 进度条颜色：>80% 绿色，30-80% 蓝色，<30% 灰色 */
export function getProgressColor(percentage: number): string {
  if (percentage > 80) return "bg-green-500";
  if (percentage >= 30) return "bg-blue-500";
  return "bg-gray-400";
}
