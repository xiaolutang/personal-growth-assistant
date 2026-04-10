import { describe, it, expect, beforeEach, vi } from "vitest";
import { act } from "@testing-library/react";
import { useTaskStore } from "./taskStore";
import { ApiError } from "@/lib/errors";

// Mock API module
vi.mock("@/services/api", () => ({
  getEntries: vi.fn(),
  createEntry: vi.fn(),
  updateEntry: vi.fn(),
  deleteEntry: vi.fn(),
  searchEntries: vi.fn(),
  getKnowledgeGraph: vi.fn(),
}));

import { getEntries } from "@/services/api";

const mockGetEntries = vi.mocked(getEntries);

describe("taskStore 503 降级处理", () => {
  beforeEach(() => {
    // 重置 store 状态
    const store = useTaskStore.getState();
    store.tasks = [];
    store.error = null;
    store.serviceUnavailable = false;
    store.isLoading = false;
    vi.clearAllMocks();
  });

  it("503 响应设置 serviceUnavailable 为 true", async () => {
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
  });

  it("重试成功后 serviceUnavailable 恢复为 false", async () => {
    // 第一次：503
    mockGetEntries.mockRejectedValueOnce(new ApiError(503, "存储服务未初始化"));
    await act(async () => {
      await useTaskStore.getState().fetchEntries({ type: "task" });
    });
    expect(useTaskStore.getState().serviceUnavailable).toBe(true);

    // 第二次：成功
    mockGetEntries.mockResolvedValueOnce({ entries: [{ id: "1", title: "测试" }] as any });
    await act(async () => {
      await useTaskStore.getState().fetchEntries({ type: "task" });
    });

    const state = useTaskStore.getState();
    expect(state.serviceUnavailable).toBe(false);
    expect(state.tasks).toHaveLength(1);
  });
});
