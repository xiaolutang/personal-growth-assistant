import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { DecisionCard } from "../DecisionCard";
import type { Task } from "@/types/task";

// Mock sonner
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
  Toaster: () => null,
}));

// Mock taskStore
const mockUpdateEntry = vi.fn();
const mockCreateEntry = vi.fn();
const mockTasks: Task[] = [];

vi.mock("@/stores/taskStore", () => ({
  useTaskStore: (selector: (state: Record<string, unknown>) => unknown) => {
    const state = {
      updateEntry: mockUpdateEntry,
      createEntry: mockCreateEntry,
      tasks: mockTasks,
    };
    return selector(state);
  },
}));

import { toast } from "sonner";

function createDecision(overrides: Partial<Task> = {}): Task {
  return {
    id: "decision-001",
    title: "是否采用微服务架构",
    content: "当前单体架构面临扩展性问题，需要评估是否迁移到微服务架构。考虑因素包括团队规模、部署频率、服务边界等。",
    category: "decision",
    status: "doing",
    tags: ["架构"],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    file_path: "decisions/decision-001.md",
    ...overrides,
  };
}

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("DecisionCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ===== 未决定的 decision 显示三个操作按钮 =====
  describe("未决定状态", () => {
    it("显示标题和内容摘要", () => {
      renderWithRouter(<DecisionCard decision={createDecision()} />);
      expect(screen.getByText("是否采用微服务架构")).toBeInTheDocument();
      // 内容截断 2 行
      expect(screen.getByText(/当前单体架构面临扩展性问题/)).toBeInTheDocument();
    });

    it("显示三个操作按钮：决定 YES / 决定 NO / 延后", () => {
      renderWithRouter(<DecisionCard decision={createDecision()} />);
      expect(screen.getByRole("button", { name: /决定 YES/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /决定 NO/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /延后/i })).toBeInTheDocument();
    });

    it("内容摘要截断为 2 行", () => {
      const longContent = "A".repeat(500);
      const { container } = renderWithRouter(
        <DecisionCard decision={createDecision({ content: longContent })} />
      );
      const contentEl = container.querySelector("[data-testid='decision-content']");
      expect(contentEl).toBeInTheDocument();
      // line-clamp-2 class applied
      expect(contentEl?.className).toContain("line-clamp-2");
    });
  });

  // ===== 点击「决定 YES」弹出对话框 =====
  describe("决定 YES 流程", () => {
    it("点击「决定 YES」弹出 DecisionResultDialog", async () => {
      const user = userEvent.setup();
      renderWithRouter(<DecisionCard decision={createDecision()} />);

      await user.click(screen.getByRole("button", { name: /决定 YES/i }));

      // 对话框应出现
      expect(screen.getByText(/决策理由/)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /确认/i })).toBeInTheDocument();
    });

    it("确认后 status 改为 complete，content 追加决策结果", async () => {
      mockUpdateEntry.mockResolvedValueOnce(undefined);
      const user = userEvent.setup();
      renderWithRouter(<DecisionCard decision={createDecision()} />);

      await user.click(screen.getByRole("button", { name: /决定 YES/i }));

      // 输入理由
      const reasonInput = screen.getByPlaceholderText(/可选：输入决策理由/);
      await user.type(reasonInput, "团队规模扩大，需要独立部署");

      // 确认
      await user.click(screen.getByRole("button", { name: /确认/i }));

      // updateEntry 应被调用
      await waitFor(() => {
        expect(mockUpdateEntry).toHaveBeenCalledWith("decision-001", expect.objectContaining({
          status: "complete",
          content: expect.stringContaining("## 决策结果"),
        }));
      });
      // content 应包含 YES 和理由
      const callArgs = mockUpdateEntry.mock.calls[0][1];
      expect(callArgs.content).toContain("YES");
      expect(callArgs.content).toContain("团队规模扩大，需要独立部署");
    });

    it("不输入理由也可确认", async () => {
      mockUpdateEntry.mockResolvedValueOnce(undefined);
      const user = userEvent.setup();
      renderWithRouter(<DecisionCard decision={createDecision()} />);

      await user.click(screen.getByRole("button", { name: /决定 YES/i }));
      await user.click(screen.getByRole("button", { name: /确认/i }));

      await waitFor(() => {
        expect(mockUpdateEntry).toHaveBeenCalled();
      });
      const callArgs = mockUpdateEntry.mock.calls[0][1];
      expect(callArgs.content).toContain("YES");
    });
  });

  // ===== 勾选创建任务 =====
  describe("创建子任务", () => {
    it("勾选创建任务时显示任务标题输入框", async () => {
      const user = userEvent.setup();
      renderWithRouter(<DecisionCard decision={createDecision()} />);

      await user.click(screen.getByRole("button", { name: /决定 YES/i }));

      // 勾选创建任务
      const toggle = screen.getByRole("checkbox", { name: /同时创建任务/ });
      await user.click(toggle);

      expect(screen.getByPlaceholderText(/输入任务标题/)).toBeInTheDocument();
    });

    it("确认后创建 task 类型条目，parent_id 指向 decision 的 project", async () => {
      mockUpdateEntry.mockResolvedValueOnce(undefined);
      mockCreateEntry.mockResolvedValueOnce({ id: "new-task-1" } as Task);
      const user = userEvent.setup();

      // decision 有 parent_id 指向 project
      renderWithRouter(
        <DecisionCard decision={createDecision({ parent_id: "project-abc" })} />
      );

      await user.click(screen.getByRole("button", { name: /决定 YES/i }));

      // 勾选创建任务
      await user.click(screen.getByRole("checkbox", { name: /同时创建任务/ }));

      // 输入任务标题
      await user.type(screen.getByPlaceholderText(/输入任务标题/), "微服务拆分计划");

      // 确认
      await user.click(screen.getByRole("button", { name: /确认/i }));

      await waitFor(() => {
        // createEntry 应被调用，parent_id 为 decision 的 parent_id（project）
        expect(mockCreateEntry).toHaveBeenCalledWith(expect.objectContaining({
          type: "task",
          title: "微服务拆分计划",
          parent_id: "project-abc",
        }));
      });
    });

    it("decision 无 parent_id 时，子任务 parent_id 指向 decision 自身 id", async () => {
      mockUpdateEntry.mockResolvedValueOnce(undefined);
      mockCreateEntry.mockResolvedValueOnce({ id: "new-task-2" } as Task);
      const user = userEvent.setup();

      // decision 没有 parent_id
      renderWithRouter(
        <DecisionCard decision={createDecision({ parent_id: undefined })} />
      );

      await user.click(screen.getByRole("button", { name: /决定 YES/i }));
      await user.click(screen.getByRole("checkbox", { name: /同时创建任务/ }));
      await user.type(screen.getByPlaceholderText(/输入任务标题/), "评估报告");
      await user.click(screen.getByRole("button", { name: /确认/i }));

      await waitFor(() => {
        expect(mockCreateEntry).toHaveBeenCalledWith(expect.objectContaining({
          parent_id: "decision-001",
        }));
      });
    });
  });

  // ===== 已完成的 decision =====
  describe("已完成状态", () => {
    it("不显示操作按钮，显示决策结果文本", () => {
      const completedDecision = createDecision({
        status: "complete",
        content: "## 决策结果\n- **决定**: YES\n- **理由**: 团队已准备好\n\n原始背景描述",
      });
      renderWithRouter(<DecisionCard decision={completedDecision} />);

      // 不显示操作按钮
      expect(screen.queryByRole("button", { name: /决定 YES/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /决定 NO/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /延后/i })).not.toBeInTheDocument();

      // 显示决策结果
      expect(screen.getByText(/YES/)).toBeInTheDocument();
    });
  });

  // ===== 延后按钮 =====
  describe("延后操作", () => {
    it("直接将 status 改为 paused，不弹对话框", async () => {
      mockUpdateEntry.mockResolvedValueOnce(undefined);
      const user = userEvent.setup();
      renderWithRouter(<DecisionCard decision={createDecision()} />);

      await user.click(screen.getByRole("button", { name: /延后/i }));

      expect(mockUpdateEntry).toHaveBeenCalledWith("decision-001", expect.objectContaining({
        status: "paused",
      }));
      // 不应出现对话框
      expect(screen.queryByText(/决策理由/)).not.toBeInTheDocument();
    });
  });

  // ===== API 失败处理 =====
  describe("错误处理", () => {
    it("API 失败时 toast 提示错误，按钮保持可点击", async () => {
      mockUpdateEntry.mockRejectedValueOnce(new Error("API error"));
      const user = userEvent.setup();
      renderWithRouter(<DecisionCard decision={createDecision()} />);

      await user.click(screen.getByRole("button", { name: /决定 YES/i }));
      await user.click(screen.getByRole("button", { name: /确认/i }));

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalled();
      });

      // 对话框关闭后按钮仍可点击
      expect(screen.getByRole("button", { name: /决定 YES/i })).toBeInTheDocument();
    });

    it("决策完成成功但子任务创建失败：decision 状态已改，toast 提示子任务创建失败", async () => {
      mockUpdateEntry.mockResolvedValueOnce(undefined);
      mockCreateEntry.mockRejectedValueOnce(new Error("Create task failed"));
      const user = userEvent.setup();

      renderWithRouter(
        <DecisionCard decision={createDecision({ parent_id: "project-abc" })} />
      );

      await user.click(screen.getByRole("button", { name: /决定 YES/i }));
      await user.click(screen.getByRole("checkbox", { name: /同时创建任务/ }));
      await user.type(screen.getByPlaceholderText(/输入任务标题/), "新任务");
      await user.click(screen.getByRole("button", { name: /确认/i }));

      await waitFor(() => {
        // decision 状态更新应该已调用
        expect(mockUpdateEntry).toHaveBeenCalled();
        // 子任务创建失败应 toast 提示
        expect(toast.error).toHaveBeenCalledWith("子任务创建失败，请手动创建");
      });
    });
  });

  // ===== 与 TaskCard 共存 =====
  describe("DecisionCard 与 TaskCard 共存", () => {
    it("DecisionCard 具有 decision 类别标识", () => {
      const { container } = renderWithRouter(<DecisionCard decision={createDecision()} />);
      expect(container.querySelector("[data-category='decision']")).toBeInTheDocument();
    });
  });
});
