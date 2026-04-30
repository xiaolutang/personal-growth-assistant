import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { ProjectCard } from "../ProjectCard";
import type { Task } from "@/types/task";

// Mock sonner
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
  Toaster: () => null,
}));

// Mock api - getProjectProgress
const mockGetProjectProgress = vi.fn();
vi.mock("@/services/api", () => ({
  getProjectProgress: (...args: string[]) => mockGetProjectProgress(...args),
}));

// Mock taskStore
const mockTasks: Task[] = [];

vi.mock("@/stores/taskStore", () => ({
  useTaskStore: (selector: (state: Record<string, unknown>) => unknown) => {
    const state = {
      tasks: mockTasks,
    };
    return selector(state);
  },
}));

function createProject(overrides: Partial<Task> = {}): Task {
  return {
    id: "project-001",
    title: "个人成长助手",
    content: "一个帮助个人成长的工具",
    category: "project",
    status: "doing",
    tags: ["项目"],
    created_at: "2025-04-20T10:00:00Z",
    updated_at: "2025-04-28T15:30:00Z",
    file_path: "projects/project-001.md",
    ...overrides,
  };
}

function createSubTask(overrides: Partial<Task> = {}): Task {
  return {
    id: "task-001",
    title: "完成首页设计",
    content: "",
    category: "task",
    status: "complete",
    tags: [],
    created_at: "2025-04-21T10:00:00Z",
    updated_at: "2025-04-22T10:00:00Z",
    file_path: "tasks/task-001.md",
    parent_id: "project-001",
    ...overrides,
  };
}

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("ProjectCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // 默认 mock 返回进度数据
    mockGetProjectProgress.mockResolvedValue({
      project_id: "project-001",
      total_tasks: 7,
      completed_tasks: 3,
      progress_percentage: 43,
      status_distribution: { complete: 3, doing: 2, waitStart: 1, paused: 1 },
    });
    // 清空 mockTasks
    mockTasks.length = 0;
  });

  // ===== 基础渲染 =====
  describe("基础渲染", () => {
    it("显示项目标题", async () => {
      renderWithRouter(<ProjectCard project={createProject()} />);
      expect(screen.getByText("个人成长助手")).toBeInTheDocument();
    });

    it("显示最近更新时间", async () => {
      renderWithRouter(<ProjectCard project={createProject()} />);
      // 更新时间应该在页面上以某种格式显示
      await waitFor(() => {
        expect(mockGetProjectProgress).toHaveBeenCalledWith("project-001");
      });
    });

    it("调用 getProjectProgress API 获取进度数据", async () => {
      renderWithRouter(<ProjectCard project={createProject()} />);
      await waitFor(() => {
        expect(mockGetProjectProgress).toHaveBeenCalledWith("project-001");
      });
    });

    it("显示进度条（X/Y 完成）", async () => {
      renderWithRouter(<ProjectCard project={createProject()} />);
      await waitFor(() => {
        expect(screen.getByText(/3\/7/)).toBeInTheDocument();
      });
    });

    it("显示百分比进度", async () => {
      renderWithRouter(<ProjectCard project={createProject()} />);
      await waitFor(() => {
        expect(screen.getByText(/43%/)).toBeInTheDocument();
      });
    });

    it("data-category 属性为 project", async () => {
      const { container } = renderWithRouter(<ProjectCard project={createProject()} />);
      expect(container.querySelector("[data-category='project']")).toBeInTheDocument();
    });
  });

  // ===== 进度条颜色 =====
  describe("进度条颜色", () => {
    it("完成 >80% 显示绿色", async () => {
      mockGetProjectProgress.mockResolvedValue({
        project_id: "project-001",
        total_tasks: 10,
        completed_tasks: 9,
        progress_percentage: 90,
        status_distribution: {},
      });
      renderWithRouter(<ProjectCard project={createProject()} />);
      await waitFor(() => {
        const bar = screen.getByTestId("progress-bar-fill");
        expect(bar.className).toContain("bg-green-500");
      });
    });

    it("完成 30-80% 显示蓝色", async () => {
      mockGetProjectProgress.mockResolvedValue({
        project_id: "project-001",
        total_tasks: 10,
        completed_tasks: 5,
        progress_percentage: 50,
        status_distribution: {},
      });
      renderWithRouter(<ProjectCard project={createProject()} />);
      await waitFor(() => {
        const bar = screen.getByTestId("progress-bar-fill");
        expect(bar.className).toContain("bg-blue-500");
      });
    });

    it("完成 <30% 显示灰色", async () => {
      mockGetProjectProgress.mockResolvedValue({
        project_id: "project-001",
        total_tasks: 10,
        completed_tasks: 2,
        progress_percentage: 20,
        status_distribution: {},
      });
      renderWithRouter(<ProjectCard project={createProject()} />);
      await waitFor(() => {
        const bar = screen.getByTestId("progress-bar-fill");
        expect(bar.className).toContain("bg-gray-400");
      });
    });

    it("子任务全部完成后进度条变绿显示 100%", async () => {
      mockGetProjectProgress.mockResolvedValue({
        project_id: "project-001",
        total_tasks: 5,
        completed_tasks: 5,
        progress_percentage: 100,
        status_distribution: {},
      });
      renderWithRouter(<ProjectCard project={createProject()} />);
      await waitFor(() => {
        const bar = screen.getByTestId("progress-bar-fill");
        expect(bar.className).toContain("bg-green-500");
        expect(screen.getByText(/100%/)).toBeInTheDocument();
        expect(screen.getByText(/5\/5/)).toBeInTheDocument();
      });
    });
  });

  // ===== 展开/折叠子任务 =====
  describe("展开子任务", () => {
    it("点击 ProjectCard 展开子任务列表", async () => {
      const user = userEvent.setup();
      // 在 store 中放入子任务
      mockTasks.push(
        createSubTask({ id: "t1", title: "任务1", status: "complete", parent_id: "project-001" }),
        createSubTask({ id: "t2", title: "任务2", status: "doing", parent_id: "project-001" }),
      );
      renderWithRouter(<ProjectCard project={createProject()} />);

      // 等待进度加载
      await waitFor(() => {
        expect(mockGetProjectProgress).toHaveBeenCalled();
      });

      // 点击展开
      const expandBtn = screen.getByTestId("expand-toggle");
      await user.click(expandBtn);

      // 应显示子任务
      expect(screen.getByText("任务1")).toBeInTheDocument();
      expect(screen.getByText("任务2")).toBeInTheDocument();
    });

    it("再次点击折叠子任务列表", async () => {
      const user = userEvent.setup();
      mockTasks.push(
        createSubTask({ id: "t1", title: "任务1", parent_id: "project-001" }),
      );
      renderWithRouter(<ProjectCard project={createProject()} />);

      await waitFor(() => {
        expect(mockGetProjectProgress).toHaveBeenCalled();
      });

      // 展开再折叠
      const expandBtn = screen.getByTestId("expand-toggle");
      await user.click(expandBtn);
      expect(screen.getByText("任务1")).toBeInTheDocument();

      await user.click(expandBtn);
      expect(screen.queryByText("任务1")).not.toBeInTheDocument();
    });
  });

  // ===== 空状态 =====
  describe("无子任务", () => {
    it("无子任务的 project 显示「暂无子任务」", async () => {
      mockGetProjectProgress.mockResolvedValue({
        project_id: "project-001",
        total_tasks: 0,
        completed_tasks: 0,
        progress_percentage: 0,
        status_distribution: {},
      });
      const user = userEvent.setup();
      renderWithRouter(<ProjectCard project={createProject()} />);

      await waitFor(() => {
        expect(mockGetProjectProgress).toHaveBeenCalled();
      });

      // 展开查看
      const expandBtn = screen.getByTestId("expand-toggle");
      await user.click(expandBtn);

      expect(screen.getByText("暂无子任务")).toBeInTheDocument();
    });
  });

  // ===== API 失败降级 =====
  describe("API 失败降级", () => {
    it("进度 API 返回 5xx 时降级显示", async () => {
      mockGetProjectProgress.mockRejectedValue(new Error("Internal Server Error"));
      renderWithRouter(<ProjectCard project={createProject()} />);

      await waitFor(() => {
        expect(mockGetProjectProgress).toHaveBeenCalled();
      });

      // 卡片标题仍然显示
      expect(screen.getByText("个人成长助手")).toBeInTheDocument();
      // 进度条显示灰色「加载失败」
      expect(screen.getByText("加载失败")).toBeInTheDocument();
      const bar = screen.getByTestId("progress-bar-fill");
      expect(bar.className).toContain("bg-gray-300");
    });
  });

  // ===== 已加载不一致标注 =====
  describe("已加载不一致标注", () => {
    it("前端已加载子任务数与 API 总数不一致时标注「已加载 N 条」", async () => {
      // API 返回 7 个任务
      mockGetProjectProgress.mockResolvedValue({
        project_id: "project-001",
        total_tasks: 7,
        completed_tasks: 3,
        progress_percentage: 43,
        status_distribution: {},
      });
      // 但 store 中只有 2 个子任务
      mockTasks.push(
        createSubTask({ id: "t1", title: "任务1", parent_id: "project-001" }),
        createSubTask({ id: "t2", title: "任务2", parent_id: "project-001" }),
      );

      const user = userEvent.setup();
      renderWithRouter(<ProjectCard project={createProject()} />);

      await waitFor(() => {
        expect(mockGetProjectProgress).toHaveBeenCalled();
      });

      // 展开子任务
      const expandBtn = screen.getByTestId("expand-toggle");
      await user.click(expandBtn);

      // 应该显示「已加载 2 条」
      expect(screen.getByText(/已加载 2 条/)).toBeInTheDocument();
    });
  });

  // ===== 布局模式 =====
  describe("布局模式", () => {
    it("compact 模式下渲染为紧凑行布局", async () => {
      const { container } = renderWithRouter(
        <ProjectCard project={createProject()} layout="compact" />
      );
      await waitFor(() => {
        expect(mockGetProjectProgress).toHaveBeenCalled();
      });
      expect(container.querySelector("[data-layout='compact']")).toBeInTheDocument();
    });

    it("grid 模式下渲染为卡片布局", async () => {
      const { container } = renderWithRouter(
        <ProjectCard project={createProject()} layout="grid" />
      );
      await waitFor(() => {
        expect(mockGetProjectProgress).toHaveBeenCalled();
      });
      expect(container.querySelector("[data-layout='grid']")).toBeInTheDocument();
    });
  });

  // ===== 可选择模式 =====
  describe("可选择模式", () => {
    it("selectable 模式下点击卡片触发 onSelect", async () => {
      const onSelect = vi.fn();
      const user = userEvent.setup();
      renderWithRouter(
        <ProjectCard project={createProject()} selectable onSelect={onSelect} />
      );

      await waitFor(() => {
        expect(mockGetProjectProgress).toHaveBeenCalled();
      });

      // 点击卡片主体
      const card = screen.getByTestId("project-card-body");
      await user.click(card);
      expect(onSelect).toHaveBeenCalledWith("project-001");
    });
  });
});
