import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  TABS,
  EXPLORE_CATEGORIES,
  normalizeSearchResult,
  computeTimeRange,
  getSearchHistory,
  addToSearchHistory,
  removeFromSearchHistory,
  getPopularTags,
  filterByCategory,
  TIME_RANGE_LABELS,
} from "../utils";
import type { Task, SearchResult } from "@/types/task";

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: vi.fn((key: string) => { delete store[key]; }),
    clear: vi.fn(() => { store = {}; }),
  };
})();
Object.defineProperty(window, "localStorage", { value: localStorageMock });

const makeTask = (overrides: Partial<Task> = {}): Task => ({
  id: "t1",
  title: "Test",
  content: "content",
  category: "note",
  status: "doing",
  priority: "medium",
  tags: [],
  created_at: "2024-01-01T00:00:00",
  updated_at: "2024-01-01T00:00:00",
  file_path: "",
  ...overrides,
});

describe("utils", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  // --- TABS constant ---
  describe("TABS", () => {
    it("F06: 包含 5 个 tab 配置项（全部/灵感/笔记/复盘/疑问）", () => {
      expect(TABS).toHaveLength(5);
    });

    it("第一个 tab 是全部（key 为空字符串）", () => {
      expect(TABS[0].key).toBe("");
      expect(TABS[0].label).toBe("全部");
    });

    it("每个 tab 都有 key, label, icon", () => {
      for (const tab of TABS) {
        expect(tab).toHaveProperty("key");
        expect(tab).toHaveProperty("label");
        expect(tab).toHaveProperty("icon");
      }
    });

    it("F06: 不包含 project 和 decision tab", () => {
      const keys = TABS.map(t => t.key);
      expect(keys).not.toContain("project");
      expect(keys).not.toContain("decision");
    });

    it("F06: 包含全部/灵感/笔记/复盘/疑问", () => {
      const keys = TABS.map(t => t.key);
      expect(keys).toEqual(["", "inbox", "note", "reflection", "question"]);
    });
  });

  // --- EXPLORE_CATEGORIES ---
  describe("EXPLORE_CATEGORIES", () => {
    it("F06: 只包含 inbox, note, reflection, question", () => {
      expect(EXPLORE_CATEGORIES.has("inbox")).toBe(true);
      expect(EXPLORE_CATEGORIES.has("note")).toBe(true);
      expect(EXPLORE_CATEGORIES.has("reflection")).toBe(true);
      expect(EXPLORE_CATEGORIES.has("question")).toBe(true);
    });

    it("F06: 不包含 task", () => {
      expect(EXPLORE_CATEGORIES.has("task")).toBe(false);
    });

    it("F06: 不包含 project 和 decision", () => {
      expect(EXPLORE_CATEGORIES.has("project")).toBe(false);
      expect(EXPLORE_CATEGORIES.has("decision")).toBe(false);
    });

    it("F06: 恰好包含 4 个类型", () => {
      expect(EXPLORE_CATEGORIES.size).toBe(4);
    });
  });

  // --- normalizeSearchResult ---
  describe("normalizeSearchResult", () => {
    it("将 SearchResult 归一化为 Task", () => {
      const sr: SearchResult = {
        id: "sr1",
        title: "Search Hit",
        score: 0.95,
        type: "note",
        category: "note",
        status: "doing",
        tags: ["tag1"],
        created_at: "2024-06-01",
        file_path: "/data/note.md",
        content_snippet: "some snippet",
      };

      const task = normalizeSearchResult(sr);
      expect(task.id).toBe("sr1");
      expect(task.title).toBe("Search Hit");
      expect(task.content).toBe("");
      expect(task.category).toBe("note");
      expect(task.status).toBe("doing");
      expect(task.priority).toBe("medium");
      expect(task.tags).toEqual(["tag1"]);
      expect(task.content_snippet).toBe("some snippet");
    });

    it("缺失字段使用默认值", () => {
      const sr: SearchResult = {
        id: "",
        title: "",
        score: 0,
        type: "",
        category: undefined as any,
        status: undefined as any,
        tags: undefined as any,
        created_at: "",
        file_path: "",
      };
      const task = normalizeSearchResult(sr);
      expect(task.category).toBe("note");
      expect(task.status).toBe("doing");
      expect(task.priority).toBe("medium");
      expect(task.tags).toEqual([]);
    });
  });

  // --- computeTimeRange ---
  describe("computeTimeRange", () => {
    it("空字符串返回空对象", () => {
      expect(computeTimeRange("")).toEqual({});
    });

    it("返回本地无时区时间字符串，避免 UTC 跨天偏移", () => {
      const result = computeTimeRange("today");
      expect(result.startTime).toBeTruthy();
      expect(result.endTime).toBeTruthy();
      expect(result.startTime).not.toContain("Z");
      expect(result.endTime).not.toContain("Z");
    });

    it("today 返回今天的起止时间", () => {
      const result = computeTimeRange("today");
      expect(result.startTime).toBeTruthy();
      expect(result.endTime).toBeTruthy();
      const start = new Date(result.startTime!);
      const end = new Date(result.endTime!);
      expect(start.getHours()).toBe(0);
      expect(end.getHours()).toBe(23);
      expect(end.getMinutes()).toBe(59);
    });

    it("week 返回本周的起止日期", () => {
      const result = computeTimeRange("week");
      expect(result.startTime).toBeTruthy();
      expect(result.endTime).toBeTruthy();
      // 验证 startTime 是周一（getDay() === 1）
      const start = new Date(result.startTime!);
      expect(start.getDay()).toBe(1);
      // endTime 是周日
      const end = new Date(result.endTime!);
      expect(end.getDay()).toBe(0);
    });

    it("month 返回本月的起止日期", () => {
      const result = computeTimeRange("month");
      expect(result.startTime).toBeTruthy();
      expect(result.endTime).toBeTruthy();
      // 验证 startTime 是当月 1 号
      const start = new Date(result.startTime!);
      expect(start.getDate()).toBe(1);
      // endTime 是当月最后一天
      const end = new Date(result.endTime!);
      expect(end.getMilliseconds()).toBe(999);
      const nextDay = new Date(end);
      nextDay.setDate(nextDay.getDate() + 1);
      expect(nextDay.getDate()).toBe(1); // 下一天是下月1号
    });
  });

  // --- TIME_RANGE_LABELS ---
  describe("TIME_RANGE_LABELS", () => {
    it("包含所有 key 的中文标签", () => {
      expect(TIME_RANGE_LABELS[""]).toBe("全部");
      expect(TIME_RANGE_LABELS["today"]).toBe("今天");
      expect(TIME_RANGE_LABELS["week"]).toBe("本周");
      expect(TIME_RANGE_LABELS["month"]).toBe("本月");
    });
  });

  // --- 搜索历史 ---
  describe("getSearchHistory", () => {
    it("空 localStorage 返回空数组", () => {
      expect(getSearchHistory()).toEqual([]);
    });

    it("正常读取历史", () => {
      localStorageMock.setItem("search_history", JSON.stringify(["query1", "query2"]));
      expect(getSearchHistory()).toEqual(["query1", "query2"]);
    });

    it("损坏数据返回空数组", () => {
      localStorageMock.setItem("search_history", "not-json");
      expect(getSearchHistory()).toEqual([]);
    });
  });

  describe("addToSearchHistory", () => {
    it("添加新查询到历史头部", () => {
      addToSearchHistory("new query");
      const history = getSearchHistory();
      expect(history[0]).toBe("new query");
    });

    it("重复查询移到头部不重复", () => {
      addToSearchHistory("q1");
      addToSearchHistory("q2");
      addToSearchHistory("q1"); // move to front
      const history = getSearchHistory();
      expect(history[0]).toBe("q1");
      expect(history.filter((h) => h === "q1")).toHaveLength(1);
    });

    it("最多保留 5 条", () => {
      for (let i = 0; i < 7; i++) addToSearchHistory(`q${i}`);
      const history = getSearchHistory();
      expect(history).toHaveLength(5);
    });

    it("空查询不添加", () => {
      addToSearchHistory("  ");
      expect(getSearchHistory()).toEqual([]);
    });
  });

  describe("removeFromSearchHistory", () => {
    it("移除指定查询", () => {
      addToSearchHistory("q1");
      addToSearchHistory("q2");
      removeFromSearchHistory("q1");
      expect(getSearchHistory()).toEqual(["q2"]);
    });
  });

  // --- getPopularTags ---
  describe("getPopularTags", () => {
    it("返回按频次排序的标签", () => {
      const entries = [
        makeTask({ tags: ["a", "b"] }),
        makeTask({ tags: ["a", "c"] }),
        makeTask({ tags: ["a"] }),
      ];
      expect(getPopularTags(entries)).toEqual(["a", "b", "c"]);
    });

    it("默认限制 5 个", () => {
      const entries = Array.from({ length: 8 }, (_, i) =>
        makeTask({ tags: [`tag${i}`] })
      );
      expect(getPopularTags(entries)).toHaveLength(5);
    });

    it("空数组返回空", () => {
      expect(getPopularTags([])).toEqual([]);
    });
  });

  // --- filterByCategory ---
  describe("filterByCategory", () => {
    it("空 tab 返回所有探索分类条目（不含 task/project/decision）", () => {
      const entries = [
        makeTask({ category: "note" }),
        makeTask({ category: "task" }),
        makeTask({ category: "inbox" }),
      ];
      const result = filterByCategory(entries, "");
      expect(result).toHaveLength(2);
      expect(result.every((t) => t.category !== "task")).toBe(true);
    });

    it("指定 tab 过滤对应分类", () => {
      const entries = [
        makeTask({ category: "note" }),
        makeTask({ category: "inbox" }),
      ];
      const result = filterByCategory(entries, "note");
      expect(result).toHaveLength(1);
      expect(result[0].category).toBe("note");
    });

    it("F06: 灵感 tab 只显示 inbox 类型", () => {
      const entries = [
        makeTask({ category: "note" }),
        makeTask({ category: "inbox" }),
        makeTask({ category: "task" }),
      ];
      const result = filterByCategory(entries, "inbox");
      expect(result).toHaveLength(1);
      expect(result[0].category).toBe("inbox");
    });
  });

  // --- filterByCategory 搜索模式跨类型混合展示 (F132) ---
  describe("filterByCategory — 搜索模式（tab=空）跨类型混合展示", () => {
    it("F06: tab 为空时排除 task/project/decision 等非 Explore 类型", () => {
      const entries = [
        makeTask({ category: "note" }),
        makeTask({ category: "task" }),
        makeTask({ category: "inbox" }),
        makeTask({ category: "project" }),
        makeTask({ category: "decision" }),
      ];
      const result = filterByCategory(entries, "");
      expect(result).toHaveLength(2);
      expect(result.every((t) => t.category !== "task")).toBe(true);
      expect(result.every((t) => t.category !== "project")).toBe(true);
      expect(result.every((t) => t.category !== "decision")).toBe(true);
    });

    it("F06: tab 为空时只保留 inbox/note/reflection/question", () => {
      const entries = [
        makeTask({ category: "note" }),
        makeTask({ category: "inbox" }),
        makeTask({ category: "reflection" }),
        makeTask({ category: "question" }),
      ];
      const result = filterByCategory(entries, "");
      expect(result).toHaveLength(4);
    });

    it("空数组返回空", () => {
      expect(filterByCategory([], "")).toEqual([]);
    });
  });
});
