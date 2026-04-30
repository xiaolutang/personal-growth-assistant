import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
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
import { toast } from "sonner";
import { categoryConfig } from "@/config/constants";
import type { Task, Category } from "@/types/task";

// 从 categoryConfig 派生全部分类，与组件保持一致（单一权威来源）
const ALL_CATEGORIES: Category[] = Object.keys(categoryConfig) as Category[];
const CATEGORY_LABELS: Record<string, string> = Object.fromEntries(
  ALL_CATEGORIES.map((cat) => [cat, categoryConfig[cat].label]),
);

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

describe("CreateDialog", () => {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // --- AC: 组件渲染 ---
  it("open=true 时渲染对话框标题", () => {
    render(<CreateDialog {...defaultProps} />);
    expect(screen.getByText("新建条目")).toBeTruthy();
  });

  it("open=false 时不渲染对话框", () => {
    render(<CreateDialog {...defaultProps} open={false} />);
    expect(screen.queryByText("新建条目")).toBeNull();
  });

  // --- AC: 类型选择器 ---
  it("默认展示全部 7 种类型", () => {
    render(<CreateDialog {...defaultProps} />);
    for (const cat of ALL_CATEGORIES) {
      expect(screen.getByText(CATEGORY_LABELS[cat])).toBeTruthy();
    }
  });

  it("传入 allowedTypes 时仅展示指定类型", () => {
    render(
      <CreateDialog
        {...defaultProps}
        allowedTypes={["task", "inbox"]}
      />
    );
    expect(screen.getByText("任务")).toBeTruthy();
    expect(screen.getByText("灵感")).toBeTruthy();
    expect(screen.queryByText("笔记")).toBeNull();
    expect(screen.queryByText("项目")).toBeNull();
  });

  it("传入 defaultType 时默认选中该类型", () => {
    render(
      <CreateDialog
        {...defaultProps}
        defaultType="project"
      />
    );
    // project 的 label 是 "项目"
    const projectBtn = screen.getByText("项目").closest("button")!;
    expect(projectBtn.className).toContain("bg-primary");
  });

  // --- AC: 按类型动态渲染字段 ---
  it("task 类型显示优先级下拉和日期选择器", () => {
    render(<CreateDialog {...defaultProps} defaultType="task" />);
    expect(screen.getByLabelText("优先级")).toBeTruthy();
    expect(screen.getByLabelText("计划日期")).toBeTruthy();
  });

  it("project 类型显示描述 textarea", () => {
    render(<CreateDialog {...defaultProps} defaultType="project" />);
    expect(screen.getByLabelText("描述")).toBeTruthy();
  });

  it("decision 类型显示选项描述 textarea", () => {
    render(<CreateDialog {...defaultProps} defaultType="decision" />);
    expect(screen.getByLabelText("选项描述")).toBeTruthy();
  });

  it("inbox 类型仅显示标题输入框", () => {
    render(<CreateDialog {...defaultProps} defaultType="inbox" />);
    expect(screen.getByLabelText("标题")).toBeTruthy();
    // 不应显示描述相关的字段
    expect(screen.queryByLabelText("描述")).toBeNull();
    expect(screen.queryByLabelText("选项描述")).toBeNull();
    expect(screen.queryByLabelText("优先级")).toBeNull();
  });

  it("note 类型显示标题和内容", () => {
    render(<CreateDialog {...defaultProps} defaultType="note" />);
    expect(screen.getByLabelText("标题")).toBeTruthy();
    expect(screen.getByLabelText("内容")).toBeTruthy();
  });

  it("reflection 类型显示标题和内容", () => {
    render(<CreateDialog {...defaultProps} defaultType="reflection" />);
    expect(screen.getByLabelText("标题")).toBeTruthy();
    expect(screen.getByLabelText("内容")).toBeTruthy();
  });

  it("question 类型显示标题和描述", () => {
    render(<CreateDialog {...defaultProps} defaultType="question" />);
    expect(screen.getByLabelText("标题")).toBeTruthy();
    expect(screen.getByLabelText("描述")).toBeTruthy();
  });

  // --- AC: 类型切换 ---
  it("从 task 切换到 project：优先级字段消失、描述字段出现", async () => {
    const user = userEvent.setup();
    render(<CreateDialog {...defaultProps} defaultType="task" />);

    // task 有优先级
    expect(screen.getByLabelText("优先级")).toBeTruthy();

    // 切到 project
    await user.click(screen.getByText("项目"));

    // project 不显示优先级，显示描述
    await waitFor(() => {
      expect(screen.queryByLabelText("优先级")).toBeNull();
      expect(screen.getByLabelText("描述")).toBeTruthy();
    });
  });

  // --- AC: 正常创建 ---
  it("选 task 类型 → 填标题+优先级 → 提交 → toast 成功 + onSuccess 触发", async () => {
    mockCreateEntry.mockResolvedValueOnce(mockEntry);
    const onSuccess = vi.fn();
    const user = userEvent.setup();

    render(
      <CreateDialog
        {...defaultProps}
        defaultType="task"
        onSuccess={onSuccess}
      />
    );

    await user.type(screen.getByLabelText("标题"), "新任务");
    await user.selectOptions(screen.getByLabelText("优先级"), "high");
    await user.click(screen.getByText("创建"));

    await waitFor(() => {
      expect(mockCreateEntry).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "task",
          title: "新任务",
          priority: "high",
        }),
      );
    });
    expect(toast.success).toHaveBeenCalled();
    expect(onSuccess).toHaveBeenCalledWith(mockEntry);
  });

  // --- AC: 回车快速提交（inbox 单字段场景） ---
  it("inbox 类型 → 输入标题 → 回车 → 直接创建", async () => {
    mockCreateEntry.mockResolvedValueOnce({ ...mockEntry, category: "inbox" });
    const onSuccess = vi.fn();
    const user = userEvent.setup();

    render(
      <CreateDialog
        {...defaultProps}
        defaultType="inbox"
        onSuccess={onSuccess}
      />
    );

    const titleInput = screen.getByLabelText("标题");
    await user.type(titleInput, "快速灵感");
    await user.keyboard("{Enter}");

    await waitFor(() => {
      expect(mockCreateEntry).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "inbox",
          title: "快速灵感",
        }),
      );
    });
    expect(toast.success).toHaveBeenCalled();
    expect(onSuccess).toHaveBeenCalled();
  });

  // --- AC: 空标题提交 ---
  it("空标题提交显示校验错误", async () => {
    const user = userEvent.setup();
    render(<CreateDialog {...defaultProps} defaultType="task" />);

    await user.click(screen.getByText("创建"));

    expect(await screen.findByText("请输入标题")).toBeTruthy();
    expect(mockCreateEntry).not.toHaveBeenCalled();
  });

  // --- AC: 创建失败 ---
  it("API 报错 → 错误提示可见 → 对话框不关闭", async () => {
    mockCreateEntry.mockRejectedValueOnce(new Error("网络错误"));
    const onOpenChange = vi.fn();
    const onSuccess = vi.fn();
    const user = userEvent.setup();

    render(
      <CreateDialog
        {...defaultProps}
        defaultType="task"
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
      />
    );

    await user.type(screen.getByLabelText("标题"), "测试标题");
    await user.click(screen.getByText("创建"));

    expect(await screen.findByText("创建失败：网络错误")).toBeTruthy();
    expect(onSuccess).not.toHaveBeenCalled();
    // onOpenChange 不应被调用（对话框不关闭）
    expect(onOpenChange).not.toHaveBeenCalled();
  });

  // --- AC: ESC 关闭（通过 dialog onClose 事件模拟，jsdom 不支持原生 ESC） ---
  it("ESC 关闭对话框（dialog close 事件）", () => {
    const onOpenChange = vi.fn();

    render(
      <CreateDialog
        {...defaultProps}
        onOpenChange={onOpenChange}
      />
    );

    // jsdom 不支持原生 ESC 关闭 dialog，直接模拟 dialog 的 close 事件
    const dialog = document.querySelector("dialog")!;
    dialog.dispatchEvent(new Event("close"));

    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  // --- AC: 表单重置（创建成功后再次打开） ---
  it("创建成功后再次打开 → 所有字段为空", async () => {
    mockCreateEntry.mockResolvedValueOnce(mockEntry);
    const onOpenChange = vi.fn();
    const user = userEvent.setup();

    const { rerender } = render(
      <CreateDialog
        {...defaultProps}
        defaultType="task"
        onOpenChange={onOpenChange}
      />
    );

    // 填写并提交
    await user.type(screen.getByLabelText("标题"), "要重置的标题");
    await user.click(screen.getByText("创建"));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalled();
    });

    // 模拟关闭
    rerender(
      <CreateDialog
        {...defaultProps}
        open={false}
        defaultType="task"
        onOpenChange={onOpenChange}
      />
    );

    // 模拟再次打开
    rerender(
      <CreateDialog
        {...defaultProps}
        open={true}
        defaultType="task"
        onOpenChange={onOpenChange}
      />
    );

    // 标题字段应为空
    const titleInput = screen.getByLabelText("标题") as HTMLInputElement;
    expect(titleInput.value).toBe("");
  });

  // --- AC: project 类型创建带描述 ---
  it("project 类型 → 填标题+描述 → 提交", async () => {
    mockCreateEntry.mockResolvedValueOnce({ ...mockEntry, category: "project" });
    const onSuccess = vi.fn();
    const user = userEvent.setup();

    render(
      <CreateDialog
        {...defaultProps}
        defaultType="project"
        onSuccess={onSuccess}
      />
    );

    await user.type(screen.getByLabelText("标题"), "新项目");
    await user.type(screen.getByLabelText("描述"), "项目描述内容");
    await user.click(screen.getByText("创建"));

    await waitFor(() => {
      expect(mockCreateEntry).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "project",
          title: "新项目",
          content: "项目描述内容",
        }),
      );
    });
  });

  // --- AC: task 类型带日期 ---
  it("task 类型 → 填标题+计划日期 → 提交", async () => {
    mockCreateEntry.mockResolvedValueOnce(mockEntry);
    const user = userEvent.setup();

    render(
      <CreateDialog
        {...defaultProps}
        defaultType="task"
      />
    );

    await user.type(screen.getByLabelText("标题"), "带日期的任务");
    await user.type(screen.getByLabelText("计划日期"), "2026-05-15");
    await user.click(screen.getByText("创建"));

    await waitFor(() => {
      expect(mockCreateEntry).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "task",
          title: "带日期的任务",
          planned_date: expect.stringContaining("2026-05-15"),
        }),
      );
    });
  });

  // --- AC: 点击取消关闭 ---
  it("点击取消按钮触发 onOpenChange(false)", async () => {
    const onOpenChange = vi.fn();
    const user = userEvent.setup();

    render(
      <CreateDialog
        {...defaultProps}
        onOpenChange={onOpenChange}
      />
    );

    await user.click(screen.getByText("取消"));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  // --- AC: 创建中 loading 状态 ---
  it("创建中显示 loading 状态", async () => {
    mockCreateEntry.mockReturnValueOnce(new Promise(() => {}));
    const user = userEvent.setup();

    render(<CreateDialog {...defaultProps} defaultType="task" />);

    await user.type(screen.getByLabelText("标题"), "加载中测试");
    await user.click(screen.getByText("创建"));

    expect(screen.getByText("创建中...")).toBeTruthy();
  });

  // --- 回归测试：defaultType 可选，不传时不预选类型 ---
  it("不传 defaultType 时无预选类型（所有按钮均非 active）", () => {
    render(<CreateDialog {...defaultProps} />);
    // 所有类型按钮不应有 bg-primary（即未选中）
    for (const cat of ALL_CATEGORIES) {
      const btn = screen.getByText(CATEGORY_LABELS[cat]).closest("button")!;
      expect(btn.className).not.toContain("bg-primary");
    }
  });

  it("不传 defaultType 时点创建显示校验错误（需选择类型）", async () => {
    const user = userEvent.setup();
    render(<CreateDialog {...defaultProps} />);

    // 不选类型直接填标题提交
    await user.type(screen.getByLabelText("标题"), "有标题");
    await user.click(screen.getByText("创建"));

    expect(await screen.findByText("请选择类型")).toBeTruthy();
    expect(mockCreateEntry).not.toHaveBeenCalled();
  });

  it("allowedTypes 不含 defaultType 时不预选类型", () => {
    render(
      <CreateDialog
        {...defaultProps}
        defaultType="project"
        allowedTypes={["inbox", "note"]}
      />
    );
    // "project" 不在 allowedTypes 中，不应预选任何类型
    const inboxBtn = screen.getByText(CATEGORY_LABELS["inbox"]).closest("button")!;
    const noteBtn = screen.getByText(CATEGORY_LABELS["note"]).closest("button")!;
    expect(inboxBtn.className).not.toContain("bg-primary");
    expect(noteBtn.className).not.toContain("bg-primary");
    // project 不在列表中
    expect(screen.queryByText(CATEGORY_LABELS["project"])).toBeNull();
  });

  // --- 回归测试：非快速创建类型 Enter 不提交 ---
  it("project 类型按 Enter 不触发提交", async () => {
    mockCreateEntry.mockResolvedValueOnce({ ...mockEntry, category: "project" });
    const user = userEvent.setup();

    render(
      <CreateDialog
        {...defaultProps}
        defaultType="project"
      />
    );

    const titleInput = screen.getByLabelText("标题");
    await user.type(titleInput, "Project title");
    await user.keyboard("{Enter}");

    // Enter 不应触发创建
    expect(mockCreateEntry).not.toHaveBeenCalled();
  });

  it("note 类型按 Enter 不触发提交", async () => {
    const user = userEvent.setup();

    render(
      <CreateDialog
        {...defaultProps}
        defaultType="note"
      />
    );

    const titleInput = screen.getByLabelText("标题");
    await user.type(titleInput, "Note title");
    await user.keyboard("{Enter}");

    expect(mockCreateEntry).not.toHaveBeenCalled();
  });

  // --- 回归测试：task 类型回车快速提交 ---
  it("task 类型按 Enter 触发提交（快速创建场景）", async () => {
    mockCreateEntry.mockResolvedValueOnce(mockEntry);
    const onSuccess = vi.fn();
    const user = userEvent.setup();

    render(
      <CreateDialog
        {...defaultProps}
        defaultType="task"
        onSuccess={onSuccess}
      />
    );

    const titleInput = screen.getByLabelText("标题");
    await user.type(titleInput, "Quick task");
    await user.keyboard("{Enter}");

    await waitFor(() => {
      expect(mockCreateEntry).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "task",
          title: "Quick task",
        }),
      );
    });
  });

  // --- 回归测试：移动端适配 CSS 类 ---
  it("dialog 元素包含移动端适配 CSS 类", () => {
    render(<CreateDialog {...defaultProps} />);
    const dialog = document.querySelector("dialog")!;
    // 移动端全屏/底部抽屉
    expect(dialog.className).toContain("max-sm:max-w-full");
    expect(dialog.className).toContain("max-sm:mt-auto");
    expect(dialog.className).toContain("max-sm:h-[90vh]");
  });

  // --- 回归测试：allowedTypes 动态收窄时 selectedType 重置 ---
  it("allowedTypes 动态收窄时 selectedType 被重置为 null", () => {
    const { rerender } = render(
      <CreateDialog
        {...defaultProps}
        defaultType="task"
        allowedTypes={["task", "project", "inbox"]}
      />
    );

    // task 被选中
    const taskBtn = screen.getByText(CATEGORY_LABELS["task"]).closest("button")!;
    expect(taskBtn.className).toContain("bg-primary");

    // 收窄 allowedTypes 排除 task
    rerender(
      <CreateDialog
        {...defaultProps}
        defaultType="task"
        allowedTypes={["project", "inbox"]}
      />
    );

    // project 和 inbox 按钮都不应该被选中
    const projectBtn = screen.getByText(CATEGORY_LABELS["project"]).closest("button")!;
    const inboxBtn = screen.getByText(CATEGORY_LABELS["inbox"]).closest("button")!;
    expect(projectBtn.className).not.toContain("bg-primary");
    expect(inboxBtn.className).not.toContain("bg-primary");
  });

  // --- 回归测试：onSuccess 抛异常不应显示创建失败 ---
  it("onSuccess 抛异常时不应显示创建失败错误", async () => {
    mockCreateEntry.mockResolvedValueOnce(mockEntry);
    const onSuccess = vi.fn(() => {
      throw new Error("callback error");
    });
    const onOpenChange = vi.fn();
    const user = userEvent.setup();

    render(
      <CreateDialog
        {...defaultProps}
        defaultType="task"
        onSuccess={onSuccess}
        onOpenChange={onOpenChange}
      />
    );

    await user.type(screen.getByLabelText("标题"), "标题");
    await user.click(screen.getByText("创建"));

    // toast.success 应已调用（创建成功）
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalled();
    });
    // 不应显示创建失败错误
    expect(screen.queryByText(/创建失败/)).toBeNull();
  });
});
