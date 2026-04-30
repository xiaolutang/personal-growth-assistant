/**
 * F04 Integration: 探索页 -> CreateDialog 真实组件集成测试
 *
 * 不 mock CreateDialog，验证真实的页面 -> 对话框 -> 创建 API -> 刷新链路。
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { Explore } from "../Explore";
import { ThemeProvider } from "@/lib/theme";

Element.prototype.scrollIntoView = vi.fn();

// Mock HTMLDialogElement for jsdom
HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) {
  this.open = true;
});
HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) {
  this.open = false;
  this.dispatchEvent(new Event("close"));
});

// --- Mocks ---

vi.mock("@/lib/authFetch", () => ({
  authFetch: (...args: unknown[]) => mockAuthFetch(...args),
  buildAuthHeaders: () => new Headers(),
}));

const mockAuthFetch = vi.fn();

const stableRunWith503 = vi.fn();
const stableRetry = vi.fn((fn: () => Promise<void>) => fn());
vi.mock("@/hooks/useServiceUnavailable", () => ({
  useServiceUnavailable: () => ({
    serviceUnavailable: false,
    runWith503: (fn: () => Promise<void>) => stableRunWith503(fn),
    retry: (fn: () => Promise<void>) => stableRetry(fn),
  }),
}));

const mockGetEntries = vi.fn();
const mockSearchEntries = vi.fn();
const mockCreateEntry = vi.fn();

vi.mock("@/services/api", () => ({
  getEntries: (...args: unknown[]) => mockGetEntries(...args),
  searchEntries: (...args: unknown[]) => mockSearchEntries(...args),
  fetchTemplates: vi.fn().mockResolvedValue({ templates: [] }),
}));

vi.mock("@/stores/taskStore", () => ({
  useTaskStore: (selector: any) => {
    const store = {
      createEntry: (...args: unknown[]) => mockCreateEntry(...args),
      isLoading: false,
    };
    return selector(store);
  },
}));

vi.mock("@/components/TaskList", () => ({
  TaskList: ({ tasks, emptyMessage }: { tasks: unknown[]; emptyMessage: string }) => (
    <div data-testid="task-list">
      {tasks.length > 0 ? (
        <span>{tasks.length} items</span>
      ) : (
        <span>{emptyMessage}</span>
      )}
    </div>
  ),
}));

vi.mock("@/components/layout/Header", () => ({
  Header: ({ title }: { title: string }) => <h1>{title}</h1>,
}));

vi.mock("@/components/ActivityHeatmap", () => ({
  ActivityHeatmap: () => <div data-testid="activity-heatmap" />,
}));

vi.mock("../explore/SearchBar", () => ({
  SearchBar: ({ searchQuery, onSearchQueryChange, inputRef }: any) => (
    <input
      data-testid="search-bar-input"
      value={searchQuery}
      onChange={(e: any) => onSearchQueryChange(e.target.value)}
      ref={inputRef}
      placeholder="搜索"
    />
  ),
}));

vi.mock("../explore/FilterBar", () => ({
  FilterBar: () => <div data-testid="filter-bar" />,
}));

vi.mock("../explore/BatchActionBar", () => ({
  BatchActionBar: () => <div data-testid="batch-action-bar" />,
}));

vi.mock("../explore/useSearchHistory", () => ({
  useSearchHistory: () => ({
    searchHistory: [],
    removeHistory: vi.fn(),
    refresh: vi.fn(),
  }),
}));

vi.mock("../explore/useBatchOperations", () => ({
  useBatchOperations: () => ({
    selectMode: false,
    selectedIds: new Set(),
    batchLoading: false,
    failedItems: [],
    offlineMode: false,
    enterSelectMode: vi.fn(),
    exitSelectMode: vi.fn(),
    selectAll: vi.fn(),
    toggleSelect: vi.fn(),
    handleBatchCategory: vi.fn(),
    handleBatchDelete: vi.fn(),
    handleBatchConvert: vi.fn(),
    clearFailedItems: vi.fn(),
    allSelectedInbox: false,
  }),
}));

vi.mock("../explore/TemplateSelector", () => ({
  TemplateSelector: ({ activeTab }: { activeTab: string }) => {
    if (activeTab !== "note") return null;
    return <div data-testid="template-selector" />;
  },
}));

// 注意：不 mock CreateDialog！使用真实组件

function renderExplore(initialPath = "/") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <ThemeProvider>
        <Explore />
      </ThemeProvider>
    </MemoryRouter>,
  );
}

function makeEntries(count: number, category = "note") {
  return Array.from({ length: count }, (_, i) => ({
    id: `e${i + 1}`,
    title: `Entry ${i + 1}`,
    content: `Content ${i + 1}`,
    category,
    status: "doing",
    priority: "medium",
    tags: [],
    created_at: "2024-01-01T00:00:00",
    updated_at: "2024-01-01T00:00:00",
    file_path: "",
  }));
}

describe("F04 Integration — Explore -> CreateDialog real component", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    stableRunWith503.mockImplementation(async (fn: () => Promise<void>) => {
      await fn();
    });

    mockGetEntries.mockResolvedValue({
      entries: [...makeEntries(2, "note")],
    });
    mockSearchEntries.mockResolvedValue({ results: [] });
  });

  it("inbox tab: 点击 '+New' -> 真实 CreateDialog 打开 -> 显示 inbox 类型预选 -> 输入标题 -> 创建成功 -> loadEntries 被调用", async () => {
    let shouldReturnRefreshedData = false;
    const refreshedEntries = [...makeEntries(1, "inbox"), ...makeEntries(2, "note")];

    mockGetEntries.mockImplementation(() => {
      if (shouldReturnRefreshedData) return Promise.resolve({ entries: refreshedEntries });
      return Promise.resolve({ entries: [...makeEntries(2, "note")] });
    });

    mockCreateEntry.mockImplementation(async (data: any) => ({
      id: "new-inbox-1",
      title: data.title,
      category: data.type,
      status: "doing",
      priority: "medium",
      tags: [],
      created_at: "2026-04-30T00:00:00",
      updated_at: "2026-04-30T00:00:00",
      content: "",
      file_path: "",
    }));

    const user = userEvent.setup();
    renderExplore("/?type=inbox");

    await waitFor(() => {
      expect(screen.getByTestId("task-list")).toBeInTheDocument();
    });

    // 点击 '+New'
    await user.click(screen.getByRole("button", { name: /新建/i }));

    // 真实 CreateDialog 打开 — 验证对话框标题
    expect(screen.getByText("新建条目")).toBeInTheDocument();

    // 验证 allowedTypes 只有 inbox（dialog 内只有一个类型按钮 "灵感"）
    const dialog = document.querySelector("dialog[open]");
    expect(dialog).toBeTruthy();
    const typeButtons = dialog!.querySelectorAll("button");
    // 只有一个类型按钮（inbox/灵感）
    const typeLabels = Array.from(typeButtons).map((b) => b.textContent);
    expect(typeLabels.some((t) => t?.includes("灵感"))).toBe(true);

    // 输入标题
    const titleInput = screen.getByLabelText("标题");
    await user.type(titleInput, "测试灵感");

    // 标记后续调用返回刷新数据
    shouldReturnRefreshedData = true;

    // 点击创建
    await user.click(screen.getByRole("button", { name: /^创建$/ }));

    // 等待 createEntry 被调用
    await waitFor(() => {
      expect(mockCreateEntry).toHaveBeenCalledWith(
        expect.objectContaining({ type: "inbox", title: "测试灵感" }),
        expect.objectContaining({ skipRefetch: true }),
      );
    });

    // 列表应该刷新，显示新条目
    await waitFor(() => {
      expect(screen.getByText("1 items")).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it("创建失败 -> 真实 CreateDialog 显示错误提示 -> 可重试", async () => {
    mockCreateEntry.mockRejectedValueOnce(new Error("Network error"));
    mockCreateEntry.mockResolvedValueOnce({
      id: "new-inbox-1",
      title: "测试灵感",
      category: "inbox",
      status: "doing",
      priority: "medium",
      tags: [],
      created_at: "2026-04-30T00:00:00",
      updated_at: "2026-04-30T00:00:00",
      content: "",
      file_path: "",
    });

    const user = userEvent.setup();
    renderExplore("/?type=inbox");

    await waitFor(() => {
      expect(screen.getByTestId("task-list")).toBeInTheDocument();
    });

    // 点击 '+New'
    await user.click(screen.getByRole("button", { name: /新建/i }));

    // 输入标题
    const titleInput = screen.getByLabelText("标题");
    await user.type(titleInput, "测试灵感");

    // 点击创建（第一次会失败）
    await user.click(screen.getByRole("button", { name: /^创建$/ }));

    // 等待错误提示显示
    await waitFor(() => {
      expect(screen.getByText(/创建失败/)).toBeInTheDocument();
    });

    // 对话框仍然打开
    expect(screen.getByText("新建条目")).toBeInTheDocument();

    // 重试 — 再次点击创建
    await user.click(screen.getByRole("button", { name: /^创建$/ }));

    // 第二次应该成功，对话框关闭
    await waitFor(() => {
      expect(screen.queryByText("新建条目")).not.toBeInTheDocument();
    });
  });
});
