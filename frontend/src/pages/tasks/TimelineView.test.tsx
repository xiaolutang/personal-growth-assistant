import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { TimelineView } from "./TimelineView";
import { OverdueBanner } from "./OverdueBanner";
import type { Task } from "@/types/task";

// Mock react-router-dom
vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
}));

// Mock taskStore
vi.mock("@/stores/taskStore", () => ({
  useTaskStore: (selector: (state: Record<string, unknown>) => unknown) => {
    const state = {
      updateTaskStatus: vi.fn(),
      deleteTask: vi.fn(),
      tasks: [],
    };
    return selector(state);
  },
}));

function createTask(overrides: Partial<Task> = {}): Task {
  return {
    id: `task-${Math.random().toString(36).slice(2, 8)}`,
    title: "测试任务",
    content: "",
    category: "task",
    status: "doing",
    tags: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    file_path: "tasks/test.md",
    ...overrides,
  };
}

describe("OverdueBanner", () => {
  it("当有逾期任务时显示提醒条", () => {
    render(<OverdueBanner count={3} />);
    expect(screen.getByTestId("overdue-banner")).toBeInTheDocument();
    expect(screen.getByText(/3 个任务已逾期/)).toBeInTheDocument();
  });

  it("逾期数量为 0 时不显示提醒条", () => {
    const { container } = render(<OverdueBanner count={0} />);
    expect(container.innerHTML).toBe("");
  });

  it("提醒条包含警告图标", () => {
    render(<OverdueBanner count={2} />);
    // Lucide AlertTriangle renders as an SVG
    const svg = screen.getByTestId("overdue-banner").querySelector("svg");
    expect(svg).toBeInTheDocument();
  });
});

