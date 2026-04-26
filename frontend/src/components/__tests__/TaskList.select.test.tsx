/**
 * F143: TaskList multi-select integration tests
 * - selectable/selectable props passed to TaskCard
 * - disableActions passed through
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TaskList } from "../TaskList";
import type { Task } from "@/types/task";

// Mock react-router-dom
vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
}));

// Mock taskStore
vi.mock("@/stores/taskStore", () => ({
  useTaskStore: (selector: (s: any) => any) =>
    selector({
      deleteTask: vi.fn(),
      updateTaskStatus: vi.fn(),
      updateEntry: vi.fn(),
      tasks: [],
    }),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const makeTask = (overrides: Partial<Task> = {}): Task => ({
  id: "t1",
  title: "Test Task",
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

describe("TaskList multi-select (F143)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("passes selectable, selectedIds, onSelect, disableActions to TaskCard", () => {
    const tasks = [makeTask({ id: "a" }), makeTask({ id: "b", title: "Task B" })];
    const selectedIds = new Set(["a"]);
    const onSelect = vi.fn();

    render(
      <TaskList
        tasks={tasks}
        selectable={true}
        selectedIds={selectedIds}
        onSelect={onSelect}
        disableActions={true}
      />
    );

    // Both tasks rendered
    expect(screen.getByText("Test Task")).toBeTruthy();
    expect(screen.getByText("Task B")).toBeTruthy();

    // Clicking on "a" triggers onSelect
    fireEvent.click(screen.getByText("Test Task"));
    expect(onSelect).toHaveBeenCalledWith("a");
  });

  it("clicking unselected task calls onSelect with its id", () => {
    const tasks = [makeTask({ id: "a" }), makeTask({ id: "b", title: "Task B" })];
    const selectedIds = new Set<string>();
    const onSelect = vi.fn();

    render(
      <TaskList
        tasks={tasks}
        selectable={true}
        selectedIds={selectedIds}
        onSelect={onSelect}
      />
    );

    fireEvent.click(screen.getByText("Task B"));
    expect(onSelect).toHaveBeenCalledWith("b");
  });

  it("renders empty state when no tasks", () => {
    render(<TaskList tasks={[]} emptyMessage="暂无内容" />);
    expect(screen.getByText("暂无内容")).toBeTruthy();
  });

  it("disableActions=true disables status toggle buttons", () => {
    const tasks = [makeTask({ id: "a" })];
    render(
      <TaskList
        tasks={tasks}
        selectable={true}
        selectedIds={new Set()}
        onSelect={vi.fn()}
        disableActions={true}
      />
    );
    const statusBtn = screen.getByLabelText("切换状态");
    expect(statusBtn).toBeDisabled();
  });
});
