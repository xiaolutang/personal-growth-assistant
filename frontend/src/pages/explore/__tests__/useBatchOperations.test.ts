import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import type { Task } from "@/types/task";

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

// Mock offlineSync subscribeSyncProgress
const { mockSubscribeSyncProgress } = vi.hoisted(() => {
  return {
    mockSubscribeSyncProgress: vi.fn<(cb: (event: any) => void) => () => void>(() => vi.fn()),
  };
});

vi.mock("@/lib/offlineSync", () => ({
  subscribeSyncProgress: mockSubscribeSyncProgress,
}));

// Mock taskStore - use hoisted variables
const { mockDeleteTask, mockUpdateEntry, mockGetState, mockSetState } = vi.hoisted(() => {
  return {
    mockDeleteTask: vi.fn(),
    mockUpdateEntry: vi.fn(),
    mockGetState: vi.fn<() => { error: string | null }>(() => ({ error: null })),
    mockSetState: vi.fn(),
  };
});

vi.mock("@/stores/taskStore", () => ({
  useTaskStore: Object.assign(
    (selector: (s: any) => any) => selector({
      deleteTask: mockDeleteTask,
      updateEntry: mockUpdateEntry,
    }),
    {
      getState: mockGetState,
      setState: mockSetState,
    }
  ),
}));

// Mock window.confirm
const mockConfirm = vi.fn(() => true);
Object.defineProperty(window, "confirm", { value: mockConfirm, writable: true });

// navigator.onLine mock
const originalOnLine = Object.getOwnPropertyDescriptor(navigator, "onLine");

import { useBatchOperations } from "../useBatchOperations";

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

