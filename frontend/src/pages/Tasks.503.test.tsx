import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Tasks } from "./Tasks";
import { useTaskStore } from "@/stores/taskStore";

// Mock API module
vi.mock("@/services/api", () => ({
  getEntries: vi.fn(),
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

vi.mock("@/components/TaskList", () => ({
  TaskList: ({ tasks }: { tasks: unknown[] }) => (
    <div data-testid="task-list">{tasks.length} tasks</div>
  ),
}));

function resetStore() {
  useTaskStore.setState({
    tasks: [],
    error: null,
    serviceUnavailable: false,
    isLoading: false,
    searchResults: [],
    knowledgeGraph: null,
  });
}

beforeEach(() => {
  resetStore();
  vi.clearAllMocks();
});

describe("Tasks 页面 503 集成", () => {
  it("serviceUnavailable=true 时显示 ServiceUnavailable 组件而非任务列表", () => {
    useTaskStore.setState({ serviceUnavailable: true });

    render(<Tasks />);

    // 应显示降级提示
    expect(screen.getByText("服务暂时不可用")).toBeInTheDocument();
    // 应有重试按钮
    expect(screen.getByText("重试")).toBeInTheDocument();
    // 不应显示任务列表卡片
    expect(screen.queryByText(/所有任务/)).not.toBeInTheDocument();
  });

  it("serviceUnavailable=false 时显示任务列表卡片", () => {
    useTaskStore.setState({
      serviceUnavailable: false,
      tasks: [
        {
          id: "1",
          title: "测试任务",
          content: "",
          category: "task",
          status: "doing",
          tags: [],
          created_at: "2026-04-11T00:00:00",
          updated_at: "2026-04-11T00:00:00",
          file_path: "test.md",
        },
      ],
    });

    render(<Tasks />);

    // 应显示任务列表
    expect(screen.getByText(/所有任务/)).toBeInTheDocument();
    // 不应显示降级提示
    expect(screen.queryByText("服务暂时不可用")).not.toBeInTheDocument();
  });

  it("点击重试按钮调用 fetchEntries", async () => {
    useTaskStore.setState({ serviceUnavailable: true });
    const fetchSpy = vi.spyOn(useTaskStore.getState(), "fetchEntries");

    render(<Tasks />);

    await userEvent.click(screen.getByText("重试"));
    expect(fetchSpy).toHaveBeenCalledWith({ type: "task", limit: 100 });
  });
});
