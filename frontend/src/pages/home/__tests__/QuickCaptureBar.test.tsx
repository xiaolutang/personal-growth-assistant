/**
 * F03: QuickCaptureBar 组件测试
 * - 默认模式：单行文本输入 + 发送按钮，回车或点击发送 -> createEntry({type:'inbox', title})
 * - 展开模式：优先级下拉 + 日期选择器 -> createEntry({type:'task', title, priority, planned_date})
 * - 更多类型：点击'更多类型'链接 -> 弹出 CreateDialog
 * - 空输入：发送按钮 disabled，回车不触发创建
 * - 网络失败：按钮恢复可用，错误提示
 * - 防重复提交：loading 状态
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

// Mock CreateDialog
vi.mock("@/components/CreateDialog", () => ({
  CreateDialog: ({ open, onOpenChange, defaultType }: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    defaultType?: string;
  }) => (
    <div data-testid="create-dialog" data-open={open} data-default-type={defaultType ?? ""}>
      <button onClick={() => onOpenChange(false)}>关闭Dialog</button>
    </div>
  ),
}));

import { QuickCaptureBar } from "../QuickCaptureBar";
import { toast } from "sonner";
import type { Task } from "@/types/task";

const mockEntry: Task = {
  id: "entry-001",
  title: "测试条目",
  content: "",
  category: "inbox",
  status: "waitStart",
  tags: [],
  created_at: "2026-04-30T10:00:00",
  updated_at: "2026-04-30T10:00:00",
  file_path: "inbox/entry-001.md",
};

describe("QuickCaptureBar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // --- AC: 默认模式渲染 ---
  it("渲染单行文本输入框和发送按钮", () => {
    render(<QuickCaptureBar />);
    expect(screen.getByPlaceholderText("记录灵感或任务...")).toBeTruthy();
    expect(screen.getByLabelText("发送")).toBeTruthy();
  });

  // --- AC: 空输入不可提交 ---
  it("输入为空时发送按钮 disabled", () => {
    render(<QuickCaptureBar />);
    const sendBtn = screen.getByLabelText("发送");
    expect(sendBtn).toBeDisabled();
  });

  // --- AC: 空输入回车不触发创建 ---
  it("输入为空时回车不触发创建", async () => {
    const user = userEvent.setup();
    render(<QuickCaptureBar />);
    const input = screen.getByPlaceholderText("记录灵感或任务...");
    await user.click(input);
    await user.keyboard("{Enter}");
    expect(mockCreateEntry).not.toHaveBeenCalled();
  });

  // --- AC: 默认模式提交创建 inbox ---
  it("输入文字后回车 -> createEntry({type:'inbox', title})", async () => {
    mockCreateEntry.mockResolvedValueOnce(mockEntry);
    const user = userEvent.setup();
    render(<QuickCaptureBar />);

    const input = screen.getByPlaceholderText("记录灵感或任务...");
    await user.type(input, "买牛奶");
    await user.keyboard("{Enter}");

    await waitFor(() => {
      expect(mockCreateEntry).toHaveBeenCalledWith({
        type: "inbox",
        title: "买牛奶",
      });
    });
    expect(toast.success).toHaveBeenCalledWith("已创建灵感");
  });

  // --- AC: 点击发送按钮创建 inbox ---
  it("输入文字后点击发送按钮 -> createEntry({type:'inbox', title})", async () => {
    mockCreateEntry.mockResolvedValueOnce(mockEntry);
    const user = userEvent.setup();
    render(<QuickCaptureBar />);

    const input = screen.getByPlaceholderText("记录灵感或任务...");
    await user.type(input, "买牛奶");
    await user.click(screen.getByLabelText("发送"));

    await waitFor(() => {
      expect(mockCreateEntry).toHaveBeenCalledWith({
        type: "inbox",
        title: "买牛奶",
      });
    });
  });

  // --- AC: 提交后清空输入 ---
  it("提交成功后清空输入框", async () => {
    mockCreateEntry.mockResolvedValueOnce(mockEntry);
    const user = userEvent.setup();
    render(<QuickCaptureBar />);

    const input = screen.getByPlaceholderText("记录灵感或任务...") as HTMLInputElement;
    await user.type(input, "买牛奶");
    await user.click(screen.getByLabelText("发送"));

    await waitFor(() => {
      expect(input.value).toBe("");
    });
  });

  // --- AC: 展开模式 ---
  it("点击展开图标后显示优先级下拉和日期选择器", async () => {
    const user = userEvent.setup();
    render(<QuickCaptureBar />);

    await user.click(screen.getByLabelText("展开更多选项"));

    expect(screen.getByLabelText("优先级")).toBeTruthy();
    expect(screen.getByLabelText("计划日期")).toBeTruthy();
  });

  // --- AC: 展开模式提交创建 task ---
  it("展开模式提交 -> createEntry({type:'task', title, priority, planned_date})", async () => {
    mockCreateEntry.mockResolvedValueOnce({ ...mockEntry, category: "task" });
    const user = userEvent.setup();
    render(<QuickCaptureBar />);

    await user.click(screen.getByLabelText("展开更多选项"));
    const input = screen.getByPlaceholderText("记录灵感或任务...");
    await user.type(input, "写周报");
    await user.selectOptions(screen.getByLabelText("优先级"), "high");
    await user.type(screen.getByLabelText("计划日期"), "2026-05-15");
    await user.click(screen.getByLabelText("发送"));

    await waitFor(() => {
      expect(mockCreateEntry).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "task",
          title: "写周报",
          priority: "high",
          planned_date: "2026-05-15",
        }),
      );
    });
    expect(toast.success).toHaveBeenCalledWith("已创建任务");
  });

  // --- AC: 展开模式回车提交 ---
  it("展开模式下回车也创建 task", async () => {
    mockCreateEntry.mockResolvedValueOnce({ ...mockEntry, category: "task" });
    const user = userEvent.setup();
    render(<QuickCaptureBar />);

    await user.click(screen.getByLabelText("展开更多选项"));
    const input = screen.getByPlaceholderText("记录灵感或任务...");
    await user.type(input, "展开回车测试{Enter}");

    await waitFor(() => {
      expect(mockCreateEntry).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "task",
          title: "展开回车测试",
        }),
      );
    });
  });

  // --- AC: 收起展开 ---
  it("再次点击展开图标可收起展开区域", async () => {
    const user = userEvent.setup();
    render(<QuickCaptureBar />);

    const toggleBtn = screen.getByLabelText("展开更多选项");
    await user.click(toggleBtn);
    expect(screen.getByLabelText("优先级")).toBeTruthy();

    // 收起
    await user.click(screen.getByLabelText("收起更多选项"));
    expect(screen.queryByLabelText("优先级")).toBeNull();
  });

  // --- AC: 更多类型链接 ---
  it("点击'更多类型'链接 -> 打开 CreateDialog", async () => {
    const user = userEvent.setup();
    render(<QuickCaptureBar />);

    await user.click(screen.getByLabelText("展开更多选项"));
    await user.click(screen.getByText("更多类型"));

    const dialog = screen.getByTestId("create-dialog");
    expect(dialog).toBeTruthy();
    expect(dialog.getAttribute("data-open")).toBe("true");
  });

  // --- AC: 网络失败 ---
  it("API 报错 -> 发送按钮恢复可用 + 显示错误提示", async () => {
    mockCreateEntry.mockRejectedValueOnce(new Error("网络错误"));
    const user = userEvent.setup();
    render(<QuickCaptureBar />);

    const input = screen.getByPlaceholderText("记录灵感或任务...");
    await user.type(input, "失败测试");
    await user.click(screen.getByLabelText("发送"));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("创建失败：网络错误");
    });

    // 按钮恢复可用
    const sendBtn = screen.getByLabelText("发送");
    expect(sendBtn).not.toBeDisabled();
    // 输入内容保留（不丢失）
    expect((input as HTMLInputElement).value).toBe("失败测试");
  });

  // --- AC: 防重复提交 ---
  it("发送中按钮 loading -> 不可重复点击", async () => {
    mockCreateEntry.mockReturnValueOnce(new Promise(() => {})); // 永不 resolve
    const user = userEvent.setup();
    render(<QuickCaptureBar />);

    const input = screen.getByPlaceholderText("记录灵感或任务...");
    await user.type(input, "防重复");
    await user.click(screen.getByLabelText("发送"));

    // 按钮应显示 loading 状态
    const sendBtn = screen.getByLabelText("发送");
    expect(sendBtn).toBeDisabled();

    // 只调用了一次
    expect(mockCreateEntry).toHaveBeenCalledTimes(1);
  });

  // --- AC: 输入框为纯空格时不可提交 ---
  it("输入纯空格时发送按钮 disabled", async () => {
    const user = userEvent.setup();
    render(<QuickCaptureBar />);

    const input = screen.getByPlaceholderText("记录灵感或任务...");
    await user.type(input, "   ");

    const sendBtn = screen.getByLabelText("发送");
    expect(sendBtn).toBeDisabled();
  });

  // --- AC: CreateDialog 关闭后状态恢复 ---
  it("CreateDialog 关闭后 dialogOpen 恢复为 false", async () => {
    const user = userEvent.setup();
    render(<QuickCaptureBar />);

    await user.click(screen.getByLabelText("展开更多选项"));
    await user.click(screen.getByText("更多类型"));
    expect(screen.getByTestId("create-dialog").getAttribute("data-open")).toBe("true");

    // 关闭 dialog
    await user.click(screen.getByText("关闭Dialog"));
    expect(screen.getByTestId("create-dialog").getAttribute("data-open")).toBe("false");
  });

  // --- AC: 输入后发送按钮变为可用 ---
  it("输入非空内容后发送按钮变为可用", async () => {
    const user = userEvent.setup();
    render(<QuickCaptureBar />);

    const input = screen.getByPlaceholderText("记录灵感或任务...");
    await user.type(input, "有内容");

    const sendBtn = screen.getByLabelText("发送");
    expect(sendBtn).not.toBeDisabled();
  });

  // --- AC: IME 输入法组合中 Enter 不触发提交 ---
  it("IME 组合输入中 Enter 不触发创建", async () => {
    const user = userEvent.setup();
    render(<QuickCaptureBar />);

    const input = screen.getByPlaceholderText("记录灵感或任务...");
    await user.click(input);

    // 模拟 IME 组合中的 Enter（isComposing=true）
    fireEvent.keyDown(input, { key: "Enter", shiftKey: false, nativeEvent: { isComposing: true } as unknown as KeyboardEvent });

    expect(mockCreateEntry).not.toHaveBeenCalled();
  });
});
