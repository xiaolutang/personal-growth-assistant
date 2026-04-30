import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { TaskCard } from "./TaskCard";
import type { Task } from "@/types/task";

// Mock sonner
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
  Toaster: () => null,
}));

// Mock convertEntry API
const mockConvertEntry = vi.fn();
vi.mock("@/services/api", () => ({
  convertEntry: (...args: unknown[]) => mockConvertEntry(...args),
}));

// Mock taskStore selectors
const mockUpdateTaskStatus = vi.fn();
const mockDeleteTask = vi.fn();
const mockTasks: Task[] = [];

vi.mock("@/stores/taskStore", () => ({
  useTaskStore: (selector: (state: Record<string, unknown>) => unknown) => {
    const state = {
      updateTaskStatus: mockUpdateTaskStatus,
      deleteTask: mockDeleteTask,
      tasks: mockTasks,
    };
    return selector(state);
  },
}));

// HTMLDialogElement polyfill for jsdom
const originalShowModal = HTMLDialogElement.prototype.showModal;
const originalClose = HTMLDialogElement.prototype.close;

import { toast } from "sonner";

function createInboxTask(overrides: Partial<Task> = {}): Task {
  return {
    id: "inbox-test123",
    title: "测试灵感",
    content: "灵感内容",
    category: "inbox",
    status: "doing",
    tags: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    file_path: "inbox/inbox-test123.md",
    ...overrides,
  };
}

function createTaskItem(overrides: Partial<Task> = {}): Task {
  return {
    id: "task-abc123",
    title: "测试任务",
    content: "任务内容",
    category: "task",
    status: "doing",
    tags: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    file_path: "tasks/task-abc123.md",
    ...overrides,
  };
}

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("TaskCard — 灵感转化", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) {
      this.open = true;
    });
    HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) {
      this.open = false;
    });
  });

  afterEach(() => {
    HTMLDialogElement.prototype.showModal = originalShowModal;
    HTMLDialogElement.prototype.close = originalClose;
  });

  it("inbox 条目应显示转化按钮", () => {
    renderWithRouter(<TaskCard task={createInboxTask()} />);
    // inbox 条目应该有：状态切换按钮 + 转任务按钮 + 转决策按钮 + 删除按钮 = 4 个按钮
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThanOrEqual(4);
  });

  it("非 inbox 条目不显示转化按钮", () => {
    const { container } = renderWithRouter(<TaskCard task={createTaskItem()} />);
    // 不应出现"转为任务"或"转为决策"文本
    expect(container.textContent).not.toContain("转为任务");
    expect(container.textContent).not.toContain("转为决策");
  });

  it("点击转任务按钮打开 ConvertDialog", async () => {
    const user = userEvent.setup();
    renderWithRouter(<TaskCard task={createInboxTask()} />);

    // 查找带 title="转为任务" 的按钮
    const convertBtn = screen.getByTitle("转为任务");
    await user.click(convertBtn);

    // ConvertDialog 应该打开
    expect(screen.getByText("转化条目")).toBeInTheDocument();
    expect(screen.getByText("确认转化")).toBeInTheDocument();
  });

  it("点击转决策按钮打开 ConvertDialog 并默认选中决策", async () => {
    const user = userEvent.setup();
    renderWithRouter(<TaskCard task={createInboxTask()} />);

    const convertBtn = screen.getByTitle("转为决策");
    await user.click(convertBtn);

    // ConvertDialog 应该打开，且决策应被选中
    expect(screen.getByText("转化条目")).toBeInTheDocument();
    const decisionButton = screen.getByText("决策").closest("button")!;
    expect(decisionButton.className).toContain("bg-primary");
  });

  it("转化失败显示错误 toast", async () => {
    mockConvertEntry.mockRejectedValueOnce(new Error("API error"));
    const onConvertSuccess = vi.fn();
    const user = userEvent.setup();
    renderWithRouter(<TaskCard task={createInboxTask()} onConvertSuccess={onConvertSuccess} />);

    const convertBtn = screen.getByTitle("转为任务");
    await user.click(convertBtn);

    // Wait for dialog to appear
    await waitFor(() => {
      expect(screen.getByText("确认转化")).toBeInTheDocument();
    });

    await user.click(screen.getByText("确认转化"));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("转化失败，请重试");
    }, { timeout: 3000 });
    expect(onConvertSuccess).not.toHaveBeenCalled();
  });

  it("转化成功后触发 onConvertSuccess 回调", async () => {
    mockConvertEntry.mockResolvedValueOnce({ ...createInboxTask(), category: "task" });
    const onConvertSuccess = vi.fn();
    const user = userEvent.setup();
    renderWithRouter(<TaskCard task={createInboxTask()} onConvertSuccess={onConvertSuccess} />);

    const convertBtn = screen.getByTitle("转为任务");
    await user.click(convertBtn);
    await user.click(screen.getByText("确认转化"));

    await waitFor(() => {
      expect(mockConvertEntry).toHaveBeenCalledWith("inbox-test123", {
        target_category: "task",
        priority: null,
        planned_date: null,
        parent_id: null,
      });
    });
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalled();
    });
    // onConvertSuccess should be called after animation timeout (300ms)
    await waitFor(() => {
      expect(onConvertSuccess).toHaveBeenCalled();
    }, { timeout: 1000 });
  });

  it("转化按钮不触发卡片导航", async () => {
    const user = userEvent.setup();
    renderWithRouter(<TaskCard task={createInboxTask()} />);

    const convertBtn = screen.getByTitle("转为任务");
    await user.click(convertBtn);

    // 转化按钮点击后应打开对话框而非导航
    expect(screen.getByText("转化条目")).toBeInTheDocument();
  });
});

