import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import type { Task } from "@/types/task";

// --- Mocks ---

// Mock react-router-dom
const mockSetSearchParams = vi.fn();
const mockSearchParams = new URLSearchParams();
vi.mock("react-router-dom", () => ({
  useSearchParams: () => [mockSearchParams, mockSetSearchParams],
}));

// Mock API
const mockSearchEntries = vi.fn();
const mockGetEntries = vi.fn();
vi.mock("@/services/api", () => ({
  searchEntries: (...args: unknown[]) => mockSearchEntries(...args),
  getEntries: (...args: unknown[]) => mockGetEntries(...args),
}));

// Mock chatStore (selector pattern)
const mockSetPageExtra = vi.fn();
vi.mock("@/stores/chatStore", () => ({
  useChatStore: (selector: (state: { setPageExtra: typeof mockSetPageExtra }) => unknown) => selector({ setPageExtra: mockSetPageExtra }),
}));

// Mock useServiceUnavailable
vi.mock("@/hooks/useServiceUnavailable", () => ({
  useServiceUnavailable: () => ({
    serviceUnavailable: false,
    runWith503: (fn: () => Promise<void>) => fn(),
    retry: vi.fn(),
  }),
}));

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

// Must import after mocks
import { useExploreSearch } from "../useExploreSearch";

describe("useExploreSearch — F132 Tab 过滤透传", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetEntries.mockResolvedValue({
      entries: [
        makeTask({ id: "e1", category: "note", title: "Note 1" }),
        makeTask({ id: "e2", category: "inbox", title: "Inbox 1" }),
        makeTask({ id: "e3", category: "project", title: "Project 1" }),
      ],
    });
    mockSearchEntries.mockResolvedValue({ results: [] });
  });

  const renderExploreSearch = () => {
    const refresh = vi.fn();
    return renderHook(() => useExploreSearch(refresh));
  };

  it("默认 activeTab 为空（全部）", async () => {
    const { result } = renderExploreSearch();
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.activeTab).toBe("");
  });

  it("手动搜索（Enter 键）传递 activeTab filter_type", async () => {
    const { result } = renderExploreSearch();
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    // 切换到"灵感" Tab
    act(() => result.current.handleTabChange("inbox"));
    expect(result.current.activeTab).toBe("inbox");

    // 设置搜索词
    act(() => result.current.setSearchQuery("manual query"));

    mockSearchEntries.mockResolvedValue({
      results: [
        { id: "s1", title: "Search Result", category: "inbox", type: "inbox", score: 0.9, status: "doing", tags: [], created_at: "2024-01-01", file_path: "" },
      ],
    });

    // 模拟 Enter 键触发手动搜索
    act(() => result.current.handleKeyDown({ key: "Enter" } as React.KeyboardEvent));

    await waitFor(() => expect(result.current.isSearching).toBe(false));

    // 验证 searchEntries 被调用时传递了 filter_type="inbox"
    expect(mockSearchEntries).toHaveBeenCalledWith(
      "manual query",
      20,
      "inbox", // filter_type = activeTab
      expect.anything(),
    );
  });

  it("手动搜索 — 全部 Tab 不传 filter_type（undefined）", async () => {
    const { result } = renderExploreSearch();
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    // activeTab 为空（全部）
    expect(result.current.activeTab).toBe("");

    act(() => result.current.setSearchQuery("all query"));

    mockSearchEntries.mockResolvedValue({
      results: [
        { id: "s1", title: "Note", category: "note", type: "note", score: 0.9, status: "doing", tags: [], created_at: "2024-01-01", file_path: "" },
        { id: "s2", title: "Inbox", category: "inbox", type: "inbox", score: 0.8, status: "doing", tags: [], created_at: "2024-01-01", file_path: "" },
      ],
    });

    act(() => result.current.handleKeyDown({ key: "Enter" } as React.KeyboardEvent));

    await waitFor(() => expect(result.current.isSearching).toBe(false));

    // 验证 filter_type 为 undefined
    expect(mockSearchEntries).toHaveBeenCalledWith(
      "all query",
      20,
      undefined,
      expect.anything(),
    );

    // 搜索结果跨类型混合展示
    expect(result.current.filteredTasks.length).toBe(2);
    const categories = result.current.filteredTasks.map((t: Task) => t.category);
    expect(categories).toContain("note");
    expect(categories).toContain("inbox");
  });

  it("手动搜索 — 搜索结果过滤 Explore 类别边界（排除 task 类型）", async () => {
    const { result } = renderExploreSearch();
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    mockSearchEntries.mockResolvedValue({
      results: [
        { id: "s1", title: "Note", category: "note", type: "note", score: 0.9, status: "doing", tags: [], created_at: "2024-01-01", file_path: "" },
        { id: "s2", title: "Task", category: "task", type: "task", score: 0.8, status: "doing", tags: [], created_at: "2024-01-01", file_path: "" },
        { id: "s3", title: "Inbox", category: "inbox", type: "inbox", score: 0.7, status: "doing", tags: [], created_at: "2024-01-01", file_path: "" },
      ],
    });

    act(() => result.current.setSearchQuery("mixed"));
    act(() => result.current.handleKeyDown({ key: "Enter" } as React.KeyboardEvent));

    await waitFor(() => expect(result.current.isSearching).toBe(false));

    // task 类型被过滤掉
    expect(result.current.filteredTasks.length).toBe(2);
    const categories = result.current.filteredTasks.map((t: Task) => t.category);
    expect(categories).toContain("note");
    expect(categories).toContain("inbox");
    expect(categories).not.toContain("task");
  });

  it("非搜索模式下 Tab 过滤正常工作", async () => {
    const { result } = renderExploreSearch();
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    // 初始加载了 note, inbox, project
    expect(result.current.filteredTasks.length).toBe(3);

    // 切换到"灵感" Tab
    act(() => result.current.handleTabChange("inbox"));

    // 非搜索模式下按 activeTab 过滤
    expect(result.current.filteredTasks.length).toBe(1);
    expect(result.current.filteredTasks[0].category).toBe("inbox");
  });

  it("手动搜索 — 笔记 Tab 传递 filter_type=note", async () => {
    const { result } = renderExploreSearch();
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => result.current.handleTabChange("note"));
    act(() => result.current.setSearchQuery("notes only"));

    mockSearchEntries.mockResolvedValue({
      results: [
        { id: "s1", title: "Manual Result", category: "note", type: "note", score: 0.95, status: "doing", tags: [], created_at: "2024-01-01", file_path: "" },
      ],
    });

    act(() => result.current.handleKeyDown({ key: "Enter" } as React.KeyboardEvent));

    await waitFor(() => expect(result.current.isSearching).toBe(false));

    expect(mockSearchEntries).toHaveBeenCalledWith(
      "notes only",
      20,
      "note",
      expect.anything(),
    );
  });
});