describe("TimelineView", () => {
  const realDate = new Date("2026-04-30T12:00:00");

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(realDate);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("空任务列表显示空状态", () => {
    const { container } = render(<TimelineView tasks={[]} />);
    expect(container.querySelector('[data-testid="timeline-empty"]')).toBeTruthy();
  });

  it("按 planned_date 分组到正确的日期桶", () => {
    const today = "2026-04-30";
    const tomorrow = "2026-05-01";
    const yesterday = "2026-04-29";
    const nextWeek = "2026-05-06";

    const tasks = [
      createTask({ id: "t1", title: "逾期任务", planned_date: yesterday }),
      createTask({ id: "t2", title: "今天的任务", planned_date: today }),
      createTask({ id: "t3", title: "明天的任务", planned_date: tomorrow }),
      createTask({ id: "t4", title: "下周的任务", planned_date: nextWeek }),
    ];

    render(<TimelineView tasks={tasks} />);

    // 检查分组标题存在
    expect(screen.getByText("逾期")).toBeInTheDocument();
    expect(screen.getByText("今天")).toBeInTheDocument();
    expect(screen.getByText("明天")).toBeInTheDocument();
    expect(screen.getByText("下周")).toBeInTheDocument();
  });

  it("没有 planned_date 的任务归入「未安排」分组", () => {
    const tasks = [
      createTask({ id: "t1", title: "无日期任务" }),
    ];

    render(<TimelineView tasks={tasks} />);

    expect(screen.getByText("未安排")).toBeInTheDocument();
  });

  it("逾期条目有红色左边框样式", () => {
    const yesterday = "2026-04-29";
    const tasks = [
      createTask({ id: "t1", title: "逾期任务", planned_date: yesterday }),
    ];

    const { container } = render(<TimelineView tasks={tasks} />);

    // 逾期分组内的卡片应有红色左边框
    const overdueGroup = container.querySelector('[data-testid="timeline-group-overdue"]');
    expect(overdueGroup).toBeTruthy();
    const borderEl = overdueGroup!.querySelector('[data-testid="timeline-overdue-border"]');
    expect(borderEl).toBeTruthy();
    expect(borderEl!.className).toContain("border-l-4");
    expect(borderEl!.className).toContain("border-red-500");
  });

  it("本周内的任务正确分组（非今天/明天）", () => {
    // 2026-04-30 是周四，所以周五 5月1日是明天，周六 5月2日是「本周」
    const thisWeek = "2026-05-02";

    const tasks = [
      createTask({ id: "t1", title: "本周任务", planned_date: thisWeek }),
    ];

    render(<TimelineView tasks={tasks} />);

    expect(screen.getByText("本周")).toBeInTheDocument();
  });

  it("更远的日期归入「更远」分组", () => {
    const farFuture = "2026-06-15";

    const tasks = [
      createTask({ id: "t1", title: "远期任务", planned_date: farFuture }),
    ];

    render(<TimelineView tasks={tasks} />);

    expect(screen.getByText("更远")).toBeInTheDocument();
  });

  it("complete 状态的任务不计入逾期", () => {
    const yesterday = "2026-04-29";
    const tasks = [
      createTask({ id: "t1", title: "已完成任务", planned_date: yesterday, status: "complete" }),
    ];

    render(<TimelineView tasks={tasks} />);

    // 已完成任务不应出现在逾期组
    expect(screen.queryByText("逾期")).not.toBeInTheDocument();
    // 应该在「更远」或其他组中出现（已完成的日期在过去但已完成为安全日期）
    // 实际上已完成的任务 planned_date 在过去，但 status=complete 所以不应该算逾期
    // 它仍会按日期分组，但不显示为逾期
  });

  it("已取消的任务不显示在视图中", () => {
    const today = "2026-04-30";
    const tasks = [
      createTask({ id: "t1", title: "已取消", planned_date: today, status: "cancelled" }),
      createTask({ id: "t2", title: "进行中", planned_date: today, status: "doing" }),
    ];

    render(<TimelineView tasks={tasks} />);

    expect(screen.getByText("进行中")).toBeInTheDocument();
    expect(screen.queryByText("已取消")).not.toBeInTheDocument();
  });

  it("渲染 OverdueBanner 显示逾期数量", () => {
    const yesterday = "2026-04-29";
    const tasks = [
      createTask({ id: "t1", title: "逾期任务1", planned_date: yesterday }),
      createTask({ id: "t2", title: "逾期任务2", planned_date: "2026-04-28" }),
    ];

    render(<TimelineView tasks={tasks} />);

    expect(screen.getByTestId("overdue-banner")).toBeInTheDocument();
    expect(screen.getByText(/2 个任务已逾期/)).toBeInTheDocument();
  });

  it("无逾期时不显示 OverdueBanner", () => {
    const tomorrow = "2026-05-01";
    const tasks = [
      createTask({ id: "t1", title: "明天的任务", planned_date: tomorrow }),
    ];

    const { container } = render(<TimelineView tasks={tasks} />);

    expect(container.querySelector('[data-testid="overdue-banner"]')).toBeNull();
  });

  it("空分组不显示", () => {
    const today = "2026-04-30";
    const tasks = [
      createTask({ id: "t1", title: "今天的任务", planned_date: today }),
    ];

    render(<TimelineView tasks={tasks} />);

    expect(screen.getByText("今天")).toBeInTheDocument();
    expect(screen.queryByText("逾期")).not.toBeInTheDocument();
    expect(screen.queryByText("明天")).not.toBeInTheDocument();
    expect(screen.queryByText("下周")).not.toBeInTheDocument();
    expect(screen.queryByText("更远")).not.toBeInTheDocument();
    expect(screen.queryByText("未安排")).not.toBeInTheDocument();
  });

  it("decision 类型的任务也能正确渲染", () => {
    const today = "2026-04-30";
    const tasks = [
      createTask({ id: "t1", title: "决策任务", category: "decision", planned_date: today }),
    ];

    render(<TimelineView tasks={tasks} />);

    expect(screen.getByText("决策任务")).toBeInTheDocument();
  });
});
