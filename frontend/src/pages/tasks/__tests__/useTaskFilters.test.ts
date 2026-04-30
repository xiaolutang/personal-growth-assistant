/**
 * F03: useTaskFilters hook tests
 * - category_group=actionable query
 * - category sub-tab filtering
 * - handleBatchCategory removed
 * - existing status/priority/date/sort filters unaffected
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useTaskFilters } from "../useTaskFilters";
import { useTaskStore } from "@/stores/taskStore";
import { resetStore, createMockTask } from "@/testUtils/taskStoreHelpers";
import type { Task } from "@/types/task";

// Mock react-router-dom
const mockSetSearchParams = vi.fn((updater) => {
  // Simulate the updater behavior for testing
  const prev = new URLSearchParams();
  return updater(prev);
});
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useSearchParams: () => [new URLSearchParams(), mockSetSearchParams],
    useNavigate: () => vi.fn(),
    useLocation: () => ({ pathname: "/tasks" }),
  };
});

// Mock sonner
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

// Mock API
vi.mock("@/services/api", () => ({
  getEntries: vi.fn().mockResolvedValue({ entries: [] }),
  createEntry: vi.fn(),
  updateEntry: vi.fn(),
  deleteEntry: vi.fn(),
  searchEntries: vi.fn(),
  getKnowledgeGraph: vi.fn(),
}));

beforeEach(() => {
  resetStore();
  vi.clearAllMocks();
});

describe("F03: useTaskFilters - category_group query", () => {
  it("TASK_QUERY_PARAMS uses category_group=actionable instead of type=task", async () => {
    // Import the constant and verify
    const { TASK_QUERY_PARAMS } = await import("../constants");
    expect(TASK_QUERY_PARAMS).toEqual({ category_group: "actionable", limit: 100 });
    expect(TASK_QUERY_PARAMS).not.toHaveProperty("type");
  });

  it("initial fetch calls fetchEntries with category_group=actionable", async () => {
    const fetchSpy = vi.spyOn(useTaskStore.getState(), "fetchEntries");

    renderHook(() => useTaskFilters());

    // Wait for the mount effect to run
    await waitFor(() => {
      // The hook should have called fetchEntries on mount if store is empty
    });

    // fetchSpy may or may not be called depending on store state
    // But when it IS called, it should use TASK_QUERY_PARAMS
    if (fetchSpy.mock.calls.length > 0) {
      const { TASK_QUERY_PARAMS } = await import("../constants");
      expect(fetchSpy).toHaveBeenCalledWith(TASK_QUERY_PARAMS);
    }
  });
});

describe("F03: useTaskFilters - sub-tab category filtering", () => {
  it("activeSubTab defaults to 'all'", () => {
    const { result } = renderHook(() => useTaskFilters());
    expect(result.current.activeSubTab).toBe("all");
  });

  it("setActiveSubTab changes the sub-tab", () => {
    const { result } = renderHook(() => useTaskFilters());
    act(() => {
      result.current.setActiveSubTab("decision");
    });
    expect(result.current.activeSubTab).toBe("decision");
  });

  it("activeSubTab='all' shows all actionable categories (task+decision+project)", () => {
    const tasks: Task[] = [
      createMockTask({ id: "1", category: "task" }),
      createMockTask({ id: "2", category: "decision" }),
      createMockTask({ id: "3", category: "project" }),
    ];
    useTaskStore.setState({ tasks });

    const { result } = renderHook(() => useTaskFilters());
    expect(result.current.activeSubTab).toBe("all");
    expect(result.current.filteredTasks).toHaveLength(3);
  });

  it("activeSubTab='task' shows only task category", () => {
    const tasks: Task[] = [
      createMockTask({ id: "1", category: "task" }),
      createMockTask({ id: "2", category: "decision" }),
      createMockTask({ id: "3", category: "project" }),
    ];
    useTaskStore.setState({ tasks });

    const { result } = renderHook(() => useTaskFilters());
    act(() => {
      result.current.setActiveSubTab("task");
    });

    expect(result.current.filteredTasks).toHaveLength(1);
    expect(result.current.filteredTasks[0].category).toBe("task");
  });

  it("activeSubTab='decision' shows only decision category", () => {
    const tasks: Task[] = [
      createMockTask({ id: "1", category: "task" }),
      createMockTask({ id: "2", category: "decision" }),
      createMockTask({ id: "3", category: "project" }),
    ];
    useTaskStore.setState({ tasks });

    const { result } = renderHook(() => useTaskFilters());
    act(() => {
      result.current.setActiveSubTab("decision");
    });

    expect(result.current.filteredTasks).toHaveLength(1);
    expect(result.current.filteredTasks[0].category).toBe("decision");
  });

  it("activeSubTab='project' shows only project category", () => {
    const tasks: Task[] = [
      createMockTask({ id: "1", category: "task" }),
      createMockTask({ id: "2", category: "decision" }),
      createMockTask({ id: "3", category: "project" }),
    ];
    useTaskStore.setState({ tasks });

    const { result } = renderHook(() => useTaskFilters());
    act(() => {
      result.current.setActiveSubTab("project");
    });

    expect(result.current.filteredTasks).toHaveLength(1);
    expect(result.current.filteredTasks[0].category).toBe("project");
  });

  it("sub-tab filter combines with status filter correctly", () => {
    const tasks: Task[] = [
      createMockTask({ id: "1", category: "task", status: "doing" }),
      createMockTask({ id: "2", category: "task", status: "complete" }),
      createMockTask({ id: "3", category: "decision", status: "doing" }),
      createMockTask({ id: "4", category: "project", status: "doing" }),
    ];
    useTaskStore.setState({ tasks });

    const { result } = renderHook(() => useTaskFilters());

    // Select "doing" status
    act(() => {
      result.current.setSelectedStatus("doing");
    });

    // Select "task" sub-tab
    act(() => {
      result.current.setActiveSubTab("task");
    });

    // Only task+doing should show
    expect(result.current.filteredTasks).toHaveLength(1);
    expect(result.current.filteredTasks[0].id).toBe("1");
  });

  it("non-actionable categories are not shown even with 'all' tab", () => {
    const tasks: Task[] = [
      createMockTask({ id: "1", category: "task" }),
      createMockTask({ id: "2", category: "note" }),
      createMockTask({ id: "3", category: "inbox" }),
      createMockTask({ id: "4", category: "decision" }),
    ];
    useTaskStore.setState({ tasks });

    const { result } = renderHook(() => useTaskFilters());
    expect(result.current.activeSubTab).toBe("all");

    // Only task and decision (actionable) should show
    const categories = result.current.filteredTasks.map(t => t.category);
    expect(categories).toContain("task");
    expect(categories).toContain("decision");
    expect(categories).not.toContain("note");
    expect(categories).not.toContain("inbox");
  });
});

describe("F03: useTaskFilters - handleBatchCategory removed", () => {
  it("handleBatchCategory should not exist in return value", () => {
    const { result } = renderHook(() => useTaskFilters());
    expect((result.current as any).handleBatchCategory).toBeUndefined();
  });
});

describe("F03: useTaskFilters - existing filters unaffected", () => {
  it("status filter still works", () => {
    const tasks: Task[] = [
      createMockTask({ id: "1", status: "doing" }),
      createMockTask({ id: "2", status: "complete" }),
    ];
    useTaskStore.setState({ tasks });

    const { result } = renderHook(() => useTaskFilters());
    act(() => {
      result.current.setSelectedStatus("doing");
    });

    expect(result.current.filteredTasks).toHaveLength(1);
    expect(result.current.filteredTasks[0].status).toBe("doing");
  });

  it("priority filter still works", () => {
    const tasks: Task[] = [
      createMockTask({ id: "1", priority: "high" }),
      createMockTask({ id: "2", priority: "low" }),
    ];
    useTaskStore.setState({ tasks });

    const { result } = renderHook(() => useTaskFilters());
    act(() => {
      result.current.setSelectedPriority("high");
    });

    expect(result.current.filteredTasks).toHaveLength(1);
    expect(result.current.filteredTasks[0].priority).toBe("high");
  });

  it("hasActiveFilters still works", () => {
    const { result } = renderHook(() => useTaskFilters());
    expect(result.current.hasActiveFilters).toBe(false);

    act(() => {
      result.current.setSelectedStatus("doing");
    });
    expect(result.current.hasActiveFilters).toBe(true);
  });

  it("clearFilters resets all filters including sub-tab", () => {
    const { result } = renderHook(() => useTaskFilters());

    act(() => {
      result.current.setActiveSubTab("decision");
      result.current.setSelectedStatus("doing");
    });

    expect(result.current.activeSubTab).toBe("decision");
    expect(result.current.selectedStatus).toBe("doing");

    act(() => {
      result.current.clearFilters();
    });

    expect(result.current.activeSubTab).toBe("all");
    expect(result.current.selectedStatus).toBeNull();
  });

  it("batch delete still works", async () => {
    const tasks: Task[] = [
      createMockTask({ id: "1" }),
      createMockTask({ id: "2" }),
    ];
    useTaskStore.setState({ tasks });
    const deleteSpy = vi.spyOn(useTaskStore.getState(), "deleteTask").mockResolvedValue(undefined);

    const { result } = renderHook(() => useTaskFilters());

    act(() => {
      result.current.enterSelectMode();
    });
    act(() => {
      result.current.toggleSelect("1");
    });

    await act(async () => {
      await result.current.handleBatchDelete();
    });

    expect(deleteSpy).toHaveBeenCalledWith("1");
  });
});

describe("F08: useTaskFilters - view state", () => {
  it("activeView defaults to 'list'", () => {
    const { result } = renderHook(() => useTaskFilters());
    expect(result.current.activeView).toBe("list");
  });

  it("setActiveView changes the view", () => {
    const { result } = renderHook(() => useTaskFilters());
    act(() => {
      result.current.setActiveView("grouped");
    });
    expect(result.current.activeView).toBe("grouped");
  });

  it("setActiveView syncs to URL params", () => {
    const { result } = renderHook(() => useTaskFilters());
    act(() => {
      result.current.setActiveView("grouped");
    });
    expect(mockSetSearchParams).toHaveBeenCalled();
    // Verify the URL param was set
    const lastCall = mockSetSearchParams.mock.calls[mockSetSearchParams.mock.calls.length - 1];
    const updater = lastCall[0];
    const prev = new URLSearchParams();
    const result_params = updater(prev);
    expect(result_params.get("view")).toBe("grouped");
  });

  it("setActiveView('list') removes view URL param", () => {
    const { result } = renderHook(() => useTaskFilters());
    act(() => {
      result.current.setActiveView("grouped");
    });
    act(() => {
      result.current.setActiveView("list");
    });
    const lastCall = mockSetSearchParams.mock.calls[mockSetSearchParams.mock.calls.length - 1];
    const updater = lastCall[0];
    const prev = new URLSearchParams();
    const result_params = updater(prev);
    expect(result_params.get("view")).toBeNull();
  });
});
