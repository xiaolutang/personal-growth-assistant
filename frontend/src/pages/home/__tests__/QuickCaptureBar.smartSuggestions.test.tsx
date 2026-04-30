/**
 * F05: QuickCaptureBar 智能提示集成测试
 * 覆盖展开模式日期解析自动填充、日期高亮提示、suppress 行为
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

// Mock CreateDialog — 避免加载完整组件
vi.mock("@/components/CreateDialog", () => ({
  CreateDialog: ({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) => (
    <div data-testid="create-dialog" data-open={open}>
      <button onClick={() => onOpenChange(false)}>关闭Dialog</button>
    </div>
  ),
}));

import { QuickCaptureBar } from "../QuickCaptureBar";
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

describe("QuickCaptureBar — 智能提示集成 (F05)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // --- 展开模式日期解析 ---

  describe("展开模式日期解析", () => {
    it("展开模式下输入含'明天'的标题 → 自动填充计划日期", async () => {
      const user = userEvent.setup();
      render(<QuickCaptureBar />);

      await user.click(screen.getByLabelText("展开更多选项"));
      const input = screen.getByPlaceholderText("记录灵感或任务...");
      await user.type(input, "明天交报告");

      const dateInput = screen.getByLabelText("计划日期") as HTMLInputElement;
      await waitFor(() => {
        expect(dateInput.value).toBeTruthy();
        expect(dateInput.value).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      });
    });

    it("展开模式下输入含'明天'的标题 → 显示日期高亮提示", async () => {
      const user = userEvent.setup();
      render(<QuickCaptureBar />);

      await user.click(screen.getByLabelText("展开更多选项"));
      const input = screen.getByPlaceholderText("记录灵感或任务...");
      await user.type(input, "明天交报告");

      await waitFor(() => {
        expect(screen.getByText(/已自动设为明天/)).toBeTruthy();
      });
    });

    it("展开模式下输入含'后天'的标题 → 自动填充后天日期", async () => {
      const user = userEvent.setup();
      render(<QuickCaptureBar />);

      await user.click(screen.getByLabelText("展开更多选项"));
      const input = screen.getByPlaceholderText("记录灵感或任务...");
      await user.type(input, "后天开会");

      const dateInput = screen.getByLabelText("计划日期") as HTMLInputElement;
      await waitFor(() => {
        expect(dateInput.value).toBeTruthy();
      });
      expect(screen.getByText(/已自动设为后天/)).toBeTruthy();
    });

    it("展开模式下输入普通文本 → 不填充计划日期", async () => {
      const user = userEvent.setup();
      render(<QuickCaptureBar />);

      await user.click(screen.getByLabelText("展开更多选项"));
      const input = screen.getByPlaceholderText("记录灵感或任务...");
      await user.type(input, "买牛奶");

      const dateInput = screen.getByLabelText("计划日期") as HTMLInputElement;
      expect(dateInput.value).toBe("");
    });
  });

  // --- 收起模式不触发日期解析 ---

  describe("收起模式不触发日期解析", () => {
    it("收起模式下输入含'明天'的文本 → 不触发日期解析", async () => {
      const user = userEvent.setup();
      render(<QuickCaptureBar />);

      const input = screen.getByPlaceholderText("记录灵感或任务...");
      await user.type(input, "明天交报告");

      // 收起模式下没有日期字段
      expect(screen.queryByLabelText("计划日期")).toBeNull();
    });
  });

  // --- 先输入后展开场景 ---

  describe("先输入后展开", () => {
    it("先输入含日期关键词 → 再展开 → 自动填充日期", async () => {
      const user = userEvent.setup();
      render(<QuickCaptureBar />);

      // 先在收起模式输入
      const input = screen.getByPlaceholderText("记录灵感或任务...");
      await user.type(input, "明天交报告");

      // 展开后应触发日期解析
      await user.click(screen.getByLabelText("展开更多选项"));

      const dateInput = screen.getByLabelText("计划日期") as HTMLInputElement;
      await waitFor(() => {
        expect(dateInput.value).toBeTruthy();
      });
    });
  });

  // --- 不展示类型建议 ---

  describe("不展示类型建议", () => {
    it("展开模式下输入含'要不要'→ 不显示类型建议", async () => {
      const user = userEvent.setup();
      render(<QuickCaptureBar />);

      await user.click(screen.getByLabelText("展开更多选项"));
      const input = screen.getByPlaceholderText("记录灵感或任务...");
      await user.type(input, "要不要学 Rust");

      // QuickCaptureBar 不启用类型建议
      expect(screen.queryByText(/建议创建为/)).toBeNull();
    });
  });

  // --- Suppress 行为 ---

  describe("Suppress 行为", () => {
    it("手动清除计划日期 → 后续输入不再自动填充", async () => {
      const user = userEvent.setup();
      render(<QuickCaptureBar />);

      await user.click(screen.getByLabelText("展开更多选项"));
      const input = screen.getByPlaceholderText("记录灵感或任务...");
      await user.type(input, "明天交报告");

      const dateInput = screen.getByLabelText("计划日期") as HTMLInputElement;
      await waitFor(() => {
        expect(dateInput.value).toBeTruthy();
      });

      // 清除日期
      await user.clear(dateInput);
      fireEvent.change(dateInput, { target: { value: "" } });

      // 再次输入含日期关键词
      await user.clear(input);
      await user.type(input, "后天开会");

      // suppress 后不应自动填充
      await waitFor(() => {
        expect(dateInput.value).toBe("");
      });
    });

    it("提交成功后 suppress 重置，下次可重新自动填充", async () => {
      mockCreateEntry.mockResolvedValueOnce(mockEntry);
      const user = userEvent.setup();
      render(<QuickCaptureBar />);

      await user.click(screen.getByLabelText("展开更多选项"));
      const input = screen.getByPlaceholderText("记录灵感或任务...");
      await user.type(input, "明天交报告");

      const dateInput = screen.getByLabelText("计划日期") as HTMLInputElement;
      await waitFor(() => {
        expect(dateInput.value).toBeTruthy();
      });

      // 提交
      await user.click(screen.getByLabelText("发送"));

      await waitFor(() => {
        expect(mockCreateEntry).toHaveBeenCalled();
      });

      // 再次展开并输入含日期关键词
      await user.click(screen.getByLabelText("展开更多选项"));
      await user.type(input, "后天开会");

      const newDateInput = screen.getByLabelText("计划日期") as HTMLInputElement;
      await waitFor(() => {
        expect(newDateInput.value).toBeTruthy();
      });
    });
  });

  // --- Stale date 回归测试 ---

  describe("Stale date 回归", () => {
    it("展开模式下自动填充后修改标题移除日期关键词 → 清除自动填充的计划日期", async () => {
      const user = userEvent.setup();
      render(<QuickCaptureBar />);

      await user.click(screen.getByLabelText("展开更多选项"));
      const input = screen.getByPlaceholderText("记录灵感或任务...");
      await user.type(input, "明天交报告");

      const dateInput = screen.getByLabelText("计划日期") as HTMLInputElement;
      await waitFor(() => {
        expect(dateInput.value).toBeTruthy();
      });

      // 清除标题后输入不含日期关键词的文本
      await user.clear(input);
      await user.type(input, "买牛奶");

      // 自动填充的日期应被清除
      await waitFor(() => {
        expect(dateInput.value).toBe("");
      });
    });
  });
});
