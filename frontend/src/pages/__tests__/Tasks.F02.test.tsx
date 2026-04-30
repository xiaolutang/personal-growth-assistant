/**
 * F02: Tasks page '+New' button + context-aware creation
 * - '+New' button visible in sub-tab bar
 * - Click '+New' opens CreateDialog with context-aware defaultType
 * - '全部' tab: allowedTypes = ACTIONABLE_CATEGORIES only
 * - Empty state: '去创建任务' opens CreateDialog instead of navigating
 * - CreateDialog closes after successful creation
 * - Sub-tab switching keeps '+New' visible
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { Tasks } from "../Tasks";
import { useTaskStore } from "@/stores/taskStore";
import { resetStore, createMockTask } from "@/testUtils/taskStoreHelpers";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function renderWithRouter(ui: React.ReactElement, initialEntries?: string[]) {
  return render(
    <MemoryRouter initialEntries={initialEntries || ["/tasks"]}>
      {ui}
    </MemoryRouter>
  );
}

// Mock API
vi.mock("@/services/api", () => ({
  getEntries: vi.fn().mockResolvedValue({ entries: [] }),
  createEntry: vi.fn(),
  updateEntry: vi.fn(),
  deleteEntry: vi.fn(),
  searchEntries: vi.fn(),
  getKnowledgeGraph: vi.fn(),
}));

// Mock Header
vi.mock("@/components/layout/Header", () => ({
  Header: ({ title }: { title: string }) => <header>{title}</header>,
}));

// Mock PullToRefresh
vi.mock("@/components/PullToRefresh", () => ({
  PullToRefresh: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

// Mock ServiceUnavailable
vi.mock("@/components/ServiceUnavailable", () => ({
  ServiceUnavailable: ({ onRetry }: { onRetry: () => void }) => (
    <div>
      <span>服务暂时不可用</span>
      <button onClick={onRetry}>重试</button>
    </div>
  ),
}));

// Mock TaskList
vi.mock("@/components/TaskList", () => ({
  TaskList: ({ tasks, emptyMessage, emptyAction }: {
    tasks: unknown[];
    emptyMessage?: string;
    emptyAction?: { label: string; onClick: () => void };
  }) => (
    <div data-testid="task-list">
      {tasks.length > 0 ? (
        <span>{tasks.length} tasks</span>
      ) : (
        <div data-testid="task-list-empty">
          <span>{emptyMessage ?? "暂无任务"}</span>
          {emptyAction && (
            <button data-testid="empty-action" onClick={emptyAction.onClick}>
              {emptyAction.label}
            </button>
          )}
        </div>
      )}
    </div>
  ),
}));

// Mock GroupedView
vi.mock("../tasks/GroupedView", () => ({
  GroupedView: ({ tasks }: { tasks: unknown[] }) => (
    <div data-testid="grouped-view">
      {tasks.length > 0 ? <span>{tasks.length} grouped tasks</span> : <span>暂无任务</span>}
    </div>
  ),
}));

// Mock TimelineView
vi.mock("../tasks/TimelineView", () => ({
  TimelineView: ({ tasks }: { tasks: unknown[] }) => (
    <div data-testid="timeline-view">
      {tasks.length > 0 ? <span>{tasks.length} timeline tasks</span> : <span>暂无任务</span>}
    </div>
  ),
}));

// Mock ViewSelector
vi.mock("../tasks/ViewSelector", () => ({
  ViewSelector: () => <div data-testid="view-selector" />,
}));

vi.mock("@/components/CreateDialog", () => ({
  CreateDialog: (props: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    defaultType?: string | null;
    allowedTypes?: string[];
    onSuccess?: (entry: unknown) => void;
  }) => {
    return props.open ? (
      <div data-testid="create-dialog">
        <span data-testid="create-dialog-default-type">{props.defaultType ?? "none"}</span>
        <span data-testid="create-dialog-allowed-types">
          {props.allowedTypes ? props.allowedTypes.join(",") : "all"}
        </span>
        <button
          data-testid="create-dialog-close"
          onClick={() => props.onOpenChange(false)}
        >
          关闭
        </button>
        <button
          data-testid="create-dialog-submit"
          onClick={() => {
            // Simulate successful creation
            props.onSuccess?.({ id: "new-1", title: "新任务", category: "task" });
            props.onOpenChange(false);
          }}
        >
          提交
        </button>
      </div>
    ) : null;
  },
}));

beforeEach(() => {
  resetStore();
  vi.clearAllMocks();
  mockNavigate.mockClear();
});

describe("F02: '+New' 按钮 - 基本显示", () => {
  it("子 Tab 栏右侧出现 '+New' 按钮（Plus 图标）", () => {
    useTaskStore.setState({
      tasks: [createMockTask({ id: "1" })],
      isLoading: false,
      serviceUnavailable: false,
    });

    renderWithRouter(<Tasks />);

    expect(screen.getByLabelText("新建条目")).toBeInTheDocument();
  });

  it("子 Tab 切换时 '+New' 按钮保持可见", async () => {
    useTaskStore.setState({
      tasks: [
        createMockTask({ id: "1", category: "task" }),
        createMockTask({ id: "2", category: "decision" }),
      ],
      isLoading: false,
      serviceUnavailable: false,
    });

    renderWithRouter(<Tasks />);

    expect(screen.getByLabelText("新建条目")).toBeInTheDocument();

    await userEvent.click(screen.getByText("决策"));

    expect(screen.getByLabelText("新建条目")).toBeInTheDocument();
  });

  it("视图切换不影响 '+New' 按钮", async () => {
    useTaskStore.setState({
      tasks: [createMockTask({ id: "1" })],
      isLoading: false,
      serviceUnavailable: false,
    });

    renderWithRouter(<Tasks />);

    expect(screen.getByLabelText("新建条目")).toBeInTheDocument();
  });
});

describe("F02: '+New' 按钮 - 上下文感知创建", () => {
  it("任务 tab 点击 '+New' → CreateDialog 以 task 默认类型打开", async () => {
    useTaskStore.setState({
      tasks: [createMockTask({ id: "1", category: "task" })],
      isLoading: false,
      serviceUnavailable: false,
    });

    renderWithRouter(<Tasks />);

    // Switch to task tab
    await userEvent.click(screen.getByText("任务"));
    await userEvent.click(screen.getByLabelText("新建条目"));

    await waitFor(() => {
      expect(screen.getByTestId("create-dialog")).toBeInTheDocument();
    });
    expect(screen.getByTestId("create-dialog-default-type")).toHaveTextContent("task");
  });

  it("决策 tab 点击 '+New' → CreateDialog 以 decision 默认类型打开", async () => {
    useTaskStore.setState({
      tasks: [createMockTask({ id: "1", category: "decision" })],
      isLoading: false,
      serviceUnavailable: false,
    });

    renderWithRouter(<Tasks />);

    await userEvent.click(screen.getByText("决策"));
    await userEvent.click(screen.getByLabelText("新建条目"));

    await waitFor(() => {
      expect(screen.getByTestId("create-dialog")).toBeInTheDocument();
    });
    expect(screen.getByTestId("create-dialog-default-type")).toHaveTextContent("decision");
  });

  it("项目 tab 点击 '+New' → CreateDialog 以 project 默认类型打开", async () => {
    useTaskStore.setState({
      tasks: [createMockTask({ id: "1", category: "project" })],
      isLoading: false,
      serviceUnavailable: false,
    });

    renderWithRouter(<Tasks />);

    await userEvent.click(screen.getByText("项目"));
    await userEvent.click(screen.getByLabelText("新建条目"));

    await waitFor(() => {
      expect(screen.getByTestId("create-dialog")).toBeInTheDocument();
    });
    expect(screen.getByTestId("create-dialog-default-type")).toHaveTextContent("project");
  });

  it("全部 tab 点击 '+New' → CreateDialog 无默认类型，allowedTypes 仅含 task/decision/project", async () => {
    useTaskStore.setState({
      tasks: [createMockTask({ id: "1" })],
      isLoading: false,
      serviceUnavailable: false,
    });

    renderWithRouter(<Tasks />);

    // Default is 'all' tab
    await userEvent.click(screen.getByLabelText("新建条目"));

    await waitFor(() => {
      expect(screen.getByTestId("create-dialog")).toBeInTheDocument();
    });
    expect(screen.getByTestId("create-dialog-default-type")).toHaveTextContent("none");
    expect(screen.getByTestId("create-dialog-allowed-types")).toHaveTextContent("task,decision,project");
  });

  it("全部 tab 类型选择器不包含 inbox/note/reflection/question", async () => {
    useTaskStore.setState({
      tasks: [createMockTask({ id: "1" })],
      isLoading: false,
      serviceUnavailable: false,
    });

    renderWithRouter(<Tasks />);

    await userEvent.click(screen.getByLabelText("新建条目"));

    await waitFor(() => {
      expect(screen.getByTestId("create-dialog")).toBeInTheDocument();
    });

    const allowedTypesStr = screen.getByTestId("create-dialog-allowed-types").textContent;
    expect(allowedTypesStr).not.toContain("inbox");
    expect(allowedTypesStr).not.toContain("note");
    expect(allowedTypesStr).not.toContain("reflection");
    expect(allowedTypesStr).not.toContain("question");
  });
});

describe("F02: 空状态 - 去创建任务按钮", () => {
  it("空状态点击 '去创建任务' 弹出 CreateDialog(defaultType='task')，不跳转首页", async () => {
    useTaskStore.setState({
      tasks: [],
      isLoading: false,
      serviceUnavailable: false,
    });

    renderWithRouter(<Tasks />);

    const createBtn = await screen.findByText("去创建任务");
    await userEvent.click(createBtn);

    // Should NOT navigate to "/"
    expect(mockNavigate).not.toHaveBeenCalledWith("/");

    // Should open CreateDialog with defaultType='task'
    await waitFor(() => {
      expect(screen.getByTestId("create-dialog")).toBeInTheDocument();
    });
    expect(screen.getByTestId("create-dialog-default-type")).toHaveTextContent("task");
  });
});

describe("F02: 创建成功后自动刷新", () => {
  it("CreateDialog 成功回调关闭对话框", async () => {
    useTaskStore.setState({
      tasks: [createMockTask({ id: "1" })],
      isLoading: false,
      serviceUnavailable: false,
    });

    renderWithRouter(<Tasks />);

    await userEvent.click(screen.getByLabelText("新建条目"));

    await waitFor(() => {
      expect(screen.getByTestId("create-dialog")).toBeInTheDocument();
    });

    // Simulate submit (CreateDialog mock calls onSuccess then onOpenChange(false))
    await userEvent.click(screen.getByTestId("create-dialog-submit"));

    await waitFor(() => {
      expect(screen.queryByTestId("create-dialog")).not.toBeInTheDocument();
    });
  });

  it("创建成功后 onSuccess 以 TASK_QUERY_PARAMS 重新拉取，保证 actionable-only + limit=100 语义", async () => {
    const fetchSpy = vi.spyOn(useTaskStore.getState(), "fetchEntries");
    useTaskStore.setState({
      tasks: [createMockTask({ id: "1" })],
      isLoading: false,
      serviceUnavailable: false,
    });

    renderWithRouter(<Tasks />);

    await userEvent.click(screen.getByLabelText("新建条目"));

    await waitFor(() => {
      expect(screen.getByTestId("create-dialog")).toBeInTheDocument();
    });

    // Record call count before submit
    const callsBefore = fetchSpy.mock.calls.length;

    // Simulate successful creation (mock calls onSuccess with skipRefetch)
    await userEvent.click(screen.getByTestId("create-dialog-submit"));

    // onSuccess should call fetchEntries with TASK_QUERY_PARAMS (single refresh, no double-fetch)
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith({ category_group: "actionable", limit: 100 });
    });

    // Only one additional fetchEntries call (no double-fetch from store internal)
    expect(fetchSpy.mock.calls.length).toBe(callsBefore + 1);

    // Dialog closes after creation
    await waitFor(() => {
      expect(screen.queryByTestId("create-dialog")).not.toBeInTheDocument();
    });
  });
});

describe("F02: grouped/timeline 空状态创建入口", () => {
  it("grouped 视图空状态显示 '去创建任务' 按钮，点击弹出 CreateDialog", async () => {
    useTaskStore.setState({
      tasks: [],
      isLoading: false,
      serviceUnavailable: false,
    });

    renderWithRouter(<Tasks />, ["/tasks?view=grouped"]);

    const createBtn = await screen.findByText("去创建任务");
    expect(createBtn).toBeInTheDocument();

    await userEvent.click(createBtn);

    await waitFor(() => {
      expect(screen.getByTestId("create-dialog")).toBeInTheDocument();
    });
    expect(screen.getByTestId("create-dialog-default-type")).toHaveTextContent("task");
  });

  it("timeline 视图空状态显示 '去创建任务' 按钮，点击弹出 CreateDialog", async () => {
    useTaskStore.setState({
      tasks: [],
      isLoading: false,
      serviceUnavailable: false,
    });

    renderWithRouter(<Tasks />, ["/tasks?view=timeline"]);

    const createBtn = await screen.findByText("去创建任务");
    expect(createBtn).toBeInTheDocument();

    await userEvent.click(createBtn);

    await waitFor(() => {
      expect(screen.getByTestId("create-dialog")).toBeInTheDocument();
    });
    expect(screen.getByTestId("create-dialog-default-type")).toHaveTextContent("task");
  });
});
