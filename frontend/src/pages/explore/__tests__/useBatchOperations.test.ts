import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import type { Task } from "@/types/task";

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
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
  });

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

  it("handleBatchDelete 成功删除并退出多选", async () => {
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
  });

  it("handleBatchDelete 用户取消时不执行删除", async () => {
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

  it("handleBatchDelete 部分失败时显示错误", async () => {
    mockDeleteTask.mockImplementation(async (id: string) => {
      if (id === "id2") {
        mockGetState.mockReturnValue({ error: "fail" });
      } else {
        mockGetState.mockReturnValue({ error: null });
      }
    });

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

    // id2 失败，不清退多选模式
    expect(result.current.selectMode).toBe(true);
  });

  it("handleBatchCategory 成功转分类", async () => {
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
  });

  it("handleBatchCategory 部分失败时显示错误", async () => {
    mockUpdateEntry.mockImplementation(async (id: string) => {
      if (id === "id2") {
        mockGetState.mockReturnValue({ error: "fail" });
      } else {
        mockGetState.mockReturnValue({ error: null });
      }
    });

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
      await result.current.handleBatchCategory("inbox");
    });

    expect(result.current.selectMode).toBe(true);
  });

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

    // After operation completes, batchLoading returns to false
    expect(result.current.batchLoading).toBe(false);
    expect(result.current.selectMode).toBe(false);
  });
});
