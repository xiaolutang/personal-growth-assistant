/**
 * F08: GroupedView component tests
 * - Groups entries by parent_id
 * - Project entries shown as group headers with progress
 * - No parent_id entries grouped into "独立任务"
 * - Group headers are expandable/collapsible
 * - Decision entries correctly grouped under their parent project
 * - Empty state when no tasks
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { GroupedView } from "../GroupedView";
import { useTaskStore } from "@/stores/taskStore";
import { resetStore, createMockTask } from "@/testUtils/taskStoreHelpers";

// Mock API for ProjectCard's getProjectProgress
vi.mock("@/services/api", () => ({
  getEntries: vi.fn().mockResolvedValue({ entries: [] }),
  createEntry: vi.fn(),
  updateEntry: vi.fn(),
  deleteEntry: vi.fn(),
  searchEntries: vi.fn(),
  getKnowledgeGraph: vi.fn(),
  getProjectProgress: vi.fn().mockResolvedValue({
    total_tasks: 0,
    completed_tasks: 0,
    progress_percentage: 0,
  }),
}));

// Mock react-router-dom
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  };
});

beforeEach(() => {
  resetStore();
  vi.clearAllMocks();
});

describe("F08: GroupedView - grouping logic", () => {
  it("shows empty message when no tasks", () => {
    render(<GroupedView tasks={[]} />);
    expect(screen.getByText("暂无任务")).toBeInTheDocument();
  });

  it("groups tasks under their parent project", () => {
    const project = createMockTask({ id: "p1", title: "我的项目", category: "project" });
    const task1 = createMockTask({ id: "t1", title: "子任务1", parent_id: "p1", category: "task" });
    const task2 = createMockTask({ id: "t2", title: "子任务2", parent_id: "p1", category: "task" });

    useTaskStore.setState({ tasks: [project, task1, task2] });

    render(<GroupedView tasks={[project, task1, task2]} />);
    // Project header should be visible
    expect(screen.getByText("我的项目")).toBeInTheDocument();
    // Sub-tasks should be visible (inside the group)
    expect(screen.getByText("子任务1")).toBeInTheDocument();
    expect(screen.getByText("子任务2")).toBeInTheDocument();
  });

  it("groups entries without parent_id into 独立任务", () => {
    const task1 = createMockTask({ id: "t1", title: "独立任务1", category: "task" });
    const task2 = createMockTask({ id: "t2", title: "独立任务2", category: "task" });

    render(<GroupedView tasks={[task1, task2]} />);

    expect(screen.getByText("独立任务")).toBeInTheDocument();
    expect(screen.getByText("独立任务1")).toBeInTheDocument();
    expect(screen.getByText("独立任务2")).toBeInTheDocument();
  });

  it("decision entries are correctly grouped under parent project", () => {
    const project = createMockTask({ id: "p1", title: "决策项目", category: "project" });
    const decision = createMockTask({ id: "d1", title: "重要决策", parent_id: "p1", category: "decision" });

    useTaskStore.setState({ tasks: [project, decision] });

    render(<GroupedView tasks={[project, decision]} />);
    expect(screen.getByText("决策项目")).toBeInTheDocument();
    expect(screen.getByText("重要决策")).toBeInTheDocument();
  });

  it("shows mixed groups: project groups and 独立任务", () => {
    const project = createMockTask({ id: "p1", title: "项目A", category: "project" });
    const subTask = createMockTask({ id: "t1", title: "子任务A1", parent_id: "p1" });
    const standalone = createMockTask({ id: "t2", title: "游离任务" });

    useTaskStore.setState({ tasks: [project, subTask, standalone] });

    render(<GroupedView tasks={[project, subTask, standalone]} />);

    expect(screen.getByText("项目A")).toBeInTheDocument();
    expect(screen.getByText("子任务A1")).toBeInTheDocument();
    // "独立任务" is the group header for items without parent_id
    expect(screen.getByText("独立任务")).toBeInTheDocument();
    // The standalone task itself
    expect(screen.getByText("游离任务")).toBeInTheDocument();
  });
});

describe("F08: GroupedView - expand/collapse", () => {
  it("group headers are expandable/collapsible", () => {
    const project = createMockTask({ id: "p1", title: "项目B", category: "project" });
    const subTask = createMockTask({ id: "t1", title: "子任务B1", parent_id: "p1" });

    useTaskStore.setState({ tasks: [project, subTask] });

    render(<GroupedView tasks={[project, subTask]} />);

    // Initially expanded by default, sub-task should be visible
    expect(screen.getByText("子任务B1")).toBeInTheDocument();

    // Find and click the collapse toggle for this group
    const toggleButtons = screen.getAllByTestId("grouped-view-toggle");
    const projectToggle = toggleButtons[0];
    fireEvent.click(projectToggle);

    // After collapsing, sub-task should not be visible
    expect(screen.queryByText("子任务B1")).not.toBeInTheDocument();

    // Click again to expand
    fireEvent.click(projectToggle);
    expect(screen.getByText("子任务B1")).toBeInTheDocument();
  });
});
