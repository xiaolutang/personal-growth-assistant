import { Lightbulb, FileText, Layers, RotateCcw, HelpCircle } from "lucide-react";
import type { Task, Category, TaskStatus, Priority, SearchResult } from "@/types/task";

/**
 * 将搜索结果归一化为 Task 类型，补齐缺失字段
 */
export function normalizeSearchResult(r: SearchResult): Task {
  return {
    id: r.id ?? "",
    title: r.title ?? "",
    content: "",
    category: (r.category ?? "note") as Category,
    status: (r.status ?? "doing") as TaskStatus,
    priority: (r.priority ?? "medium") as Priority,
    tags: r.tags ?? [],
    created_at: r.created_at ?? "",
    updated_at: "",
    file_path: r.file_path ?? "",
    parent_id: undefined,
    content_snippet: r.content_snippet,
  };
}

export const TABS = [
  { key: "", label: "全部", icon: Layers },
  { key: "inbox", label: "灵感", icon: Lightbulb },
  { key: "note", label: "笔记", icon: FileText },
  { key: "reflection", label: "复盘", icon: RotateCcw },
  { key: "question", label: "疑问", icon: HelpCircle },
] as const;

// F06: 探索页只展示 inbox/note/reflection/question，不含 task/project/decision
export const EXPLORE_CATEGORIES = new Set(["inbox", "note", "reflection", "question"]);

// === 时间范围快选 ===
export type TimeRange = "today" | "week" | "month" | "";

export const TIME_RANGE_LABELS: Record<TimeRange, string> = {
  today: "今天",
  week: "本周",
  month: "本月",
  "": "全部",
};

function formatLocalDateTime(date: Date): string {
  const pad = (value: number, width = 2) => value.toString().padStart(width, "0");
  return [
    date.getFullYear(),
    pad(date.getMonth() + 1),
    pad(date.getDate()),
  ].join("-") + `T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}.${pad(date.getMilliseconds(), 3)}`;
}

export function computeTimeRange(range: TimeRange): { startTime?: string; endTime?: string } {
  const now = new Date();
  const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const endOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59, 999);

  if (range === "today") {
    const s = startOfDay(now);
    const e = endOfDay(now);
    return { startTime: formatLocalDateTime(s), endTime: formatLocalDateTime(e) };
  }
  if (range === "week") {
    const day = now.getDay() || 7;
    const monday = new Date(now);
    monday.setDate(now.getDate() - day + 1);
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    return {
      startTime: formatLocalDateTime(startOfDay(monday)),
      endTime: formatLocalDateTime(endOfDay(sunday)),
    };
  }
  if (range === "month") {
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
    const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    return {
      startTime: formatLocalDateTime(startOfDay(firstDay)),
      endTime: formatLocalDateTime(endOfDay(lastDay)),
    };
  }
  return {};
}

// === 搜索历史管理 ===
const SEARCH_HISTORY_KEY = "search_history";
const MAX_HISTORY = 5;

export function getSearchHistory(): string[] {
  try {
    const raw = localStorage.getItem(SEARCH_HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function addToSearchHistory(query: string) {
  if (!query.trim()) return;
  const history = getSearchHistory().filter((h) => h !== query.trim());
  history.unshift(query.trim());
  localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(history.slice(0, MAX_HISTORY)));
}

export function removeFromSearchHistory(query: string) {
  const history = getSearchHistory().filter((h) => h !== query);
  localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(history));
}

// === 热门标签 ===
export function getPopularTags(entries: Task[], limit = 5): string[] {
  const tagCount: Record<string, number> = {};
  for (const entry of entries) {
    for (const tag of entry.tags || []) {
      tagCount[tag] = (tagCount[tag] || 0) + 1;
    }
  }
  return Object.entries(tagCount)
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([tag]) => tag);
}

export function filterByCategory(entries: Task[], tab: string): Task[] {
  const filtered = entries.filter((t) => EXPLORE_CATEGORIES.has(t.category));
  if (!tab) return filtered;
  return filtered.filter((t) => t.category === tab);
}
