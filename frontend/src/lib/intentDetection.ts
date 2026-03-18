/**
 * 意图检测工具
 * 用于分析用户输入并确定操作类型
 */

import { Plus, Search, GitBranch } from "lucide-react";

// 意图类型
export type Intent = "create" | "search" | "knowledge";

// 意图配置
export const intentConfig: Record<Intent, { label: string; color: string }> = {
  create: { label: "创建任务", color: "text-primary" },
  search: { label: "语义搜索", color: "text-blue-500" },
  knowledge: { label: "知识图谱", color: "text-purple-500" },
};

// 意图图标映射
export const intentIcons: Record<Intent, typeof Plus> = {
  create: Plus,
  search: Search,
  knowledge: GitBranch,
};

// 搜索关键词
const SEARCH_KEYWORDS = ["帮我找", "搜索", "有没有", "查找", "寻找", "找一下", "找找"];

// 知识图谱关键词
const KNOWLEDGE_KEYWORDS = ["知识图谱", "相关概念", "什么关系", "查看图谱", "展示图谱", "概念图"];

/**
 * 检测用户输入的意图
 */
export function detectIntent(text: string): Intent {
  if (SEARCH_KEYWORDS.some((k) => text.includes(k))) return "search";
  if (KNOWLEDGE_KEYWORDS.some((k) => text.includes(k))) return "knowledge";
  return "create";
}

/**
 * 从搜索文本中提取查询词
 */
export function extractSearchQuery(text: string): string {
  const patterns = [
    /帮我找[一下]?\s*(.+)/,
    /搜索\s*(.+)/,
    /有没有\s*(.+)/,
    /查找\s*(.+)/,
    /寻找\s*(.+)/,
    /找[一下]?\s*(.+)/,
    /找找\s*(.+)/,
  ];

  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) return match[1].trim();
  }
  return text;
}

/**
 * 从知识图谱文本中提取概念
 */
export function extractConcept(text: string): string {
  const patterns = [
    /(.+?)的?知识图谱/,
    /(.+?)的?相关概念/,
    /(.+?)的?概念图/,
    /查看\s*(.+?)\s*的?图谱/,
    /展示\s*(.+?)\s*的?图谱/,
  ];

  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) return match[1].trim();
  }
  return text;
}