describe("useBatchOperations", () => {
  let setEntries: any;
  let setSearchResults: any;

  beforeEach(() => {
    vi.clearAllMocks();
    setEntries = vi.fn();
    setSearchResults = vi.fn();
    mockConfirm.mockReturnValue(true);
    mockDeleteTask.mockResolvedValue(undefined);
    mockUpdateEntry.mockResolvedValue(undefined);
    mockGetState.mockReturnValue({ error: null });
    // Default to online
    Object.defineProperty(navigator, "onLine", { value: true, configurable: true });
  });

  afterEach(() => {
    // Restore navigator.onLine
    if (originalOnLine) {
      Object.defineProperty(navigator, "onLine", originalOnLine);
    }
  });

  // ─── 基础操作 ───────────────────────────────────────

  it("enterSelectMode 进入多选模式", () => {
    const { result } = renderHook(() =>
      useBatchOperations({
        filteredTasks: [],
        setEntries,
        setSearchResults,
      })
    );
    expect(result.current.selectMode).toBe(false);
    act(() => result.current.enterSelectMode());
    expect(result.current.selectMode).toBe(true);
    expect(result.current.selectedIds.size).toBe(0);
  });

  it("exitSelectMode 退出多选模式并清空选中", () => {
    const { result } = renderHook(() =>
      useBatchOperations({
        filteredTasks: [],
        setEntries,
        setSearchResults,
      })
    );
    act(() => {
      result.current.enterSelectMode();
      result.current.toggleSelect("id1");
    });
    expect(result.current.selectedIds.size).toBe(1);

    act(() => result.current.exitSelectMode());
    expect(result.current.selectMode).toBe(false);
    expect(result.current.selectedIds.size).toBe(0);
  });

  it("toggleSelect 切换选中状态", () => {
    const { result } = renderHook(() =>
      useBatchOperations({
        filteredTasks: [],
        setEntries,
        setSearchResults,
      })
    );
    act(() => result.current.toggleSelect("id1"));
    expect(result.current.selectedIds.has("id1")).toBe(true);

    act(() => result.current.toggleSelect("id1"));
    expect(result.current.selectedIds.has("id1")).toBe(false);
  });

  it("selectAll 选中所有 filteredTasks", () => {
    const tasks = [makeTask({ id: "a" }), makeTask({ id: "b" }), makeTask({ id: "c" })];
    const { result } = renderHook(() =>
      useBatchOperations({
        filteredTasks: tasks,
        setEntries,
        setSearchResults,
      })
    );
    act(() => result.current.selectAll());
    expect(result.current.selectedIds.size).toBe(3);
    expect(result.current.selectedIds.has("a")).toBe(true);
    expect(result.current.selectedIds.has("b")).toBe(true);
    expect(result.current.selectedIds.has("c")).toBe(true);
  });

  it("ESC 键退出多选模式并清空选中", () => {
    const { result } = renderHook(() =>
      useBatchOperations({
        filteredTasks: [],
        setEntries,
        setSearchResults,
      })
    );
    act(() => {
      result.current.enterSelectMode();
      result.current.toggleSelect("id1");
      result.current.toggleSelect("id2");
    });
    expect(result.current.selectMode).toBe(true);
    expect(result.current.selectedIds.size).toBe(2);

    act(() => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    });
    expect(result.current.selectMode).toBe(false);
    expect(result.current.selectedIds.size).toBe(0);
  });

  it("ESC 不在多选模式时无效", () => {
    const { result } = renderHook(() =>
      useBatchOperations({
        filteredTasks: [],
        setEntries,
        setSearchResults,
      })
    );
    expect(result.current.selectMode).toBe(false);

    act(() => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    });
    expect(result.current.selectMode).toBe(false);
  });

  // ─── 在线批量删除 ───────────────────────────────────

  it("在线批量删除：成功后列表本地更新并退出多选", async () => {
    const { result } = renderHook(() =>
      useBatchOperations({
        filteredTasks: [],
        setEntries,
        setSearchResults,
      })
    );
    act(() => {
      result.current.enterSelectMode();
      result.current.toggleSelect("id1");
      result.current.toggleSelect("id2");
    });

    await act(async () => {
      await result.current.handleBatchDelete();
    });

    expect(mockDeleteTask).toHaveBeenCalledTimes(2);
    expect(setEntries).toHaveBeenCalled();
    expect(result.current.selectMode).toBe(false);
    expect(result.current.failedItems.length).toBe(0);
  });

  it("在线批量删除：用户取消时不执行删除", async () => {
    mockConfirm.mockReturnValue(false);
    const { result } = renderHook(() =>
      useBatchOperations({
        filteredTasks: [],
        setEntries,
        setSearchResults,
      })
    );
    act(() => {
      result.current.enterSelectMode();
      result.current.toggleSelect("id1");
    });

    await act(async () => {
      await result.current.handleBatchDelete();
    });

    expect(mockDeleteTask).not.toHaveBeenCalled();
  });

  it("在线批量删除：部分失败时展示失败条目提示，保持多选", async () => {
    const tasks = [makeTask({ id: "id1", title: "条目A" }), makeTask({ id: "id2", title: "条目B" })];
    mockDeleteTask.mockImplementation(async (id: string) => {
      if (id === "id2") {
        mockGetState.mockReturnValue({ error: "fail" });
      } else {
        mockGetState.mockReturnValue({ error: null });
      }
    });

    const { result } = renderHook(() =>
      useBatchOperations({
        filteredTasks: tasks,
        setEntries,
        setSearchResults,
      })
    );
    act(() => {
      result.current.enterSelectMode();
      result.current.toggleSelect("id1");
      result.current.toggleSelect("id2");
    });

    await act(async () => {
      await result.current.handleBatchDelete();
    });

    // 部分失败：保持多选模式
    expect(result.current.selectMode).toBe(true);
    // 失败条目包含失败的具体信息
    expect(result.current.failedItems.length).toBe(1);
    expect(result.current.failedItems[0].id).toBe("id2");
    expect(result.current.failedItems[0].title).toBe("条目B");
  });

  it("在线批量删除：全量成功后自动退出多选模式", async () => {
    const { result } = renderHook(() =>
      useBatchOperations({
        filteredTasks: [],
        setEntries,
        setSearchResults,
      })
    );
    act(() => {
      result.current.enterSelectMode();
      result.current.toggleSelect("id1");
    });

    await act(async () => {
      await result.current.handleBatchDelete();
    });

    expect(result.current.selectMode).toBe(false);
    expect(result.current.failedItems.length).toBe(0);
  });

  // ─── 在线批量转分类 ─────────────────────────────────

  it("在线批量转分类：成功后列表本地刷新并退出多选", async () => {
    const { result } = renderHook(() =>
      useBatchOperations({
        filteredTasks: [],
        setEntries,
        setSearchResults,
      })
    );
    act(() => {
      result.current.enterSelectMode();
      result.current.toggleSelect("id1");
    });

    await act(async () => {
      await result.current.handleBatchCategory("note");
    });

    expect(mockUpdateEntry).toHaveBeenCalledWith("id1", { category: "note" });
    expect(setEntries).toHaveBeenCalled();
    expect(result.current.selectMode).toBe(false);
    expect(result.current.failedItems.length).toBe(0);
  });

  it("在线批量转分类：部分失败时展示失败条目提示", async () => {
    const tasks = [makeTask({ id: "id1", title: "笔记A" }), makeTask({ id: "id2", title: "笔记B" })];
    mockUpdateEntry.mockImplementation(async (id: string) => {
      if (id === "id2") {
        mockGetState.mockReturnValue({ error: "fail" });
      } else {
        mockGetState.mockReturnValue({ error: null });
      }
    });

    const { result } = renderHook(() =>
      useBatchOperations({
        filteredTasks: tasks,
        setEntries,
        setSearchResults,
      })
    );
    act(() => {
      result.current.enterSelectMode();
      result.current.toggleSelect("id1");
      result.current.toggleSelect("id2");
    });

    await act(async () => {
      await result.current.handleBatchCategory("inbox");
    });

    expect(result.current.selectMode).toBe(true);
    expect(result.current.failedItems.length).toBe(1);
    expect(result.current.failedItems[0].title).toBe("笔记B");
  });

  it("在线批量转分类：全量成功后自动退出多选模式", async () => {
    const { result } = renderHook(() =>
      useBatchOperations({
        filteredTasks: [],
        setEntries,
        setSearchResults,
      })
    );
    act(() => {
      result.current.enterSelectMode();
      result.current.toggleSelect("id1");
      result.current.toggleSelect("id2");
    });

    await act(async () => {
      await result.current.handleBatchCategory("task");
    });

    expect(result.current.selectMode).toBe(false);
  });

  // ─── 离线批量操作入 offlineSync 队列 ────────────────

  it("离线批量删除：操作入队后退出多选，显示离线 toast 提示", async () => {
    const { toast } = await import("sonner");
    Object.defineProperty(navigator, "onLine", { value: false, configurable: true });

    const { result } = renderHook(() =>
      useBatchOperations({
        filteredTasks: [],
        setEntries,
        setSearchResults,
      })
    );
    act(() => {
      result.current.enterSelectMode();
      result.current.toggleSelect("id1");
      result.current.toggleSelect("id2");
    });

    await act(async () => {
      await result.current.handleBatchDelete();
    });

    // 离线模式下 deleteTask 仍被调用（底层 taskStore 会处理入队）
    expect(mockDeleteTask).toHaveBeenCalledTimes(2);
    // 全量成功后退出多选（因为底层已处理入队）
    expect(result.current.selectMode).toBe(false);
    // 离线成功提示包含"离线"关键字
    expect(toast.success).toHaveBeenCalledWith(
      expect.stringContaining("离线")
    );
  });

  it("离线批量转分类：操作入队后退出多选，显示离线 toast 提示", async () => {
    const { toast } = await import("sonner");
    Object.defineProperty(navigator, "onLine", { value: false, configurable: true });

    const { result } = renderHook(() =>
      useBatchOperations({
        filteredTasks: [],
        setEntries,
        setSearchResults,
      })
    );
    act(() => {
      result.current.enterSelectMode();
      result.current.toggleSelect("id1");
    });

    await act(async () => {
      await result.current.handleBatchCategory("task");
    });

    expect(mockUpdateEntry).toHaveBeenCalledWith("id1", { category: "task" });
    expect(result.current.selectMode).toBe(false);
    expect(toast.success).toHaveBeenCalledWith(
      expect.stringContaining("离线")
    );
  });

  it("离线批量删除：部分失败时保持多选并展示失败条目", async () => {
    Object.defineProperty(navigator, "onLine", { value: false, configurable: true });
    const tasks = [makeTask({ id: "id1", title: "条目A" }), makeTask({ id: "id2", title: "条目B" })];
    mockDeleteTask.mockImplementation(async (id: string) => {
      if (id === "id2") {
        mockGetState.mockReturnValue({ error: "fail" });
      } else {
        mockGetState.mockReturnValue({ error: null });
      }
    });

    const { result } = renderHook(() =>
      useBatchOperations({
        filteredTasks: tasks,
        setEntries,
        setSearchResults,
      })
    );
    act(() => {
      result.current.enterSelectMode();
      result.current.toggleSelect("id1");
      result.current.toggleSelect("id2");
    });

    await act(async () => {
      await result.current.handleBatchDelete();
    });

    expect(result.current.offlineMode).toBe(true);
    expect(result.current.selectMode).toBe(true);
    expect(result.current.failedItems.length).toBe(1);
    expect(result.current.failedItems[0].id).toBe("id2");
  });

  // ─── 联网后队列回放成功后刷新列表并退出多选 ──────────

  it("联网后：同步完成事件触发 onSyncCompleted 回调刷新列表", async () => {
    let syncCallback: ((event: any) => void) | null = null;
    mockSubscribeSyncProgress.mockImplementation((cb: (event: any) => void) => {
      syncCallback = cb;
      return vi.fn();
    });

    const onSyncCompleted = vi.fn();

    // 先在离线模式下执行批量操作
    Object.defineProperty(navigator, "onLine", { value: false, configurable: true });

    const { result } = renderHook(() =>
      useBatchOperations({
        filteredTasks: [],
        setEntries,
        setSearchResults,
        onSyncCompleted,
      })
    );
    act(() => {
      result.current.enterSelectMode();
      result.current.toggleSelect("id1");
    });

    await act(async () => {
      await result.current.handleBatchDelete();
    });

    // 操作完成，已退出多选（因为底层成功入队）
    expect(result.current.selectMode).toBe(false);

    // 模拟联网后同步完成事件
    Object.defineProperty(navigator, "onLine", { value: true, configurable: true });

    // 再次进入多选模式以触发 subscribeSyncProgress 订阅
    act(() => {
      result.current.enterSelectMode();
    });

    // 触发同步完成事件
    act(() => {
      syncCallback?.({ type: "completed" });
    });

    // onSyncCompleted 应该被调用（刷新列表）
    expect(onSyncCompleted).toHaveBeenCalled();
    // 同步完成后应自动退出多选
    expect(result.current.selectMode).toBe(false);
  });

  // ─── clearFailedItems 清除失败提示 ──────────────────

  it("clearFailedItems 清除失败条目列表", async () => {
    const tasks = [makeTask({ id: "id1", title: "A" }), makeTask({ id: "id2", title: "B" })];
    mockDeleteTask.mockImplementation(async (id: string) => {
      if (id === "id2") {
        mockGetState.mockReturnValue({ error: "fail" });
      } else {
        mockGetState.mockReturnValue({ error: null });
      }
    });

    const { result } = renderHook(() =>
      useBatchOperations({
        filteredTasks: tasks,
        setEntries,
        setSearchResults,
      })
    );
    act(() => {
      result.current.enterSelectMode();
      result.current.toggleSelect("id1");
      result.current.toggleSelect("id2");
    });

    await act(async () => {
      await result.current.handleBatchDelete();
    });

    expect(result.current.failedItems.length).toBe(1);

    act(() => {
      result.current.clearFailedItems();
    });

    expect(result.current.failedItems.length).toBe(0);
  });

  // ─── batchLoading 状态 ──────────────────────────────

  it("batchLoading 操作结束后恢复 false", async () => {
    mockDeleteTask.mockResolvedValue(undefined);
    const { result } = renderHook(() =>
      useBatchOperations({
        filteredTasks: [],
        setEntries,
        setSearchResults,
      })
    );
    act(() => {
      result.current.enterSelectMode();
      result.current.toggleSelect("id1");
    });

    await act(async () => {
      await result.current.handleBatchDelete();
    });

    expect(result.current.batchLoading).toBe(false);
    expect(result.current.selectMode).toBe(false);
  });
});
