/**
 * 意图检测工具
 * 用于分析用户输入并确定操作类型
 * 支持完整 CRUD（增删改查）+ 功能入口（知识图谱、回顾、帮助）
 */

import { Plus, Search, GitBranch, Edit, Trash2, BarChart3, HelpCircle } from "lucide-react";

// 意图类型（CRUD + 功能入口）
export type Intent =
  // CRUD 基础操作
  | "create"      // 创建：新增任务/笔记/灵感/项目
  | "read"        // 查询：搜索、查看详情
  | "update"      // 更新：修改状态、内容、标签等
  | "delete"      // 删除：移除条目
  // 功能入口
  | "knowledge"   // 知识图谱
  | "review"      // 回顾总结
  | "help";       // 帮助说明

// 意图配置
export const intentConfig: Record<Intent, { label: string; color: string; description: string }> = {
  create: { label: "创建", color: "text-primary", description: "创建任务、笔记或灵感" },
  read: { label: "查询", color: "text-blue-500 dark:text-blue-400", description: "搜索和查看内容" },
  update: { label: "更新", color: "text-orange-500 dark:text-orange-400", description: "修改已有内容" },
  delete: { label: "删除", color: "text-red-500 dark:text-red-400", description: "删除不需要的内容" },
  knowledge: { label: "知识图谱", color: "text-purple-500 dark:text-purple-400", description: "查看知识关联" },
  review: { label: "回顾", color: "text-green-500 dark:text-green-400", description: "查看成长报告" },
  help: { label: "帮助", color: "text-gray-500 dark:text-gray-400", description: "查看使用说明" },
};

// 意图图标映射
export const intentIcons: Record<Intent, typeof Plus> = {
  create: Plus,
  read: Search,
  update: Edit,
  delete: Trash2,
  knowledge: GitBranch,
  review: BarChart3,
  help: HelpCircle,
};

// 意图关键词映射
const INTENT_KEYWORDS: Record<Intent, string[]> = {
  // 创建
  create: ["新建", "创建", "添加", "记录", "记一下", "添加一个", "新增"],

  // 查询（合并原 search）
  read: ["帮我找", "搜索", "有没有", "查找", "寻找", "找一下", "查看", "显示", "列出", "找找"],

  // 更新
  update: ["修改", "更新", "改一下", "把", "改为", "改成", "标记", "完成", "设为", "设置"],

  // 删除
  delete: ["删除", "移除", "去掉", "删掉", "不要了"],

  // 功能入口
  knowledge: ["知识图谱", "相关概念", "什么关系", "查看图谱", "展示图谱", "概念图", "学习路径"],
  review: ["今天做了什么", "本周进度", "月报", "回顾", "统计", "做了啥", "干了什么", "进度"],
  help: ["帮助", "能做什么", "怎么用", "使用说明", "功能介绍"],
};

// 状态关键词（提取为常量避免每次调用重新创建）
const STATUS_KEYWORDS = ["完成", "进行中", "暂停", "取消", "等待", "complete", "doing", "paused", "cancelled", "waitStart"];

// 状态映射（中文 -> 英文）
const STATUS_MAP: Record<string, string> = {
  "完成": "complete", "已完成": "complete",
  "进行中": "doing", "做": "doing",
  "暂停": "paused",
  "取消": "cancelled",
  "等待": "waitStart",
};

/**
 * 检测用户输入的意图
 */
export function detectIntent(text: string): Intent {
  // 按优先级检测（功能入口 > CRUD）
  // 先检测 help
  if (INTENT_KEYWORDS.help.some((k) => text.includes(k))) return "help";
  // 再检测 review
  if (INTENT_KEYWORDS.review.some((k) => text.includes(k))) return "review";
  // 再检测 knowledge
  if (INTENT_KEYWORDS.knowledge.some((k) => text.includes(k))) return "knowledge";
  // 检测 delete
  if (INTENT_KEYWORDS.delete.some((k) => text.includes(k))) return "delete";
  // 检测 update（需要"把"等关键词配合，或"添加标签"模式）
  if ((
    INTENT_KEYWORDS.update.some((k) => text.includes(k)) && (
      text.includes("改为") || text.includes("改成") || text.includes("标记") ||
      text.includes("完成") || text.includes("设为") || text.includes("设置") ||
      text.includes("修改") || text.includes("更新")
    )
  ) || /给\s*.+\s*添加?标签/.test(text) || /为\s*.+\s*添加?标签/.test(text)) {
    return "update";
  }
  // 检测 read
  if (INTENT_KEYWORDS.read.some((k) => text.includes(k))) return "read";
  // 默认创建
  return "create";
}

