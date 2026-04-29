import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { TaskCard } from "@/components/TaskCard";
import type { Task, TaskStatus } from "@/types/task";

// Mock sonner
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
  Toaster: () => null,
}));

// Mock createEntry for reflection
const mockCreateEntry = vi.fn();
vi.mock("@/services/api", () => ({
  convertEntry: vi.fn(),
}));

// Mock taskStore selectors
const mockUpdateTaskStatus = vi.fn();
const mockDeleteTask = vi.fn();
const mockTasks: Task[] = [];

vi.mock("@/stores/taskStore", () => ({
  useTaskStore: (selector: (state: Record<string, unknown>) => unknown) => {
    const state = {
      updateTaskStatus: mockUpdateTaskStatus,
      deleteTask: mockDeleteTask,
      tasks: mockTasks,
      createEntry: mockCreateEntry,
    };
    return selector(state);
  },
}));

function createDoingTask(overrides: Partial<Task> = {}): Task {
  return {
    id: "task-doing123",
    title: "学习 TypeScript",
    content: "任务内容",
    category: "task",
    status: "doing",
    tags: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    file_path: "tasks/task-doing123.md",
    ...overrides,
  };
}

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("TaskCard — 完成时复盘提示集成", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("doing -> complete 时显示复盘提示", () => {
    const task = createDoingTask({ status: "doing" });

    // After status toggle, the task becomes complete
    mockUpdateTaskStatus.mockImplementation(async () => {});

    const { rerender } = renderWithRouter(<TaskCard task={task} />);

    // Initially no prompt
    expect(screen.queryByText("写个复盘？")).not.toBeInTheDocument();

    // Simulate task becoming complete after toggle
    const updatedTask = { ...task, status: "complete" as TaskStatus };
    rerender(
      <MemoryRouter>
        <TaskCard task={updatedTask} />
      </MemoryRouter>
    );

    expect(screen.getByText("写个复盘？")).toBeInTheDocument();
  });

  it("complete 的 task 直接显示复盘提示", () => {
    const task = createDoingTask({ status: "complete" });

    renderWithRouter(<TaskCard task={task} />);

    // complete 状态的 task 直接显示复盘提示
    expect(screen.getByText("写个复盘？")).toBeInTheDocument();
  });

  it("跳过后关闭复盘提示", async () => {
    const user = userEvent.setup();
    const task = createDoingTask({ status: "complete" });

    renderWithRouter(<TaskCard task={task} />);

    expect(screen.getByText("写个复盘？")).toBeInTheDocument();
    await user.click(screen.getByText("跳过"));

    // Prompt should be dismissed
    await waitFor(() => {
      expect(screen.queryByText("写个复盘？")).not.toBeInTheDocument();
    });
  });

  it("写复盘 -> 创建 reflection 并跳转", async () => {
    const user = userEvent.setup();
    const task = createDoingTask({ status: "complete" });

    mockCreateEntry.mockResolvedValueOnce({ id: "reflection-new1", title: "关于「学习 TypeScript」的复盘" });

    renderWithRouter(<TaskCard task={task} />);

    await user.click(screen.getByText("写复盘"));

    await waitFor(() => {
      expect(mockCreateEntry).toHaveBeenCalledWith({
        type: "reflection",
        title: "关于「学习 TypeScript」的复盘",
        parent_id: "task-doing123",
      });
    });
  });

  it("非 complete 状态不显示复盘提示", () => {
    const task = createDoingTask({ status: "doing" });
    renderWithRouter(<TaskCard task={task} />);
    expect(screen.queryByText("写个复盘？")).not.toBeInTheDocument();
  });

  it("跳过后再次渲染不再弹出", async () => {
    const user = userEvent.setup();
    const task = createDoingTask({ status: "complete" });

    const { rerender } = renderWithRouter(<TaskCard task={task} />);
    expect(screen.getByText("写个复盘？")).toBeInTheDocument();

    await user.click(screen.getByText("跳过"));

    await waitFor(() => {
      expect(screen.queryByText("写个复盘？")).not.toBeInTheDocument();
    });

    // Rerender same task, should still not show
    rerender(
      <MemoryRouter>
        <TaskCard task={task} />
      </MemoryRouter>
    );
    expect(screen.queryByText("写个复盘？")).not.toBeInTheDocument();
  });
});
