import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Tasks } from "./Tasks";
import { useTaskStore } from "@/stores/taskStore";
import { resetStore, createMockTask } from "@/testUtils/taskStoreHelpers";

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

beforeEach(() => {
  resetStore();
  vi.clearAllMocks();
});

describe("Tasks 页面 503 降级集成", () => {
  it("serviceUnavailable=true 时显示 ServiceUnavailable 组件而非任务列表", () => {
    useTaskStore.setState({ serviceUnavailable: true });

    render(<Tasks />);

    expect(screen.getByText("服务暂时不可用")).toBeInTheDocument();
    expect(screen.getByText("重试")).toBeInTheDocument();
    expect(screen.queryByText(/所有任务/)).not.toBeInTheDocument();
  });

  it("serviceUnavailable=false 时显示任务列表卡片", () => {
    useTaskStore.setState({
      serviceUnavailable: false,
      tasks: [createMockTask({ id: "1", title: "测试任务" })],
    });

    render(<Tasks />);

    expect(screen.getByText(/所有任务/)).toBeInTheDocument();
    expect(screen.queryByText("服务暂时不可用")).not.toBeInTheDocument();
  });

  it("点击重试按钮调用 fetchEntries（且挂载时不会自动调用）", async () => {
    useTaskStore.setState({ serviceUnavailable: true });
    const fetchSpy = vi.spyOn(useTaskStore.getState(), "fetchEntries");

    render(<Tasks />);

    // 挂载时不应自动调用 fetchEntries（因为 serviceUnavailable=true）
    expect(fetchSpy).not.toHaveBeenCalled();

    await userEvent.click(screen.getByText("重试"));
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(fetchSpy).toHaveBeenCalledWith({ type: "task", limit: 100 });
  });
});
