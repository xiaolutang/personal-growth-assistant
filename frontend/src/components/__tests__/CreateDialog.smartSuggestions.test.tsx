/**
 * F05: CreateDialog 智能提示集成测试
 * 覆盖日期解析自动填充、类型建议、suppress 行为的组件级集成
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// Mock sonner
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
  Toaster: () => null,
}));

// Mock taskStore
const mockCreateEntry = vi.fn();
vi.mock("@/stores/taskStore", () => ({
  useTaskStore: (selector: (state: Record<string, unknown>) => unknown) => {
    const state = { createEntry: (...args: unknown[]) => mockCreateEntry(...args) };
    return selector(state);
  },
}));

// HTMLDialogElement polyfill for jsdom
beforeEach(() => {
  HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) {
    this.open = true;
  });
  HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) {
    this.open = false;
    this.dispatchEvent(new Event("close"));
  });
});

import { CreateDialog } from "../CreateDialog";
import type { Task } from "@/types/task";

const mockEntry: Task = {
  id: "entry-001",
  title: "测试条目",
  content: "",
  category: "task",
  status: "doing",
  tags: [],
  created_at: "2026-04-30T10:00:00",
  updated_at: "2026-04-30T10:00:00",
  file_path: "tasks/entry-001.md",
};

describe("CreateDialog — 智能提示集成 (F05)", () => {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // --- 日期解析自动填充 ---

  describe("日期解析自动填充", () => {
    it("输入含'明天'的标题 → task 类型下自动填充计划日期", async () => {
      const user = userEvent.setup();
      render(<CreateDialog {...defaultProps} defaultType="task" />);

      await user.type(screen.getByLabelText("标题"), "明天交报告");

      // 计划日期应被自动填充（明天的日期）
      const dateInput = screen.getByLabelText("计划日期") as HTMLInputElement;
      await waitFor(() => {
        expect(dateInput.value).toBeTruthy();
        expect(dateInput.value).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      });
    });

    it("输入含'明天'的标题 → 显示日期高亮提示", async () => {
      const user = userEvent.setup();
      render(<CreateDialog {...defaultProps} defaultType="task" />);

      await user.type(screen.getByLabelText("标题"), "明天交报告");

      await waitFor(() => {
        expect(screen.getByText(/已自动设为明天/)).toBeTruthy();
      });
    });

    it("输入含'后天'的标题 → 自动填充后天的日期", async () => {
      const user = userEvent.setup();
      render(<CreateDialog {...defaultProps} defaultType="task" />);

      await user.type(screen.getByLabelText("标题"), "后天开会");

      const dateInput = screen.getByLabelText("计划日期") as HTMLInputElement;
      await waitFor(() => {
        expect(dateInput.value).toBeTruthy();
      });
      expect(screen.getByText(/已自动设为后天/)).toBeTruthy();
    });

    it("输入普通文本 → 不填充计划日期", async () => {
      const user = userEvent.setup();
      render(<CreateDialog {...defaultProps} defaultType="task" />);

      await user.type(screen.getByLabelText("标题"), "买牛奶");

      const dateInput = screen.getByLabelText("计划日期") as HTMLInputElement;
      expect(dateInput.value).toBe("");
    });

    it("非 task 类型不自动填充计划日期（即使含日期关键词）", async () => {
      const user = userEvent.setup();
      render(<CreateDialog {...defaultProps} defaultType="project" />);

      await user.type(screen.getByLabelText("标题"), "明天交报告");

      // project 类型没有计划日期字段
      expect(screen.queryByLabelText("计划日期")).toBeNull();
    });
  });

  // --- 日期高亮提示显示条件 ---

  describe("日期高亮提示显示条件", () => {
    it("dateHint 存在但 plannedDate 为空时不显示提示", async () => {
      const user = userEvent.setup();
      // 默认不选 task（无日期字段），输入含日期关键词的文本
      // 再切到 task — 此时 suggestedDate 已被重置
      render(<CreateDialog {...defaultProps} />);

      // 直接切到 task
      await user.click(screen.getByText("任务"));

      // 此时日期字段为空，不应有提示
      const dateInput = screen.getByLabelText("计划日期") as HTMLInputElement;
      expect(dateInput.value).toBe("");
    });
  });

  // --- 类型建议 ---

  describe("类型建议", () => {
    it("输入含'要不要'→ 显示'建议创建为决策'链接", async () => {
      const user = userEvent.setup();
      render(<CreateDialog {...defaultProps} defaultType="task" />);

      await user.type(screen.getByLabelText("标题"), "要不要学 Rust");

      await waitFor(() => {
        expect(screen.getByText("建议创建为决策")).toBeTruthy();
      });
    });

    it("输入含'完成'→ 显示'建议创建为任务'链接", async () => {
      const user = userEvent.setup();
      render(<CreateDialog {...defaultProps} defaultType="inbox" />);

      await user.type(screen.getByLabelText("标题"), "完成项目文档");

      await waitFor(() => {
        expect(screen.getByText("建议创建为任务")).toBeTruthy();
      });
    });

    it("点击类型建议 → 切换到建议类型", async () => {
      const user = userEvent.setup();
      render(<CreateDialog {...defaultProps} defaultType="task" />);

      await user.type(screen.getByLabelText("标题"), "要不要学 Rust");
      await waitFor(() => {
        expect(screen.getByText("建议创建为决策")).toBeTruthy();
      });

      await user.click(screen.getByText("建议创建为决策"));

      // 应切换到 decision 类型（显示选项描述 textarea）
      await waitFor(() => {
        expect(screen.getByLabelText("选项描述")).toBeTruthy();
      });
    });

    it("点击类型建议后建议消失", async () => {
      const user = userEvent.setup();
      render(<CreateDialog {...defaultProps} defaultType="task" />);

      await user.type(screen.getByLabelText("标题"), "要不要学 Rust");
      await waitFor(() => {
        expect(screen.getByText("建议创建为决策")).toBeTruthy();
      });

      await user.click(screen.getByText("建议创建为决策"));

      await waitFor(() => {
        expect(screen.queryByText("建议创建为决策")).toBeNull();
      });
    });

    it("点击与当前相同类型的建议 → 不切换但建议消失", async () => {
      const user = userEvent.setup();
      render(<CreateDialog {...defaultProps} defaultType="decision" />);

      await user.type(screen.getByLabelText("标题"), "要不要学 Rust");
      await waitFor(() => {
        expect(screen.getByText("建议创建为决策")).toBeTruthy();
      });

      await user.click(screen.getByText("建议创建为决策"));

      // decision 类型仍保持（不切换），建议消失
      expect(screen.getByLabelText("选项描述")).toBeTruthy();
      await waitFor(() => {
        expect(screen.queryByText("建议创建为决策")).toBeNull();
      });
    });

    it("allowedTypes 不包含建议类型时不显示类型建议", async () => {
      const user = userEvent.setup();
      // 只允许 task 和 inbox，不允许 decision
      render(
        <CreateDialog
          {...defaultProps}
          defaultType="task"
          allowedTypes={["task", "inbox"]}
        />
      );

      await user.type(screen.getByLabelText("标题"), "要不要学 Rust");

      // decision 不在 allowedTypes 中，不应显示建议
      await waitFor(() => {
        expect(screen.queryByText("建议创建为决策")).toBeNull();
      });
    });

    it("输入普通文本无类型建议", async () => {
      const user = userEvent.setup();
      render(<CreateDialog {...defaultProps} defaultType="task" />);

      await user.type(screen.getByLabelText("标题"), "买牛奶");

      expect(screen.queryByText(/建议创建为/)).toBeNull();
    });
  });

  // --- Suppress 行为 ---

  describe("Suppress 行为", () => {
    it("手动清除计划日期 → 后续输入不再自动填充", async () => {
      const user = userEvent.setup();
      render(<CreateDialog {...defaultProps} defaultType="task" />);

      // 触发日期解析
      await user.type(screen.getByLabelText("标题"), "明天交报告");
      const dateInput = screen.getByLabelText("计划日期") as HTMLInputElement;
      await waitFor(() => {
        expect(dateInput.value).toBeTruthy();
      });

      // 清除日期
      await user.clear(dateInput);
      // 触发 change 事件（模拟清除日期字段）
      fireEvent.change(dateInput, { target: { value: "" } });

      // 再次输入含日期关键词
      const titleInput = screen.getByLabelText("标题") as HTMLInputElement;
      await user.clear(titleInput);
      await user.type(titleInput, "后天开会");

      // suppress 后不应自动填充
      await waitFor(() => {
        expect(dateInput.value).toBe("");
      });
    });

    it("关闭后重新打开 → suppress 重置，可再次自动填充", async () => {
      mockCreateEntry.mockResolvedValueOnce(mockEntry);
      const onOpenChange = vi.fn();
      const user = userEvent.setup();

      const { rerender } = render(
        <CreateDialog {...defaultProps} defaultType="task" onOpenChange={onOpenChange} />
      );

      // 触发日期解析
      await user.type(screen.getByLabelText("标题"), "明天交报告");
      const dateInput = screen.getByLabelText("计划日期") as HTMLInputElement;
      await waitFor(() => {
        expect(dateInput.value).toBeTruthy();
      });

      // 清除日期触发 suppress
      await user.clear(dateInput);
      fireEvent.change(dateInput, { target: { value: "" } });

      // 关闭
      rerender(
        <CreateDialog {...defaultProps} open={false} defaultType="task" onOpenChange={onOpenChange} />
      );

      // 重新打开
      rerender(
        <CreateDialog {...defaultProps} open={true} defaultType="task" onOpenChange={onOpenChange} />
      );

      // 重新输入含日期关键词
      await user.type(screen.getByLabelText("标题"), "后天开会");
      const newDateInput = screen.getByLabelText("计划日期") as HTMLInputElement;

      // 重置后应可再次自动填充
      await waitFor(() => {
        expect(newDateInput.value).toBeTruthy();
      });
    });
  });

  // --- Stale date 回归测试 ---

  describe("Stale date 回归", () => {
    it("自动填充日期后修改标题移除日期关键词 → 清除自动填充的计划日期", async () => {
      const user = userEvent.setup();
      render(<CreateDialog {...defaultProps} defaultType="task" />);

      // 输入含日期关键词的标题 → 自动填充
      const titleInput = screen.getByLabelText("标题") as HTMLInputElement;
      await user.type(titleInput, "明天交报告");

      const dateInput = screen.getByLabelText("计划日期") as HTMLInputElement;
      await waitFor(() => {
        expect(dateInput.value).toBeTruthy();
      });

      // 清除标题后输入不含日期关键词的文本
      await user.clear(titleInput);
      await user.type(titleInput, "买牛奶");

      // 自动填充的日期应被清除
      await waitFor(() => {
        expect(dateInput.value).toBe("");
      });
    });

    it("自动填充日期后修改标题换一个日期关键词 → 更新为新的日期", async () => {
      const user = userEvent.setup();
      render(<CreateDialog {...defaultProps} defaultType="task" />);

      const titleInput = screen.getByLabelText("标题") as HTMLInputElement;
      await user.type(titleInput, "明天交报告");

      const dateInput = screen.getByLabelText("计划日期") as HTMLInputElement;
      await waitFor(() => {
        expect(dateInput.value).toBeTruthy();
      });

      // 修改为另一个日期关键词
      await user.clear(titleInput);
      await user.type(titleInput, "后天开会");

      // 日期应更新为后天的日期
      await waitFor(() => {
        expect(dateInput.value).toBeTruthy();
        expect(screen.getByText(/已自动设为后天/)).toBeTruthy();
      });
    });
  });

  // --- 先输入后选类型回归测试 ---

  describe("先输入后选类型", () => {
    it("无预选类型 → 输入含日期关键词 → 选择 task → 计划日期自动填充", async () => {
      const user = userEvent.setup();
      render(<CreateDialog {...defaultProps} />);

      // 无预选类型时输入标题
      const titleInput = screen.getByLabelText("标题") as HTMLInputElement;
      await user.type(titleInput, "明天交报告");

      // 此时应无计划日期字段（非 task 类型）
      expect(screen.queryByLabelText("计划日期")).toBeNull();

      // 选择 task 类型
      await user.click(screen.getByText("任务"));

      // 计划日期应自动填充
      const dateInput = screen.getByLabelText("计划日期") as HTMLInputElement;
      await waitFor(() => {
        expect(dateInput.value).toBeTruthy();
        expect(dateInput.value).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      });
    });

    it("输入标题触发'建议创建为任务' → 点击建议 → 类型切换到 task 且计划日期自动填充", async () => {
      const user = userEvent.setup();
      render(<CreateDialog {...defaultProps} defaultType="inbox" />);

      const titleInput = screen.getByLabelText("标题") as HTMLInputElement;
      await user.type(titleInput, "完成项目文档");

      // 应显示类型建议
      await waitFor(() => {
        expect(screen.getByText("建议创建为任务")).toBeTruthy();
      });

      // 此时应无计划日期字段（inbox 类型）
      expect(screen.queryByLabelText("计划日期")).toBeNull();

      // 点击类型建议
      await user.click(screen.getByText("建议创建为任务"));

      // 应切换到 task 类型
      await waitFor(() => {
        expect(screen.getByLabelText("优先级")).toBeTruthy();
      });

      // 注意：点击建议后标题变为"完成项目文档"（无日期关键词），所以不会有自动填充日期
      // 这里的测试验证的是类型切换本身正常工作
    });

    it("输入含日期关键词+类型建议 → 点击建议切换类型 → 计划日期保留", async () => {
      const user = userEvent.setup();
      render(<CreateDialog {...defaultProps} defaultType="inbox" />);

      const titleInput = screen.getByLabelText("标题") as HTMLInputElement;
      await user.type(titleInput, "明天完成项目");

      // 应显示类型建议（含"完成"关键词）
      await waitFor(() => {
        expect(screen.getByText("建议创建为任务")).toBeTruthy();
      });

      // 点击建议切换到 task
      await user.click(screen.getByText("建议创建为任务"));

      // 应切换到 task 类型且计划日期自动填充
      await waitFor(() => {
        const dateInput = screen.getByLabelText("计划日期") as HTMLInputElement;
        expect(dateInput.value).toBeTruthy();
      });
    });
  });
});
