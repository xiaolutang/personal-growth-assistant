/**
 * 回顾报告格式化工具
 * 用于格式化日报、周报、月报数据
 */

import type { SearchResult } from "@/types/task";

// 回顾报告接口
export interface ReviewReport {
  type: "daily" | "weekly" | "monthly";
  dateRange: {
    start: string;
    end: string;
  };
  taskStats: {
    total: number;
    completed: number;
    inProgress: number;
    pending: number;
    completionRate: number;
  };
  categoryStats: Record<string, number>;
  tagStats: Record<string, number>;
  recentEntries: SearchResult[];
  highlights: string[];
}

/**
 * 格式化回顾报告为 Markdown
 */
export function formatReviewReport(report: ReviewReport): string {
  const typeLabel = {
    daily: "今日",
    weekly: "本周",
    monthly: "本月",
  }[report.type];

  const lines: string[] = [
    `## ${typeLabel}回顾`,
    "",
    `**时间范围**: ${report.dateRange.start} ~ ${report.dateRange.end}`,
    "",
    "### 任务完成情况",
    "",
    `| 指标 | 数值 |`,
    `|------|------|`,
    `| 总任务 | ${report.taskStats.total} |`,
    `| 已完成 | ${report.taskStats.completed} |`,
    `| 进行中 | ${report.taskStats.inProgress} |`,
    `| 待开始 | ${report.taskStats.pending} |`,
    `| 完成率 | ${report.taskStats.completionRate}% |`,
    "",
    "### 分类统计",
    "",
  ];

  // 添加分类统计
  Object.entries(report.categoryStats)
    .sort((a, b) => b[1] - a[1])
    .forEach(([category, count]) => {
      lines.push(`- ${getCategoryLabel(category)}: ${count}`);
    });

  // 添加标签统计（如果有）
  if (Object.keys(report.tagStats).length > 0) {
    lines.push("", "### 标签云", "");
    const topTags = Object.entries(report.tagStats)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10);
    lines.push(topTags.map(([tag, count]) => `\`${tag}\`(${count})`).join(" "));
  }

  // 添加亮点
  if (report.highlights.length > 0) {
    lines.push("", "### 今日亮点", "");
    report.highlights.forEach((h) => lines.push(`- ${h}`));
  }

  // 添加最近条目
  if (report.recentEntries.length > 0) {
    lines.push("", "### 最近记录", "");
    report.recentEntries.slice(0, 5).forEach((entry) => {
      const statusIcon = entry.status === "complete" ? "✅" : entry.status === "doing" ? "🔄" : "⏳";
      lines.push(`- ${statusIcon} ${entry.title}`);
    });
  }

  return lines.join("\n");
}

/**
 * 格式化简短回顾报告
 */
export function formatShortReview(report: ReviewReport): string {
  const typeLabel = {
    daily: "今日",
    weekly: "本周",
    monthly: "本月",
  }[report.type];

  return `## ${typeLabel}回顾

**任务完成情况**
- 总任务: ${report.taskStats.total}
- 已完成: ${report.taskStats.completed}
- 完成率: ${report.taskStats.completionRate}%

**分类统计**
${Object.entries(report.categoryStats)
  .map(([cat, count]) => `- ${getCategoryLabel(cat)}: ${count}`)
  .join("\n")}`;
}

/**
 * 从条目列表生成回顾报告
 */
export function generateReviewReport(
  entries: SearchResult[],
  type: "daily" | "weekly" | "monthly"
): ReviewReport {
  const now = new Date();
  const today = now.toISOString().split("T")[0];

  // 计算日期范围
  let startDate = today;
  if (type === "weekly") {
    const weekStart = new Date(now);
    weekStart.setDate(weekStart.getDate() - 7);
    startDate = weekStart.toISOString().split("T")[0];
  } else if (type === "monthly") {
    startDate = today.substring(0, 8) + "01";
  }

  // 过滤日期范围内的条目
  const filteredEntries = entries.filter((e) => {
    const entryDate = e.created_at?.split("T")[0] || "";
    return entryDate >= startDate && entryDate <= today;
  });

  // 统计任务状态
  const taskStats = {
    total: filteredEntries.length,
    completed: filteredEntries.filter((e) => e.status === "complete").length,
    inProgress: filteredEntries.filter((e) => e.status === "doing").length,
    pending: filteredEntries.filter((e) => e.status === "waitStart").length,
    completionRate: 0,
  };
  taskStats.completionRate =
    taskStats.total > 0 ? Math.round((taskStats.completed / taskStats.total) * 100) : 0;

  // 统计分类
  const categoryStats: Record<string, number> = {};
  filteredEntries.forEach((e) => {
    const cat = e.category || "other";
    categoryStats[cat] = (categoryStats[cat] || 0) + 1;
  });

  // 统计标签
  const tagStats: Record<string, number> = {};
  filteredEntries.forEach((e) => {
    (e.tags || []).forEach((tag) => {
      tagStats[tag] = (tagStats[tag] || 0) + 1;
    });
  });

  // 生成亮点（已完成的高优先级任务）
  const highlights = filteredEntries
    .filter((e) => e.status === "complete" && e.priority === "high")
    .slice(0, 3)
    .map((e) => e.title);

  return {
    type,
    dateRange: { start: startDate, end: today },
    taskStats,
    categoryStats,
    tagStats,
    recentEntries: filteredEntries.slice(0, 10),
    highlights,
  };
}

/**
 * 获取分类标签
 */
function getCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    task: "任务",
    note: "笔记",
    project: "项目",
    inbox: "灵感",
    other: "其他",
  };
  return labels[category] || category;
}

export default {
  formatReviewReport,
  formatShortReview,
  generateReviewReport,
};
