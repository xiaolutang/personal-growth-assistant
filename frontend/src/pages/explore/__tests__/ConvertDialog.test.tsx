import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ConvertDialog } from "../ConvertDialog";
import type { Task } from "@/types/task";

// Mock sonner
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
  Toaster: () => null,
}));

// Mock api
const mockConvertEntry = vi.fn();
vi.mock("@/services/api", () => ({
  convertEntry: (...args: unknown[]) => mockConvertEntry(...args),
}));

// HTMLDialogElement polyfill for jsdom
beforeEach(() => {
  HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) {
    this.open = true;
    this.dispatchEvent(new Event("open"));
  });
  HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) {
    this.open = false;
    this.dispatchEvent(new Event("close"));
  });
});

import { toast } from "sonner";

const baseTask: Task = {
  id: "inbox-001",
  title: "测试灵感条目",
  content: "这是灵感内容",
  category: "inbox",
  status: "doing",
  tags: [],
  created_at: "2026-04-30T10:00:00",
  updated_at: "2026-04-30T10:00:00",
  file_path: "inbox/inbox-001.md",
};

describe("ConvertDialog", () => {
  const defaultProps = {
    open: true,
    onClose: vi.fn(),
    onSuccess: vi.fn(),
    entry: baseTask,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("打开时渲染对话框标题和预填标题", () => {
    render(<ConvertDialog {...defaultProps} />);
    expect(screen.getByText("转化条目")).toBeTruthy();
    expect(screen.getByDisplayValue("测试灵感条目")).toBeTruthy();
  });

  it("显示 task 和 decision 两个目标类型选项", () => {
    render(<ConvertDialog {...defaultProps} />);
    expect(screen.getByText("任务")).toBeTruthy();
    expect(screen.getByText("决策")).toBeTruthy();
  });

  it("默认选中 task 类型", () => {
    render(<ConvertDialog {...defaultProps} />);
    const taskButton = screen.getByText("任务").closest("button")!;
    expect(taskButton.className).toContain("bg-primary");
  });

  it("点击 decision 类型切换选中状态", async () => {
    const user = userEvent.setup();
    render(<ConvertDialog {...defaultProps} />);
    await user.click(screen.getByText("决策"));
    const decisionButton = screen.getByText("决策").closest("button")!;
    expect(decisionButton.className).toContain("bg-primary");
  });

  it("显示优先级选择器", () => {
    render(<ConvertDialog {...defaultProps} />);
    expect(screen.getByText("优先级")).toBeTruthy();
  });

  it("显示计划日期输入", () => {
    render(<ConvertDialog {...defaultProps} />);
    expect(screen.getByText("计划日期")).toBeTruthy();
  });

  it("点击确认调用 convertEntry API 并触发 onSuccess", async () => {
    mockConvertEntry.mockResolvedValueOnce({ ...baseTask, category: "task" });
    const onSuccess = vi.fn();
    const user = userEvent.setup();
    render(<ConvertDialog {...defaultProps} onSuccess={onSuccess} />);

    await user.click(screen.getByText("确认转化"));
    await waitFor(() => {
      expect(mockConvertEntry).toHaveBeenCalledWith("inbox-001", {
        target_category: "task",
        priority: null,
        planned_date: null,
        parent_id: null,
      });
    });
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalled();
    });
    expect(onSuccess).toHaveBeenCalled();
  });

  it("选择优先级后调用 API 时传递 priority", async () => {
    mockConvertEntry.mockResolvedValueOnce({ ...baseTask, category: "task" });
    const user = userEvent.setup();
    render(<ConvertDialog {...defaultProps} />);

    // 选择优先级 "高"
    const select = screen.getByLabelText("优先级");
    await user.selectOptions(select, "high");

    await user.click(screen.getByText("确认转化"));
    await waitFor(() => {
      expect(mockConvertEntry).toHaveBeenCalledWith("inbox-001", {
        target_category: "task",
        priority: "high",
        planned_date: null,
        parent_id: null,
      });
    });
  });

  it("设置计划日期后调用 API 时传递 planned_date", async () => {
    mockConvertEntry.mockResolvedValueOnce({ ...baseTask, category: "task" });
    const user = userEvent.setup();
    render(<ConvertDialog {...defaultProps} />);

    const dateInput = screen.getByLabelText("计划日期");
    await user.type(dateInput, "2026-05-15");

    await user.click(screen.getByText("确认转化"));
    await waitFor(() => {
      expect(mockConvertEntry).toHaveBeenCalledWith("inbox-001", expect.objectContaining({
        target_category: "task",
        planned_date: expect.stringContaining("2026-05-15"),
      }));
    });
  });

  it("转化为 decision 类型时正确传参", async () => {
    mockConvertEntry.mockResolvedValueOnce({ ...baseTask, category: "decision" });
    const user = userEvent.setup();
    render(<ConvertDialog {...defaultProps} />);

    await user.click(screen.getByText("决策"));
    await user.click(screen.getByText("确认转化"));
    await waitFor(() => {
      expect(mockConvertEntry).toHaveBeenCalledWith("inbox-001", {
        target_category: "decision",
        priority: null,
        planned_date: null,
        parent_id: null,
      });
    });
  });

  it("API 失败时显示错误 toast，不触发 onSuccess", async () => {
    mockConvertEntry.mockRejectedValueOnce(new Error("Server error"));
    const onSuccess = vi.fn();
    const user = userEvent.setup();
    render(<ConvertDialog {...defaultProps} onSuccess={onSuccess} />);

    await user.click(screen.getByText("确认转化"));
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("转化失败，请重试");
    });
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it("点击取消触发 onClose", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<ConvertDialog {...defaultProps} onClose={onClose} />);

    await user.click(screen.getByText("取消"));
    expect(onClose).toHaveBeenCalled();
  });

  it("转化中显示 loading 状态", async () => {
    mockConvertEntry.mockReturnValueOnce(new Promise(() => {}));
    const user = userEvent.setup();
    render(<ConvertDialog {...defaultProps} />);

    await user.click(screen.getByText("确认转化"));
    expect(screen.getByText("转化中...")).toBeTruthy();
  });

  it("open=false 时不渲染对话框内容", () => {
    render(<ConvertDialog {...defaultProps} open={false} />);
    expect(screen.queryByText("转化条目")).toBeNull();
  });
});
