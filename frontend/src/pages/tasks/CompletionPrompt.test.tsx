import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { CompletionPrompt } from "./CompletionPrompt";
import type { Task } from "@/types/task";

// Mock sonner
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
  Toaster: () => null,
}));

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
}));

// Mock taskStore
const mockCreateEntry = vi.fn();
vi.mock("@/stores/taskStore", () => ({
  useTaskStore: (selector: (state: Record<string, unknown>) => unknown) => {
    const state = { createEntry: mockCreateEntry };
    return selector(state);
  },
}));

import { toast } from "sonner";

function createTask(overrides: Partial<Task> = {}): Task {
  return {
    id: "task-abc123",
    title: "完成项目设计",
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

describe("CompletionPrompt", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("task 状态变为 complete 时显示复盘提示", () => {
    render(
      <CompletionPrompt
        task={createTask({ status: "complete" })}
        onDismiss={vi.fn()}
      />
    );
    expect(screen.getByText("写个复盘？")).toBeInTheDocument();
    expect(screen.getByText("写复盘")).toBeInTheDocument();
    expect(screen.getByText("跳过")).toBeInTheDocument();
  });

  it("非 complete 状态不显示提示", () => {
    const { container } = render(
      <CompletionPrompt
        task={createTask({ status: "doing" })}
        onDismiss={vi.fn()}
      />
    );
    expect(container.innerHTML).toBe("");
  });

  it("点击「写复盘」创建 reflection 条目并跳转", async () => {
    const user = userEvent.setup();
    const onDismiss = vi.fn();
    const newReflection = { id: "reflection-new123", title: "关于「完成项目设计」的复盘" };

    mockCreateEntry.mockResolvedValueOnce(newReflection);

    render(
      <CompletionPrompt
        task={createTask({ status: "complete" })}
        onDismiss={onDismiss}
      />
    );

    await user.click(screen.getByText("写复盘"));

    await waitFor(() => {
      expect(mockCreateEntry).toHaveBeenCalledWith({
        type: "reflection",
        title: "关于「完成项目设计」的复盘",
        parent_id: "task-abc123",
      });
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith(
        "/explore?type=reflection&entry_id=reflection-new123"
      );
    });

    expect(onDismiss).toHaveBeenCalled();
  });

  it("点击「跳过」关闭提示，不创建条目", async () => {
    const user = userEvent.setup();
    const onDismiss = vi.fn();

    render(
      <CompletionPrompt
        task={createTask({ status: "complete" })}
        onDismiss={onDismiss}
      />
    );

    await user.click(screen.getByText("跳过"));

    expect(mockCreateEntry).not.toHaveBeenCalled();
    expect(onDismiss).toHaveBeenCalled();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("创建 reflection 失败时 toast 提示", async () => {
    const user = userEvent.setup();
    const onDismiss = vi.fn();

    mockCreateEntry.mockRejectedValueOnce(new Error("API error"));

    render(
      <CompletionPrompt
        task={createTask({ status: "complete" })}
        onDismiss={onDismiss}
      />
    );

    await user.click(screen.getByText("写复盘"));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("创建复盘失败，请重试");
    });

    // Should not navigate on failure
    expect(mockNavigate).not.toHaveBeenCalled();
    // onDismiss should not be called on failure so user can retry
    expect(onDismiss).not.toHaveBeenCalled();
  });

  it("创建中显示 loading 状态", async () => {
    const user = userEvent.setup();
    let resolveCreate: (value: unknown) => void;
    mockCreateEntry.mockReturnValueOnce(new Promise((resolve) => { resolveCreate = resolve; }));

    render(
      <CompletionPrompt
        task={createTask({ status: "complete" })}
        onDismiss={vi.fn()}
      />
    );

    await user.click(screen.getByText("写复盘"));

    // Should show loading indicator
    expect(screen.getByText("创建中...")).toBeInTheDocument();

    // Resolve to clean up
    resolveCreate!({ id: "reflection-1" });
    await waitFor(() => {
      expect(screen.queryByText("创建中...")).not.toBeInTheDocument();
    });
  });
});
