import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { act } from "@testing-library/react";
import { useTaskStore } from "./taskStore";
import { ApiError } from "@/lib/errors";
import type { Task, SearchResult } from "@/types/task";

// Mock API module
vi.mock("@/services/api", () => ({
  getEntries: vi.fn(),
  createEntry: vi.fn(),
  updateEntry: vi.fn(),
  deleteEntry: vi.fn(),
  searchEntries: vi.fn(),
  getKnowledgeGraph: vi.fn(),
}));

import {
  getEntries,
  createEntry as apiCreateEntry,
  updateEntry as apiUpdateEntry,
  deleteEntry as apiDeleteEntry,
  searchEntries as apiSearchEntries,
} from "@/services/api";

const mockGetEntries = vi.mocked(getEntries);
const mockCreateEntry = vi.mocked(apiCreateEntry);
const mockUpdateEntry = vi.mocked(apiUpdateEntry);
const mockDeleteEntry = vi.mocked(apiDeleteEntry);
const mockSearchEntries = vi.mocked(apiSearchEntries);

// === 测试数据工厂 ===
function createMockTask(overrides: Partial<Task> = {}): Task {
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

function createMockSearchResult(overrides: Partial<SearchResult> = {}): SearchResult {
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

// === 重置 store 状态辅助函数 ===
function resetStore() {
  useTaskStore.setState({
    tasks: [],
    error: null,
    serviceUnavailable: false,
    isLoading: false,
    searchResults: [],
    knowledgeGraph: null,
  });
}

// === 顶层统一重置 ===
beforeEach(() => {
  resetStore();
  vi.clearAllMocks();
});

// ============================================================
// fetchEntries 测试
// ============================================================
describe("fetchEntries", () => {
  it("正常获取条目并更新 tasks 状态", async () => {
    const mockTasks = [
      createMockTask({ id: "1", title: "任务A" }),
      createMockTask({ id: "2", title: "任务B" }),
    ];
    mockGetEntries.mockResolvedValueOnce({ entries: mockTasks });

    await act(async () => {
      await useTaskStore.getState().fetchEntries();
    });

    const state = useTaskStore.getState();
    expect(state.tasks).toHaveLength(2);
    expect(state.tasks[0].title).toBe("任务A");
    expect(state.tasks[1].title).toBe("任务B");
    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
    expect(state.serviceUnavailable).toBe(false);
  });

  it("传入参数调用 getEntries", async () => {
    mockGetEntries.mockResolvedValueOnce({ entries: [] });

    await act(async () => {
      await useTaskStore.getState().fetchEntries({
        type: "task",
        status: "doing",
        limit: 10,
      });
    });

    expect(mockGetEntries).toHaveBeenCalledWith({
      type: "task",
      status: "doing",
      limit: 10,
    });
  });

  it("请求中设置 isLoading 为 true", async () => {
    let resolvePromise: (value: any) => void;
    const pending = new Promise((resolve) => {
      resolvePromise = resolve;
    });
    mockGetEntries.mockReturnValueOnce(pending as any);

    const promise = useTaskStore.getState().fetchEntries();

    // 请求进行中
    expect(useTaskStore.getState().isLoading).toBe(true);

    resolvePromise!({ entries: [] });
    await act(async () => {
      await promise;
    });

    expect(useTaskStore.getState().isLoading).toBe(false);
  });

  it("503 错误设置 serviceUnavailable 为 true", async () => {
    mockGetEntries.mockRejectedValueOnce(new ApiError(503, "存储服务未初始化"));

    await act(async () => {
      await useTaskStore.getState().fetchEntries({ type: "task" });
    });

    const state = useTaskStore.getState();
    expect(state.serviceUnavailable).toBe(true);
    expect(state.error).toBe("存储服务未初始化");
    expect(state.tasks).toEqual([]);
  });

  it("非 503 错误不设置 serviceUnavailable", async () => {
    mockGetEntries.mockRejectedValueOnce(new ApiError(500, "内部错误"));

    await act(async () => {
      await useTaskStore.getState().fetchEntries({ type: "task" });
    });

    const state = useTaskStore.getState();
    expect(state.serviceUnavailable).toBe(false);
    expect(state.error).toBe("内部错误");
    expect(state.isLoading).toBe(false);
  });

  it("非 ApiError 类型的错误使用默认消息", async () => {
    mockGetEntries.mockRejectedValueOnce(new Error("网络断开"));

    await act(async () => {
      await useTaskStore.getState().fetchEntries();
    });

    const state = useTaskStore.getState();
    expect(state.error).toBe("网络断开");
    expect(state.isLoading).toBe(false);
  });

  it("非 Error 实例的错误使用默认消息", async () => {
    mockGetEntries.mockRejectedValueOnce("未知错误字符串");

    await act(async () => {
      await useTaskStore.getState().fetchEntries();
    });

    const state = useTaskStore.getState();
    expect(state.error).toBe("获取条目失败");
  });

  it("重试成功后 serviceUnavailable 恢复为 false", async () => {
    // 第一次：503
    mockGetEntries.mockRejectedValueOnce(new ApiError(503, "存储服务未初始化"));
    await act(async () => {
      await useTaskStore.getState().fetchEntries({ type: "task" });
    });
    expect(useTaskStore.getState().serviceUnavailable).toBe(true);

    // 第二次：成功
    mockGetEntries.mockResolvedValueOnce({
      entries: [createMockTask({ id: "1", title: "测试" })],
    });
    await act(async () => {
      await useTaskStore.getState().fetchEntries({ type: "task" });
    });

    const state = useTaskStore.getState();
    expect(state.serviceUnavailable).toBe(false);
    expect(state.tasks).toHaveLength(1);
  });
});

// ============================================================
// addTasks 测试（批量并行创建）
// ============================================================
describe("addTasks", () => {
  it("并行创建多个任务", async () => {
    const tasks = [
      {
        type: "task",
        title: "任务1",
        content: "内容1",
        category: "task" as const,
        status: "doing" as const,
      },
      {
        type: "task",
        title: "任务2",
        content: "内容2",
        category: "task" as const,
        status: "waitStart" as const,
      },
    ];

    // createEntry 被调用后 fetchEntries 会再次调用 getEntries
    mockCreateEntry.mockResolvedValueOnce(createMockTask({ id: "c1" }));
    mockCreateEntry.mockResolvedValueOnce(createMockTask({ id: "c2" }));
    mockGetEntries.mockResolvedValueOnce({
      entries: [
        createMockTask({ id: "c1", title: "任务1" }),
        createMockTask({ id: "c2", title: "任务2" }),
      ],
    });

    await act(async () => {
      await useTaskStore.getState().addTasks(tasks);
    });

    // 验证 createEntry 被调用两次（并行）
    expect(mockCreateEntry).toHaveBeenCalledTimes(2);
    expect(mockCreateEntry).toHaveBeenCalledWith({
      type: "task",
      title: "任务1",
      content: "内容1",
      tags: undefined,
    });
    expect(mockCreateEntry).toHaveBeenCalledWith({
      type: "task",
      title: "任务2",
      content: "内容2",
      tags: undefined,
    });

    // 创建完成后重新获取列表
    expect(mockGetEntries).toHaveBeenCalledTimes(1);
    const state = useTaskStore.getState();
    expect(state.tasks).toHaveLength(2);
    expect(state.isLoading).toBe(false);
  });

  it("创建任务时传递 tags", async () => {
    const tasks = [
      {
        type: "task",
        title: "带标签任务",
        category: "task" as const,
        status: "doing" as const,
        tags: ["tag1", "tag2"],
      },
    ];

    mockCreateEntry.mockResolvedValueOnce(createMockTask());
    mockGetEntries.mockResolvedValueOnce({ entries: [] });

    await act(async () => {
      await useTaskStore.getState().addTasks(tasks);
    });

    expect(mockCreateEntry).toHaveBeenCalledWith({
      type: "task",
      title: "带标签任务",
      content: undefined,
      tags: ["tag1", "tag2"],
    });
  });

  it("创建失败时设置错误消息", async () => {
    const tasks = [
      {
        type: "task",
        title: "失败任务",
        category: "task" as const,
        status: "doing" as const,
      },
    ];

    mockCreateEntry.mockRejectedValueOnce(new Error("创建失败"));

    await act(async () => {
      await useTaskStore.getState().addTasks(tasks);
    });

    const state = useTaskStore.getState();
    expect(state.error).toBe("创建失败");
    expect(state.isLoading).toBe(false);
  });

  it("空数组不调用 createEntry", async () => {
    mockGetEntries.mockResolvedValueOnce({ entries: [] });

    await act(async () => {
      await useTaskStore.getState().addTasks([]);
    });

    expect(mockCreateEntry).not.toHaveBeenCalled();
    // 但 fetchEntries 仍会被调用
    expect(mockGetEntries).toHaveBeenCalledTimes(1);
  });
});

// ============================================================
// updateTaskStatus 测试
// ============================================================
describe("updateTaskStatus", () => {
  it("调用 API 更新状态并重新获取列表", async () => {
    mockUpdateEntry.mockResolvedValueOnce({ success: true, message: "ok" });
    mockGetEntries.mockResolvedValueOnce({
      entries: [
        createMockTask({ id: "1", status: "complete" }),
      ],
    });

    await act(async () => {
      await useTaskStore.getState().updateTaskStatus("1", "complete");
    });

    expect(mockUpdateEntry).toHaveBeenCalledWith("1", { status: "complete" });
    expect(mockGetEntries).toHaveBeenCalledTimes(1);

    const state = useTaskStore.getState();
    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
  });

  it("更新失败时设置错误消息", async () => {
    mockUpdateEntry.mockRejectedValueOnce(new Error("更新失败"));

    await act(async () => {
      await useTaskStore.getState().updateTaskStatus("1", "doing");
    });

    const state = useTaskStore.getState();
    expect(state.error).toBe("更新失败");
    expect(state.isLoading).toBe(false);
  });

  it("非 Error 类型的失败使用默认消息", async () => {
    mockUpdateEntry.mockRejectedValueOnce("字符串错误");

    await act(async () => {
      await useTaskStore.getState().updateTaskStatus("1", "doing");
    });

    const state = useTaskStore.getState();
    expect(state.error).toBe("更新状态失败");
  });
});

// ============================================================
// deleteTask 测试（乐观更新 + 失败回滚）
// ============================================================
describe("deleteTask", () => {
  it("乐观更新：立即从本地列表中移除任务", async () => {
    const task1 = createMockTask({ id: "1", title: "任务1" });
    const task2 = createMockTask({ id: "2", title: "任务2" });

    // 先设置初始任务列表
    useTaskStore.setState({ tasks: [task1, task2] });

    mockDeleteEntry.mockResolvedValueOnce({ success: true, message: "ok" });
    mockGetEntries.mockResolvedValueOnce({
      entries: [task2],
    });

    const promise = useTaskStore.getState().deleteTask("1");

    // 在 API 返回之前，任务已从本地移除（乐观更新）
    expect(useTaskStore.getState().tasks).toHaveLength(1);
    expect(useTaskStore.getState().tasks[0].id).toBe("2");

    await act(async () => {
      await promise;
    });

    // API 调用成功后重新获取列表
    expect(mockDeleteEntry).toHaveBeenCalledWith("1");
    expect(mockGetEntries).toHaveBeenCalledTimes(1);
  });

  it("删除成功后重新获取列表以确保数据一致", async () => {
    const task1 = createMockTask({ id: "1" });
    useTaskStore.setState({ tasks: [task1] });

    mockDeleteEntry.mockResolvedValueOnce({ success: true, message: "ok" });
    mockGetEntries.mockResolvedValueOnce({ entries: [] });

    await act(async () => {
      await useTaskStore.getState().deleteTask("1");
    });

    const state = useTaskStore.getState();
    expect(state.tasks).toHaveLength(0);
    expect(state.error).toBeNull();
  });

  it("失败时回滚到之前的任务列表", async () => {
    const task1 = createMockTask({ id: "1", title: "任务1" });
    const task2 = createMockTask({ id: "2", title: "任务2" });
    useTaskStore.setState({ tasks: [task1, task2] });

    mockDeleteEntry.mockRejectedValueOnce(new Error("删除失败"));

    await act(async () => {
      await useTaskStore.getState().deleteTask("1");
    });

    const state = useTaskStore.getState();
    // 回滚：任务列表恢复原样
    expect(state.tasks).toHaveLength(2);
    expect(state.tasks[0].id).toBe("1");
    expect(state.tasks[1].id).toBe("2");
    expect(state.error).toBe("删除失败");
  });

  it("回滚时非 Error 类型使用默认消息", async () => {
    const task1 = createMockTask({ id: "1" });
    useTaskStore.setState({ tasks: [task1] });

    mockDeleteEntry.mockRejectedValueOnce("网络错误");

    await act(async () => {
      await useTaskStore.getState().deleteTask("1");
    });

    const state = useTaskStore.getState();
    expect(state.error).toBe("删除失败");
    expect(state.tasks).toHaveLength(1);
  });
});

// ============================================================
// searchEntries 测试
// ============================================================
describe("searchEntries", () => {
  it("正常搜索并存储结果", async () => {
    const mockResults = [
      createMockSearchResult({ id: "r1", title: "结果1", score: 0.95 }),
      createMockSearchResult({ id: "r2", title: "结果2", score: 0.8 }),
    ];
    mockSearchEntries.mockResolvedValueOnce({ results: mockResults });

    const result = await act(async () => {
      return useTaskStore.getState().searchEntries("测试查询");
    });

    expect(mockSearchEntries).toHaveBeenCalledWith("测试查询", 5);
    expect(result).toHaveLength(2);
    expect(result![0].title).toBe("结果1");
    expect(result![1].title).toBe("结果2");

    const state = useTaskStore.getState();
    expect(state.searchResults).toHaveLength(2);
    expect(state.searchResults[0].score).toBe(0.95);
    expect(state.isLoading).toBe(false);
  });

  it("传入自定义 limit 参数", async () => {
    mockSearchEntries.mockResolvedValueOnce({ results: [] });

    await act(async () => {
      await useTaskStore.getState().searchEntries("查询", 10);
    });

    expect(mockSearchEntries).toHaveBeenCalledWith("查询", 10);
  });

  it("搜索失败时返回空数组并设置错误", async () => {
    mockSearchEntries.mockRejectedValueOnce(new Error("搜索服务不可用"));

    const result = await act(async () => {
      return useTaskStore.getState().searchEntries("查询");
    });

    expect(result).toEqual([]);
    const state = useTaskStore.getState();
    expect(state.error).toBe("搜索服务不可用");
    expect(state.isLoading).toBe(false);
  });

  it("搜索失败时非 Error 类型使用默认消息", async () => {
    mockSearchEntries.mockRejectedValueOnce("超时");

    await act(async () => {
      await useTaskStore.getState().searchEntries("查询");
    });

    const state = useTaskStore.getState();
    expect(state.error).toBe("搜索失败");
  });

  it("clearSearchResults 清空搜索结果", () => {
    useTaskStore.setState({
      searchResults: [
        createMockSearchResult({ id: "r1" }),
        createMockSearchResult({ id: "r2" }),
      ],
    });

    useTaskStore.getState().clearSearchResults();

    expect(useTaskStore.getState().searchResults).toEqual([]);
  });
});

// ============================================================
// getTodayTasks 测试
// ============================================================
describe("getTodayTasks", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-04-11T10:00:00"));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("返回 planned_date 为今天的任务", () => {
    const task1 = createMockTask({
      id: "1",
      planned_date: "2026-04-11T10:00:00",
    });
    const task2 = createMockTask({
      id: "2",
      planned_date: "2020-01-01T10:00:00",
    });

    useTaskStore.setState({ tasks: [task1, task2] });

    const result = useTaskStore.getState().getTodayTasks();
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe("1");
  });

  it("没有 planned_date 时按 created_at 过滤", () => {
    const task1 = createMockTask({
      id: "1",
      planned_date: undefined,
      created_at: "2026-04-11T08:00:00",
    });
    const task2 = createMockTask({
      id: "2",
      planned_date: undefined,
      created_at: "2020-06-15T08:00:00",
    });

    useTaskStore.setState({ tasks: [task1, task2] });

    const result = useTaskStore.getState().getTodayTasks();
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe("1");
  });

  it("planned_date 优先于 created_at", () => {
    const task = createMockTask({
      id: "1",
      planned_date: "2026-04-11T10:00:00",
      created_at: "2020-01-01T08:00:00",
    });

    useTaskStore.setState({ tasks: [task] });

    const result = useTaskStore.getState().getTodayTasks();
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe("1");
  });

  it("planned_date 不是今天但 created_at 是今天时，使用 planned_date 判断", () => {
    const task = createMockTask({
      id: "1",
      planned_date: "2020-01-01T10:00:00",
      created_at: "2026-04-11T08:00:00",
    });

    useTaskStore.setState({ tasks: [task] });

    const result = useTaskStore.getState().getTodayTasks();
    // planned_date 存在但不是今天，所以不返回
    expect(result).toHaveLength(0);
  });

  it("没有日期字段的任务不返回", () => {
    const task = createMockTask({
      id: "1",
      planned_date: undefined,
      created_at: "",
    });

    useTaskStore.setState({ tasks: [task] });

    const result = useTaskStore.getState().getTodayTasks();
    expect(result).toHaveLength(0);
  });

  it("空任务列表返回空数组", () => {
    useTaskStore.setState({ tasks: [] });
    const result = useTaskStore.getState().getTodayTasks();
    expect(result).toEqual([]);
  });
});

// ============================================================
// 辅助方法测试
// ============================================================
describe("getTasksByCategory", () => {
  it("按分类过滤任务", () => {
    useTaskStore.setState({
      tasks: [
        createMockTask({ id: "1", category: "task" }),
        createMockTask({ id: "2", category: "inbox" }),
        createMockTask({ id: "3", category: "task" }),
      ],
    });

    const result = useTaskStore.getState().getTasksByCategory("task");
    expect(result).toHaveLength(2);
    expect(result.every((t) => t.category === "task")).toBe(true);
  });
});

describe("getTasksByStatus", () => {
  it("按状态过滤任务", () => {
    useTaskStore.setState({
      tasks: [
        createMockTask({ id: "1", status: "doing" }),
        createMockTask({ id: "2", status: "complete" }),
        createMockTask({ id: "3", status: "doing" }),
      ],
    });

    const result = useTaskStore.getState().getTasksByStatus("doing");
    expect(result).toHaveLength(2);
    expect(result.every((t) => t.status === "doing")).toBe(true);
  });
});
