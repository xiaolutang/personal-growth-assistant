import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { Tasks } from "./Tasks";
import { useTaskStore } from "@/stores/taskStore";
import { resetStore, createMockTask } from "@/testUtils/taskStoreHelpers";

// Mock useNavigate to verify navigation calls
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

// Mock API module
vi.mock("@/services/api", () => ({
  getEntries: vi.fn().mockResolvedValue({ entries: [] }),
  createEntry: vi.fn(),
  updateEntry: vi.fn(),
  deleteEntry: vi.fn(),
  searchEntries: vi.fn(),
  getKnowledgeGraph: vi.fn(),
}));

// Mock child components that may have external dependencies
vi.mock("@/components/layout/Header", () => ({
  Header: ({ title }: { title: string }) => <header>{title}</header>,
}));

// Mock TaskList to expose empty-state props for assertion
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

beforeEach(() => {
  resetStore();
  vi.clearAllMocks();
  mockNavigate.mockClear();
});

describe("Tasks 页面 503 降级集成", () => {
  it("serviceUnavailable=true 时显示 ServiceUnavailable 组件而非任务列表", () => {
    useTaskStore.setState({ serviceUnavailable: true });

    renderWithRouter(<Tasks />);

    expect(screen.getByText("服务暂时不可用")).toBeInTheDocument();
    expect(screen.getByText("重试")).toBeInTheDocument();
    expect(screen.queryByText(/所有任务/)).not.toBeInTheDocument();
  });

  it("serviceUnavailable=false 时显示任务列表卡片", () => {
    useTaskStore.setState({
      serviceUnavailable: false,
      tasks: [createMockTask({ id: "1", title: "测试任务" })],
    });

    renderWithRouter(<Tasks />);

    expect(screen.getByText(/所有任务/)).toBeInTheDocument();
    expect(screen.queryByText("服务暂时不可用")).not.toBeInTheDocument();
  });

  it("点击重试按钮调用 fetchEntries（且挂载时不会自动调用）", async () => {
    useTaskStore.setState({ serviceUnavailable: true });
    const fetchSpy = vi.spyOn(useTaskStore.getState(), "fetchEntries");

    renderWithRouter(<Tasks />);

    // 挂载时不应自动调用 fetchEntries（因为 serviceUnavailable=true）
    expect(fetchSpy).not.toHaveBeenCalled();

    await userEvent.click(screen.getByText("重试"));
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(fetchSpy).toHaveBeenCalledWith({ type: "task", limit: 100 });
  });
});

describe("F139: Tasks 空状态展示", () => {
  it("无任务时显示空状态引导文案和快速创建入口", async () => {
    useTaskStore.setState({
      tasks: [],
      isLoading: false,
      serviceUnavailable: false,
    });

    renderWithRouter(<Tasks />);

    // 等待 fetchEntries 完成，isLoading 从 true 回到 false
    await waitFor(() => {
      expect(screen.getByText("还没有任务，开始记录你的第一个任务吧")).toBeInTheDocument();
    });
    expect(screen.getByTestId("empty-action")).toBeInTheDocument();
    expect(screen.getByText("去创建任务")).toBeInTheDocument();
  });

  it("点击快速创建入口导航到首页", async () => {
    useTaskStore.setState({
      tasks: [],
      isLoading: false,
      serviceUnavailable: false,
    });

    renderWithRouter(<Tasks />);

    const createBtn = await screen.findByText("去创建任务");
    await userEvent.click(createBtn);

    // 验证 navigate 被调用，目标是首页 "/"
    expect(mockNavigate).toHaveBeenCalledWith("/");
  });

  it("有任务时正常显示列表，不显示空状态", async () => {
    useTaskStore.setState({
      tasks: [createMockTask({ id: "1", title: "已完成任务", status: "complete" })],
      isLoading: false,
      serviceUnavailable: false,
    });

    renderWithRouter(<Tasks />);

    await waitFor(() => {
      expect(screen.getByText(/所有任务/)).toBeInTheDocument();
    });
    expect(screen.queryByText("还没有任务，开始记录你的第一个任务吧")).not.toBeInTheDocument();
    expect(screen.queryByText("当前筛选条件下没有匹配的任务")).not.toBeInTheDocument();
  });

  it("筛选无结果时显示清除筛选按钮和提示", async () => {
    // 有一个 doing 状态的任务
    useTaskStore.setState({
      tasks: [createMockTask({ id: "1", title: "进行中任务", status: "doing" })],
      isLoading: false,
      serviceUnavailable: false,
    });

    renderWithRouter(<Tasks />);

    // 等待加载完成
    await waitFor(() => {
      expect(screen.getByText(/所有任务/)).toBeInTheDocument();
    });

    // 打开筛选面板
    const filterBtn = screen.getByText("筛选");
    await userEvent.click(filterBtn);

    // 点击 "待开始" 状态 badge（与 doing 不匹配，会导致筛选无结果）
    const waitStartBadge = screen.getByText("待开始");
    await userEvent.click(waitStartBadge);

    // 现在应该显示筛选无结果提示
    await waitFor(() => {
      expect(screen.getByText("当前筛选条件下没有匹配的任务")).toBeInTheDocument();
    });
    expect(screen.getByText("清除筛选")).toBeInTheDocument();
  });

  it("加载中不显示空状态", () => {
    useTaskStore.setState({
      tasks: [],
      isLoading: true,
      serviceUnavailable: false,
    });

    renderWithRouter(<Tasks />);

    expect(screen.getByText("加载中...")).toBeInTheDocument();
    expect(screen.queryByText("还没有任务")).not.toBeInTheDocument();
    expect(screen.queryByText("当前筛选条件")).not.toBeInTheDocument();
  });
});