/**
 * 从搜索文本中提取查询词（read 意图）
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
    /查看\s*(.+)/,
    /显示\s*(.+)/,
    /列出\s*(.+)/,
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
    /(.+?)的?学习路径/,
  ];

  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) return match[1].trim();
  }
  return text;
}

/**
 * 提取更新目标（update 意图）
 * 例："把MCP笔记的状态改为完成" → { query: "MCP笔记", field: "status", value: "complete" }
 * 例："给LangChain添加标签RAG" → { query: "LangChain", field: "tags", value: "RAG" }
 */
export function extractUpdateTarget(text: string): {
  query: string;      // 搜索关键词
  field: string;      // 要更新的字段 (status/tags/content/title)
  value: string;      // 新值
} {
  // 状态更新模式（更精确的模式优先）
  const statusPatterns = [
    // "把...的状态改为..." 模式
    /把\s*["「]?([^"」]+?)["」]?\s*的\s*状态\s*(?:改为|改成|设为|设置)\s*["「]?([^"」]+)["」]?/,
    // "把...改为..." 模式
    /把\s*["「]?([^"」]+?)["」]?\s*(?:改为|改成|设为|设置)\s*["「]?([^"」]+)["」]?/,
    // "把...标记为..." 模式
    /把\s*["「]?([^"」]+?)["」]?\s*标记\s*(?:为|成)\s*["「]?([^"」]+)["」]?/,
    // "标记...为..." 模式（使用非贪婪匹配）
    /标记\s*["「]?([^"」]+?)["」]?\s*为\s*["「]?([^"」]+)["」]?/,
    // "将...改为..." 模式
    /将\s*["「]?([^"」]+?)["」]?\s*(?:改为|改成|设为|设置)\s*["「]?([^"」]+)["」]?/,
  ];

  for (const pattern of statusPatterns) {
    const match = text.match(pattern);
    if (match) {
      const query = match[1].trim();
      const value = match[2].trim();
      // 判断是状态还是内容
      if (STATUS_KEYWORDS.some(k => value.includes(k))) {
        return { query, field: "status", value: STATUS_MAP[value] || value };
      }
      // 默认当作标题或内容更新
      return { query, field: "title", value };
    }
  }

  // 标签更新模式
  const tagPatterns = [
    /给\s*["「]?([^"」]+)["」]?\s*添加?标签\s*["「]?([^"」]+)["」]?/,
    /为\s*["「]?([^"」]+)["」]?\s*添加?标签\s*["「]?([^"」]+)["」]?/,
    /给\s*["「]?([^"」]+)["」]?\s*打上?标签\s*["「]?([^"」]+)["」]?/,
  ];

  for (const pattern of tagPatterns) {
    const match = text.match(pattern);
    if (match) {
      return { query: match[1].trim(), field: "tags", value: match[2].trim() };
    }
  }

  // 通用修改模式
  const generalPattern = /(?:修改|更新|改一下)\s*["「]?([^"」]+)["」]?\s*(?:的)?(.+)/;
  const generalMatch = text.match(generalPattern);
  if (generalMatch) {
    return { query: generalMatch[1].trim(), field: "content", value: generalMatch[2].trim() };
  }

  // 如果都不匹配，返回整个文本作为查询
  return { query: text, field: "", value: "" };
}

/**
 * 提取删除目标（delete 意图）
 * 例："删除测试任务" → { query: "测试任务" }
 */
export function extractDeleteTarget(text: string): {
  query: string;      // 搜索关键词
} {
  const patterns = [
    /删除\s*["「]?([^"」]+)["」]?/,
    /移除\s*["「]?([^"」]+)["」]?/,
    /去掉\s*["「]?([^"」]+)["」]?/,
    /删掉\s*["「]?([^"」]+)["」]?/,
    /不要\s*["「]?([^"」]+)["」]?/,
  ];

  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) return { query: match[1].trim() };
  }
  return { query: text };
}

/**
 * 提取回顾参数（review 意图）
 */
export function extractReviewParams(text: string): {
  type: "daily" | "weekly" | "monthly";
  date?: string;      // 可选的具体日期
} {
  if (/本月|这个月|月报/.test(text)) {
    return { type: "monthly" };
  }
  if (/本周|这周|周报/.test(text)) {
    return { type: "weekly" };
  }
  if (/昨天|昨日/.test(text)) {
    // 返回昨天的日期
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    return { type: "daily", date: yesterday.toISOString().split("T")[0] };
  }
  // 默认今天
  return { type: "daily" };
}

/**
 * 获取帮助信息
 */
export function getHelpMessage(): string {
  return `## 🎯 我能帮你做什么？

**操作类**
- **创建**：明天下午3点开会、记录今天的学习笔记
- **查询**：帮我找 MCP 的笔记、搜索关于 RAG 的内容
- **更新**：把 MCP 笔记改为完成、给学习添加标签 AI
- **删除**：删除测试任务、移除临时记录

**功能类**
- **回顾**：今天做了什么、本周进度、本月统计
- **知识图谱**：MCP 的知识图谱、查看学习路径

**提示**：直接输入内容即可，我会自动识别你的意图！`;
}
