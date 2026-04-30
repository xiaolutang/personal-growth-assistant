import { vi } from "vitest";
import { useTaskStore } from "@/stores/taskStore";
import type { Task, SearchResult } from "@/types/task";

// === API Mock 模板 ===
export const apiMockFactory = () => ({
  getEntries: vi.fn(),
  createEntry: vi.fn(),
  updateEntry: vi.fn(),
  deleteEntry: vi.fn(),
  searchEntries: vi.fn(),
  getKnowledgeGraph: vi.fn(),
});

// === Store 重置 ===
export function resetStore() {
  useTaskStore.setState({
    tasks: [],
    error: null,
    serviceUnavailable: false,
    isFetching: false,
    isCreating: false,
    isLoading: false,
    searchResults: [],
    knowledgeGraph: null,
  });
}

// === Mock 数据工厂 ===
export function createMockTask(overrides: Partial<Task> = {}): Task {
  return {
    id: `task-${Math.random().toString(36).slice(2, 8)}`,
    title: "测试任务",
    content: "测试内容",
    category: "task",
    status: "doing",
    tags: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    file_path: "test.md",
    ...overrides,
  };
}

export function createMockSearchResult(overrides: Partial<SearchResult> = {}): SearchResult {
  return {
    id: `result-${Math.random().toString(36).slice(2, 8)}`,
    title: "搜索结果",
    score: 0.95,
    type: "task",
    category: "task",
    status: "doing",
    tags: [],
    created_at: new Date().toISOString(),
    file_path: "test.md",
    ...overrides,
  };
}
