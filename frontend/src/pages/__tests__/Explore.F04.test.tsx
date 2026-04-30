/**
 * F04: 探索页创建表单集成测试
 *
 * 覆盖：
 * - inbox/reflection/question tab 显示 '+New' 按钮
 * - note tab 不显示 '+New' 按钮
 * - 全部 tab 和搜索结果态不显示 '+New'
 * - 点击 '+New' 弹出 CreateDialog 传入对应 defaultType 和 allowedTypes
 * - 创建成功后列表可见刷新（条目数增加 / 空状态消失）
 * - 空 tab 状态下也显示 '+New' 按钮
 * - 创建失败时 CreateDialog 保持打开，可重试
 * - 搜索态（含搜索失败）不显示 '+New'
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { Explore } from "../Explore";
import { ThemeProvider } from "@/lib/theme";

// Mock scrollIntoView for tab ref
Element.prototype.scrollIntoView = vi.fn();

// --- Mocks ---

// Mock authFetch
vi.mock("@/lib/authFetch", () => ({
  authFetch: (...args: unknown[]) => mockAuthFetch(...args),
  buildAuthHeaders: () => new Headers(),
}));

const mockAuthFetch = vi.fn();

// Mock useServiceUnavailable — 返回稳定函数引用
const stableRunWith503 = vi.fn();
const stableRetry = vi.fn((fn: () => Promise<void>) => fn());
vi.mock("@/hooks/useServiceUnavailable", () => ({
  useServiceUnavailable: () => ({
    serviceUnavailable: false,
    runWith503: (fn: () => Promise<void>) => stableRunWith503(fn),
    retry: (fn: () => Promise<void>) => stableRetry(fn),
  }),
}));

// API mock
const mockGetEntries = vi.fn();
const mockSearchEntries = vi.fn();

vi.mock("@/services/api", () => ({
  getEntries: (...args: unknown[]) => mockGetEntries(...args),
  searchEntries: (...args: unknown[]) => mockSearchEntries(...args),
  fetchTemplates: vi.fn().mockResolvedValue({ templates: [] }),
}));

// Mock TaskList
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

// Mock Header
vi.mock("@/components/layout/Header", () => ({
  Header: ({ title }: { title: string }) => <h1>{title}</h1>,
}));

// Mock ActivityHeatmap
vi.mock("@/components/ActivityHeatmap", () => ({
  ActivityHeatmap: () => <div data-testid="activity-heatmap" />,
}));

// Mock SearchBar — 渲染真实 input 以支持搜索输入
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

// Mock FilterBar
vi.mock("../explore/FilterBar", () => ({
  FilterBar: () => <div data-testid="filter-bar" />,
}));

// Mock BatchActionBar
vi.mock("../explore/BatchActionBar", () => ({
  BatchActionBar: () => <div data-testid="batch-action-bar" />,
}));

// Mock useSearchHistory — 返回稳定函数引用
vi.mock("../explore/useSearchHistory", () => ({
  useSearchHistory: () => ({
    searchHistory: [],
    removeHistory: vi.fn(),
    refresh: vi.fn(),
  }),
}));

// Mock useBatchOperations
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

// Mock CreateDialog — 记录调用参数，支持成功/失败模式
let mockCreateShouldFail = false;
vi.mock("@/components/CreateDialog", () => ({
  CreateDialog: ({ open, onOpenChange, defaultType, allowedTypes, onSuccess }: any) => {
    (window as any).__createDialogProps = { open, onOpenChange, defaultType, allowedTypes, onSuccess };
    if (!open) return null;
    return (
      <div data-testid="create-dialog">
        <span data-testid="create-dialog-type">{defaultType}</span>
        <span data-testid="create-dialog-allowed-types">{(allowedTypes ?? []).join(",")}</span>
        <button data-testid="create-dialog-submit" onClick={() => {
          if (mockCreateShouldFail) return;
          const entry = { id: "new-1", title: "Test", category: defaultType, status: "doing", priority: "medium", tags: [], created_at: "", updated_at: "", content: "", file_path: "" };
          onSuccess?.(entry);
          onOpenChange(false);
        }}>
          创建
        </button>
      </div>
    );
  },
}));

// Mock TemplateSelector
vi.mock("../explore/TemplateSelector", () => ({
  TemplateSelector: ({ activeTab }: { activeTab: string }) => {
    if (activeTab !== "note") return null;
    return <div data-testid="template-selector" />;
  },
}));

function renderExplore(initialPath = "/") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <ThemeProvider>
        <Explore />
      </ThemeProvider>
    </MemoryRouter>,
  );
}

// 标准条目 mock
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

// 混合类型条目
function makeMixedEntries() {
  return [
    ...makeEntries(2, "inbox"),
    ...makeEntries(2, "note"),
    ...makeEntries(2, "reflection"),
    ...makeEntries(2, "question"),
  ];
}

// 控制数据返回的辅助变量
let shouldReturnRefreshedData = false;
let initialData: any = null;
let refreshedData: any = null;

describe("Explore — F04 创建表单集成", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCreateShouldFail = false;
    shouldReturnRefreshedData = false;
    initialData = null;
    refreshedData = null;

    stableRunWith503.mockImplementation(async (fn: () => Promise<void>) => {
      await fn();
    });

    // 默认返回混合类型数据
    mockGetEntries.mockResolvedValue({
      entries: makeMixedEntries(),
    });
    mockSearchEntries.mockResolvedValue({ results: [] });
  });

  afterEach(() => {
    shouldReturnRefreshedData = false;
  });

  // ---- 1. inbox tab 显示 '+New' 按钮 ----
  it("inbox tab 显示 '+New' 按钮", async () => {
    renderExplore("/?type=inbox");

    await waitFor(() => {
      expect(screen.getByTestId("task-list")).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: /新建/i })).toBeInTheDocument();
  });

  // ---- 2. reflection tab 显示 '+New' 按钮 ----
  it("reflection tab 显示 '+New' 按钮", async () => {
    renderExplore("/?type=reflection");

    await waitFor(() => {
      expect(screen.getByTestId("task-list")).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: /新建/i })).toBeInTheDocument();
  });

  // ---- 3. question tab 显示 '+New' 按钮 ----
  it("question tab 显示 '+New' 按钮", async () => {
    renderExplore("/?type=question");

    await waitFor(() => {
      expect(screen.getByTestId("task-list")).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: /新建/i })).toBeInTheDocument();
  });

  // ---- 4. note tab 不显示 '+New' 按钮 ----
  it("note tab 不显示 '+New' 按钮（使用模板选择器）", async () => {
    renderExplore("/?type=note");

    await waitFor(() => {
      expect(screen.getByTestId("task-list")).toBeInTheDocument();
    });

    expect(screen.queryByRole("button", { name: /新建/i })).not.toBeInTheDocument();
  });

  // ---- 5. 全部 tab 不显示 '+New' ----
  it("全部 tab 不显示 '+New' 按钮", async () => {
    renderExplore("/");

    await waitFor(() => {
      expect(screen.getByTestId("task-list")).toBeInTheDocument();
    });

    expect(screen.queryByRole("button", { name: /新建/i })).not.toBeInTheDocument();
  });

  // ---- 6. 点击 '+New' 弹出 CreateDialog 传入 defaultType ----
  it("点击 inbox 的 '+New' 弹出 CreateDialog(defaultType='inbox')", async () => {
    const user = userEvent.setup();
    renderExplore("/?type=inbox");

    await waitFor(() => {
      expect(screen.getByTestId("task-list")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /新建/i }));

    expect(screen.getByTestId("create-dialog")).toBeInTheDocument();
    expect(screen.getByTestId("create-dialog-type")).toHaveTextContent("inbox");
  });

  it("点击 reflection 的 '+New' 弹出 CreateDialog(defaultType='reflection')", async () => {
    const user = userEvent.setup();
    renderExplore("/?type=reflection");

    await waitFor(() => {
      expect(screen.getByTestId("task-list")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /新建/i }));

    expect(screen.getByTestId("create-dialog")).toBeInTheDocument();
    expect(screen.getByTestId("create-dialog-type")).toHaveTextContent("reflection");
  });

  it("点击 question 的 '+New' 弹出 CreateDialog(defaultType='question')", async () => {
    const user = userEvent.setup();
    renderExplore("/?type=question");

    await waitFor(() => {
      expect(screen.getByTestId("task-list")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /新建/i }));

    expect(screen.getByTestId("create-dialog")).toBeInTheDocument();
    expect(screen.getByTestId("create-dialog-type")).toHaveTextContent("question");
  });

  // ---- 7. 创建成功后列表可见刷新 ----
  it("空 inbox tab 创建成功后列表刷新，空状态消失", async () => {
    initialData = { entries: makeEntries(3, "note") };
    refreshedData = { entries: [...makeEntries(1, "inbox"), ...makeEntries(3, "note")] };

    mockGetEntries.mockImplementation(() => {
      if (shouldReturnRefreshedData) return Promise.resolve(refreshedData);
      return Promise.resolve(initialData);
    });

    const user = userEvent.setup();
    renderExplore("/?type=inbox");

    await waitFor(() => {
      expect(screen.getByTestId("task-list")).toBeInTheDocument();
    });

    // 初始 inbox 空状态
    expect(screen.getByText(/暂无/)).toBeInTheDocument();

    // 标记后续调用应返回刷新数据
    shouldReturnRefreshedData = true;

    // 点击新建并创建
    await user.click(screen.getByRole("button", { name: /新建/i }));
    await user.click(screen.getByTestId("create-dialog-submit"));

    // 列表刷新后空状态消失，显示 1 条记录
    await waitFor(() => {
      expect(screen.getByText("1 items")).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  // ---- 7b. 列表已有条目时创建成功，条目数增加 ----
  it("已有条目的 tab 创建成功后列表刷新，条目数增加", async () => {
    initialData = { entries: [...makeEntries(2, "inbox"), ...makeEntries(2, "note")] };
    refreshedData = { entries: [...makeEntries(3, "inbox"), ...makeEntries(2, "note")] };

    mockGetEntries.mockImplementation(() => {
      if (shouldReturnRefreshedData) return Promise.resolve(refreshedData);
      return Promise.resolve(initialData);
    });

    const user = userEvent.setup();
    renderExplore("/?type=inbox");

    await waitFor(() => {
      expect(screen.getByTestId("task-list")).toBeInTheDocument();
    });

    // 初始 2 条 inbox
    expect(screen.getByText("2 items")).toBeInTheDocument();

    // 标记后续调用应返回刷新数据
    shouldReturnRefreshedData = true;

    // 点击新建并创建
    await user.click(screen.getByRole("button", { name: /新建/i }));
    await user.click(screen.getByTestId("create-dialog-submit"));

    // 列表刷新后显示 3 条记录
    await waitFor(() => {
      expect(screen.getByText("3 items")).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  // ---- 7c. 创建失败时 CreateDialog 保持打开 ----
  it("创建失败时 CreateDialog 保持打开可重试", async () => {
    mockCreateShouldFail = true;

    const user = userEvent.setup();
    renderExplore("/?type=inbox");

    await waitFor(() => {
      expect(screen.getByTestId("task-list")).toBeInTheDocument();
    });

    // 点击新建
    await user.click(screen.getByRole("button", { name: /新建/i }));
    expect(screen.getByTestId("create-dialog")).toBeInTheDocument();

    // 模拟失败提交 — 对话框不会关闭
    await user.click(screen.getByTestId("create-dialog-submit"));

    // CreateDialog 仍保持打开，用户可重试
    expect(screen.getByTestId("create-dialog")).toBeInTheDocument();

    // 修复失败，再次点击应该成功
    mockCreateShouldFail = false;
    await user.click(screen.getByTestId("create-dialog-submit"));

    // 对话框关闭，列表刷新
    await waitFor(() => {
      expect(screen.queryByTestId("create-dialog")).not.toBeInTheDocument();
    });
  });

  // ---- 8. 空 tab 状态下也显示 '+New' ----
  it("空 tab（0 条记录）时也显示 '+New' 按钮", async () => {
    mockGetEntries.mockResolvedValue({ entries: [] });

    renderExplore("/?type=inbox");

    await waitFor(() => {
      expect(screen.getByTestId("task-list")).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: /新建/i })).toBeInTheDocument();
  });

  // ---- 9. CreateDialog 不传 skipStoreRefetch，由 Explore 在 onSuccess 中自行调用 loadEntries ----
  it("CreateDialog 不传 skipStoreRefetch，onSuccess 中调用 loadEntries 刷新", async () => {
    const user = userEvent.setup();
    renderExplore("/?type=inbox");

    await waitFor(() => {
      expect(screen.getByTestId("task-list")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /新建/i }));

    const props = (window as any).__createDialogProps;
    // CreateDialog 不再接收 skipStoreRefetch prop
    expect(props.skipStoreRefetch).toBeUndefined();
    // onSuccess 回调存在（Explore 会调用 loadEntries）
    expect(props.onSuccess).toBeDefined();
  });

  // ---- 9b. CreateDialog 传入 allowedTypes 约束类型 ----
  it("inbox tab 的 CreateDialog allowedTypes 只包含 inbox", async () => {
    const user = userEvent.setup();
    renderExplore("/?type=inbox");

    await waitFor(() => {
      expect(screen.getByTestId("task-list")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /新建/i }));

    const props = (window as any).__createDialogProps;
    expect(props.allowedTypes).toEqual(["inbox"]);
  });

  it("reflection tab 的 CreateDialog allowedTypes 只包含 reflection", async () => {
    const user = userEvent.setup();
    renderExplore("/?type=reflection");

    await waitFor(() => {
      expect(screen.getByTestId("task-list")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /新建/i }));

    const props = (window as any).__createDialogProps;
    expect(props.allowedTypes).toEqual(["reflection"]);
  });

  it("question tab 的 CreateDialog allowedTypes 只包含 question", async () => {
    const user = userEvent.setup();
    renderExplore("/?type=question");

    await waitFor(() => {
      expect(screen.getByTestId("task-list")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /新建/i }));

    const props = (window as any).__createDialogProps;
    expect(props.allowedTypes).toEqual(["question"]);
  });

  // ---- 10. 搜索态不显示 '+New'（搜索有结果） ----
  it("搜索态不显示 '+New' 按钮（搜索有结果时）", async () => {
    mockSearchEntries.mockResolvedValue({
      results: [
        { id: "s1", title: "Search result", category: "inbox", status: "doing", score: 0.9 },
      ],
    });

    const user = userEvent.setup();
    renderExplore("/?type=inbox");

    await waitFor(() => {
      expect(screen.getByTestId("task-list")).toBeInTheDocument();
    });

    // 初始 inbox tab 应该有 '+New' 按钮
    expect(screen.getByRole("button", { name: /新建/i })).toBeInTheDocument();

    // 输入搜索词触发搜索模式
    const searchInput = screen.getByTestId("search-bar-input");
    await user.clear(searchInput);
    await user.type(searchInput, "test query");

    await waitFor(() => {
      expect(mockSearchEntries).toHaveBeenCalled();
    }, { timeout: 3000 });

    // 搜索态不应该有 '+New' 按钮
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: /新建/i })).not.toBeInTheDocument();
    });
  });

  // ---- 10b. 搜索态不显示 '+New'（搜索失败时） ----
  it("搜索态不显示 '+New' 按钮（搜索失败时）", async () => {
    mockSearchEntries.mockRejectedValue(new Error("Search failed"));

    const user = userEvent.setup();
    renderExplore("/?type=inbox");

    await waitFor(() => {
      expect(screen.getByTestId("task-list")).toBeInTheDocument();
    });

    // 初始 inbox tab 应该有 '+New' 按钮
    expect(screen.getByRole("button", { name: /新建/i })).toBeInTheDocument();

    // 输入搜索词触发搜索模式
    const searchInput = screen.getByTestId("search-bar-input");
    await user.clear(searchInput);
    await user.type(searchInput, "test query");

    await waitFor(() => {
      expect(mockSearchEntries).toHaveBeenCalled();
    }, { timeout: 3000 });

    // 搜索失败时只要有 searchQuery 就不应该有 '+New' 按钮
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: /新建/i })).not.toBeInTheDocument();
    });
  });
});
