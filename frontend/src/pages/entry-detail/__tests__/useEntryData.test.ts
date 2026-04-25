import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import type { Task } from "@/types/task";
import { ApiError } from "@/lib/errors";
/* eslint-disable @typescript-eslint/no-explicit-any */

// Mock react-router-dom
const mockParams = { id: "entry-1" };
vi.mock("react-router-dom", () => ({
  useParams: () => mockParams,
}));

// Mock API calls
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let getEntryMock = vi.fn() as any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let getEntriesMock = vi.fn() as any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let getProjectProgressMock = vi.fn() as any;

vi.mock("@/services/api", () => ({
  getEntry: (...args: any[]) => getEntryMock(...args),
  getEntries: (...args: any[]) => getEntriesMock(...args),
  getProjectProgress: (...args: any[]) => getProjectProgressMock(...args),
}));

import { useEntryData } from "../useEntryData";

const makeTask = (overrides: Partial<Task> = {}): Task => ({
  id: "entry-1",
  title: "Test Entry",
  content: "Test content",
  category: "note",
  status: "doing",
  priority: "medium",
  tags: [],
  created_at: "2024-01-01T00:00:00",
  updated_at: "2024-01-01T00:00:00",
  file_path: "",
  ...overrides,
});

describe("useEntryData", () => {
  beforeEach(() => {
    getEntryMock = vi.fn().mockResolvedValue(makeTask());
    getEntriesMock = vi.fn().mockResolvedValue({ entries: [], total: 0 });
    getProjectProgressMock = vi.fn().mockResolvedValue(null);
  });

  it("初始加载 entry 数据", async () => {
    const { result } = renderHook(() => useEntryData());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.entry).toBeTruthy();
    expect(result.current.entry?.id).toBe("entry-1");
    expect(result.current.error).toBeNull();
    expect(result.current.serviceUnavailable).toBe(false);
  });

  it("503 错误设置 serviceUnavailable=true", async () => {
    getEntryMock.mockRejectedValue(new ApiError(503, "Service Unavailable", {}));

    const { result } = renderHook(() => useEntryData());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.serviceUnavailable).toBe(true);
    expect(result.current.entry).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("非 503 错误设置 error 信息", async () => {
    getEntryMock.mockRejectedValue(new ApiError(500, "Server Error", {}));

    const { result } = renderHook(() => useEntryData());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe("Server Error");
    expect(result.current.serviceUnavailable).toBe(false);
  });

  it("旧请求的 503 不会覆盖新请求的成功结果", async () => {
    let resolveOld: (v: Task) => void;
    const oldPromise = new Promise<Task>((r) => { resolveOld = r; });

    let callCount = 0;
    getEntryMock.mockImplementation(() => {
      callCount++;
      if (callCount === 1) return oldPromise;
      return Promise.resolve(makeTask({ id: "entry-2", title: "New Entry" }));
    });

    const { result } = renderHook(() => useEntryData());

    // 等第一次调用开始
    await waitFor(() => expect(getEntryMock).toHaveBeenCalledTimes(1));

    // 模拟路由切换：id 变化
    mockParams.id = "entry-2";

    // 触发重新渲染（id 变化后 hook 重新执行）
    result.current.reloadEntry();

    await waitFor(() => expect(getEntryMock).toHaveBeenCalledTimes(2));

    // 等新请求完成
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.entry?.id).toBe("entry-2");
    expect(result.current.serviceUnavailable).toBe(false);

    // 旧请求现在以 503 返回
    await act(async () => {
      resolveOld!(makeTask({ id: "entry-1" }));
      // 让微任务排空
      await new Promise((r) => setTimeout(r, 0));
    });

    // 新请求结果不受影响
    expect(result.current.entry?.id).toBe("entry-2");
    expect(result.current.serviceUnavailable).toBe(false);
  });

  it("retryService 清除 503 状态并重新加载", async () => {
    getEntryMock.mockRejectedValueOnce(new ApiError(503, "Service Unavailable", {}));
    getEntryMock.mockResolvedValue(makeTask());

    const { result } = renderHook(() => useEntryData());

    await waitFor(() => {
      expect(result.current.serviceUnavailable).toBe(true);
    });

    // retry
    await act(async () => {
      result.current.retryService(result.current.reloadEntry);
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.serviceUnavailable).toBe(false);
    expect(result.current.entry).toBeTruthy();
  });

  it("retryService 后再次 503 重新进入降级态", async () => {
    getEntryMock.mockRejectedValueOnce(new ApiError(503, "Service Unavailable", {}));
    getEntryMock.mockRejectedValueOnce(new ApiError(503, "Service Unavailable", {}));

    const { result } = renderHook(() => useEntryData());

    await waitFor(() => {
      expect(result.current.serviceUnavailable).toBe(true);
    });

    await act(async () => {
      result.current.retryService(result.current.reloadEntry);
    });

    await waitFor(() => {
      expect(result.current.serviceUnavailable).toBe(true);
    });
  });

  it("project 类型条目加载 childTasks 和 projectProgress", async () => {
    getEntryMock.mockResolvedValue(makeTask({ category: "project" }));
    getEntriesMock.mockResolvedValue({ entries: [makeTask({ id: "child-1" })], total: 1 });
    getProjectProgressMock.mockResolvedValue({ total: 5, completed: 3 });

    const { result } = renderHook(() => useEntryData());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.childTasks).toHaveLength(1);
    expect(result.current.projectProgress).toBeTruthy();
  });

  it("过期请求不写入 isLoading/error/serviceUnavailable", async () => {
    let resolveOld: (v: Task) => void;
    const oldPromise = new Promise<Task>((r) => { resolveOld = r; });

    let callCount = 0;
    getEntryMock.mockImplementation(() => {
      callCount++;
      if (callCount === 1) return oldPromise;
      return Promise.resolve(makeTask({ id: "entry-2" }));
    });

    const { result } = renderHook(() => useEntryData());

    await waitFor(() => expect(getEntryMock).toHaveBeenCalledTimes(1));

    // 新请求
    mockParams.id = "entry-2";
    await act(async () => {
      await result.current.reloadEntry();
    });

    // 新请求已完成
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();

    // 旧请求现在以 error 返回
    await act(async () => {
      resolveOld!(makeTask({ id: "entry-1" }));
      await new Promise((r) => setTimeout(r, 0));
    });

    // 状态不受旧请求影响
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.entry?.id).toBe("entry-2");
  });
});