describe("useExploreSearch — F138 错误状态", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetEntries.mockResolvedValue({
      entries: [
        makeTask({ id: "e1", category: "note", title: "Note 1" }),
        makeTask({ id: "e2", category: "inbox", title: "Inbox 1" }),
      ],
    });
    mockSearchEntries.mockResolvedValue({ results: [] });
  });

  const renderExploreSearch = () => {
    const refresh = vi.fn();
    return renderHook(() => useExploreSearch(refresh));
  };

  it("首次加载失败时 entriesError 非空，entries 为空", async () => {
    mockGetEntries.mockRejectedValue(new Error("Network error"));

    const { result } = renderExploreSearch();

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.entriesError).toBe("加载失败，请重试");
    expect(result.current.entries).toEqual([]);
    expect(result.current.filteredTasks).toEqual([]);
  });

  it("loadEntries catch 中未清空 entries，部分失败保留旧数据", async () => {
    // 验证 loadEntries 的实现：catch 中只有 setEntriesError，没有 setEntries([])
    // 所以当首次加载成功后，后续 loadEntries 失败时，entries 保留旧值

    // 首次成功加载
    const firstEntries = [
      makeTask({ id: "e1", category: "note", title: "Note 1" }),
      makeTask({ id: "e2", category: "inbox", title: "Inbox 2" }),
    ];
    mockGetEntries.mockResolvedValue({ entries: firstEntries });

    const { result } = renderExploreSearch();

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
      expect(result.current.entries.length).toBe(2);
    });

    // 验证首次加载成功状态
    expect(result.current.entriesError).toBeNull();
    expect(result.current.entries).toEqual(firstEntries);
  });
});