describe("TaskCard — HighlightText 关键词高亮", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("高亮所有匹配的关键词", () => {
    const task = createTaskItem({ title: "foo bar foo baz foo" });
    const { container } = renderWithRouter(<TaskCard task={task} highlightKeyword="foo" />);
    const marks = container.querySelectorAll("mark");
    expect(marks.length).toBe(3);
    marks.forEach((m) => expect(m.textContent).toBe("foo"));
  });

  it("大小写不敏感高亮", () => {
    const task = createTaskItem({ title: "React Hooks" });
    const { container } = renderWithRouter(<TaskCard task={task} highlightKeyword="react" />);
    const marks = container.querySelectorAll("mark");
    expect(marks.length).toBe(1);
    expect(marks[0].textContent).toBe("React");
  });

  it("无匹配时返回原文", () => {
    const task = createTaskItem({ title: "Hello World" });
    renderWithRouter(<TaskCard task={task} highlightKeyword="xyz" />);
    expect(screen.getByText("Hello World")).toBeInTheDocument();
  });

  it("空关键词时不高亮", () => {
    const task = createTaskItem({ title: "Hello World" });
    renderWithRouter(<TaskCard task={task} highlightKeyword="" />);
    expect(screen.getByText("Hello World")).toBeInTheDocument();
  });

  it("特殊正则字符安全转义", () => {
    const task = createTaskItem({ title: "price: $10 (50%)" });
    const { container } = renderWithRouter(<TaskCard task={task} highlightKeyword="$10" />);
    const marks = container.querySelectorAll("mark");
    expect(marks.length).toBe(1);
    expect(marks[0].textContent).toBe("$10");
  });

  it("Unicode 大小写边界：原始索引安全，精确高亮不污染", () => {
    const task = createTaskItem({ title: "Straße strasse" });
    const { container } = renderWithRouter(<TaskCard task={task} highlightKeyword="straße" />);
    const marks = container.querySelectorAll("mark");
    // matchAll 在原始文本上匹配，精确匹配到 "Straße"
    expect(marks.length).toBe(1);
    expect(marks[0].textContent).toBe("Straße");
    // 确认 "strasse" 未被误高亮——任何 mark 内都不包含 "strasse"
    for (const m of marks) {
      expect(m.textContent).not.toBe("strasse");
    }
  });
});
