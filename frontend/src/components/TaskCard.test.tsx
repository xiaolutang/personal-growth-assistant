import { describe, it, expect, vi, beforeEach } from "vitest";
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

// Mock taskStore selectors
const mockUpdateEntry = vi.fn();
const mockUpdateTaskStatus = vi.fn();
const mockDeleteTask = vi.fn();
const mockTasks: Task[] = [];

vi.mock("@/stores/taskStore", () => ({
  useTaskStore: (selector: (state: Record<string, unknown>) => unknown) => {
    const state = {
      updateEntry: mockUpdateEntry,
      updateTaskStatus: mockUpdateTaskStatus,
      deleteTask: mockDeleteTask,
      tasks: mockTasks,
    };
    return selector(state);
  },
}));

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
  });

  it("inbox 条目应显示更多操作按钮", () => {
    renderWithRouter(<TaskCard task={createInboxTask()} />);
    // 查找包含 MoreHorizontal 图标的按钮区域
    const buttons = screen.getAllByRole("button");
    // inbox 条目应该有：状态切换按钮 + 菜单按钮 + 删除按钮 = 3 个按钮
    expect(buttons.length).toBeGreaterThanOrEqual(3);
  });

  it("非 inbox 条目不显示转化菜单", () => {
    const { container } = renderWithRouter(<TaskCard task={createTaskItem()} />);
    // 不应出现"转为任务"或"转为笔记"文本
    expect(container.textContent).not.toContain("转为任务");
    expect(container.textContent).not.toContain("转为笔记");
  });

  it("点击菜单按钮显示「转为任务」和「转为笔记」选项", async () => {
    const user = userEvent.setup();
    renderWithRouter(<TaskCard task={createInboxTask()} />);

    // 点击第二个按钮（菜单按钮）
    const buttons = screen.getAllByRole("button");
    // 状态切换=buttons[0], 菜单按钮=buttons[1]（在删除按钮前面）
    await user.click(buttons[1]);

    expect(screen.getByText("转为任务")).toBeInTheDocument();
    expect(screen.getByText("转为笔记")).toBeInTheDocument();
  });

  it("点击「转为任务」调用 updateEntry 并显示成功 toast", async () => {
    mockUpdateEntry.mockResolvedValueOnce(undefined);
    const user = userEvent.setup();
    renderWithRouter(<TaskCard task={createInboxTask()} />);

    const buttons = screen.getAllByRole("button");
    await user.click(buttons[1]); // 打开菜单
    await user.click(screen.getByText("转为任务"));

    expect(mockUpdateEntry).toHaveBeenCalledWith("inbox-test123", { category: "task" });
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("已转为任务：测试灵感");
    });
  });

  it("点击「转为笔记」调用 updateEntry 并显示成功 toast", async () => {
    mockUpdateEntry.mockResolvedValueOnce(undefined);
    const user = userEvent.setup();
    renderWithRouter(<TaskCard task={createInboxTask()} />);

    const buttons = screen.getAllByRole("button");
    await user.click(buttons[1]);
    await user.click(screen.getByText("转为笔记"));

    expect(mockUpdateEntry).toHaveBeenCalledWith("inbox-test123", { category: "note" });
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("已转为笔记：测试灵感");
    });
  });

  it("转化失败显示错误 toast", async () => {
    mockUpdateEntry.mockRejectedValueOnce(new Error("API error"));
    const user = userEvent.setup();
    renderWithRouter(<TaskCard task={createInboxTask()} />);

    const buttons = screen.getAllByRole("button");
    await user.click(buttons[1]);
    await user.click(screen.getByText("转为任务"));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("转化失败，请重试");
    });
  });

  it("点击菜单按钮不触发卡片导航", async () => {
    const user = userEvent.setup();
    renderWithRouter(<TaskCard task={createInboxTask()} />);

    const buttons = screen.getAllByRole("button");
    await user.click(buttons[1]);

    // 菜单按钮点击后不应触发导航（卡片点击才导航）
    // 验证菜单打开而非导航
    expect(screen.getByText("转为任务")).toBeInTheDocument();
  });

  it("转化过程中显示 loading 图标", async () => {
    // 让 updateEntry 永远 pending
    mockUpdateEntry.mockReturnValueOnce(new Promise(() => {}));
    const user = userEvent.setup();
    renderWithRouter(<TaskCard task={createInboxTask()} />);

    const buttons = screen.getAllByRole("button");
    await user.click(buttons[1]); // 打开菜单
    await user.click(screen.getByText("转为任务"));

    // 转化中，菜单按钮应变为 disabled（Loader2 图标）
    const menuBtn = buttons[1];
    expect(menuBtn).toBeDisabled();
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
