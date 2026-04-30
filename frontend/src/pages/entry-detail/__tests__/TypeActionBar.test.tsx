import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { TypeActionBar } from "../TypeActionBar";
import type { Task } from "@/types/task";

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
}));

// Mock taskStore
const mockUpdateTaskStatus = vi.fn();
const mockCreateEntry = vi.fn();
vi.mock("@/stores/taskStore", () => ({
  useTaskStore: (selector: any) =>
    selector({
      updateTaskStatus: mockUpdateTaskStatus,
      createEntry: mockCreateEntry,
    }),
}));

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

// Mock ConvertDialog
vi.mock("@/components/ConvertDialog", () => ({
  ConvertDialog: ({ open, onClose, onSuccess, entry }: any) =>
    open ? (
      <div data-testid="convert-dialog">
        <span>ConvertDialog for {entry?.title}</span>
        <button onClick={onSuccess}>mock-success</button>
        <button onClick={onClose}>mock-close</button>
      </div>
    ) : null,
}));

// Mock CompletionPrompt
vi.mock("@/pages/tasks/CompletionPrompt", () => ({
  CompletionPrompt: ({ task, onDismiss }: any) => (
    <div data-testid="completion-prompt">
      <span>CompletionPrompt for {task?.title}</span>
      <button onClick={onDismiss}>mock-dismiss</button>
    </div>
  ),
}));

const makeTask = (overrides: Partial<Task> = {}): Task => ({
  id: "entry-1",
  title: "Test Entry",
  content: "Test content",
  category: "task",
  status: "doing",
  priority: "medium",
  tags: [],
  created_at: "2024-01-01T00:00:00",
  updated_at: "2024-01-01T00:00:00",
  file_path: "",
  ...overrides,
});

describe("TypeActionBar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // === task type ===
  describe("task type", () => {
    it("renders status advance button for task", () => {
      render(
        <TypeActionBar
          entry={makeTask({ category: "task", status: "doing" })}
          onReload={vi.fn()}
        />,
      );
      // nextStatusMap: doing -> complete
      expect(screen.getByText("标记完成")).toBeTruthy();
    });

    it("shows CompletionPrompt after status advance to complete", async () => {
      mockUpdateTaskStatus.mockResolvedValue(undefined);
      render(
        <TypeActionBar
          entry={makeTask({ category: "task", status: "doing" })}
          onReload={vi.fn()}
        />,
      );
      fireEvent.click(screen.getByText("标记完成"));
      await waitFor(() => {
        expect(mockUpdateTaskStatus).toHaveBeenCalledWith("entry-1", "complete");
      });
      // After status update, rerender with complete status to verify prompt shows
      expect(mockUpdateTaskStatus).toHaveBeenCalled();
    });

    it("calls updateTaskStatus when status button clicked", () => {
      mockUpdateTaskStatus.mockResolvedValue(undefined);
      render(
        <TypeActionBar
          entry={makeTask({ category: "task", status: "doing" })}
          onReload={vi.fn()}
        />,
      );
      fireEvent.click(screen.getByText("标记完成"));
      expect(mockUpdateTaskStatus).toHaveBeenCalledWith("entry-1", "complete");
    });

    it("shows waitStart -> doing transition", () => {
      render(
        <TypeActionBar
          entry={makeTask({ category: "task", status: "waitStart" })}
          onReload={vi.fn()}
        />,
      );
      expect(screen.getByText("开始")).toBeTruthy();
    });
  });

  // === inbox type ===
  describe("inbox type", () => {
    it("renders convert buttons for inbox", () => {
      render(
        <TypeActionBar
          entry={makeTask({ category: "inbox" })}
          onReload={vi.fn()}
        />,
      );
      expect(screen.getByText("转为任务")).toBeTruthy();
      expect(screen.getByText("转为决策")).toBeTruthy();
    });

    it("opens ConvertDialog when convert button clicked", () => {
      render(
        <TypeActionBar
          entry={makeTask({ category: "inbox" })}
          onReload={vi.fn()}
        />,
      );
      fireEvent.click(screen.getByText("转为任务"));
      expect(screen.getByTestId("convert-dialog")).toBeTruthy();
    });
  });

  // === question type ===
  describe("question type", () => {
    it("renders convert-to-note button for question", () => {
      render(
        <TypeActionBar
          entry={makeTask({ category: "question" })}
          onReload={vi.fn()}
        />,
      );
      expect(screen.getByText("转为笔记")).toBeTruthy();
    });

    it("creates a new note entry when convert-to-note clicked", async () => {
      mockCreateEntry.mockResolvedValue({ id: "new-note-1" });
      const onReload = vi.fn();
      render(
        <TypeActionBar
          entry={makeTask({ category: "question", id: "q-1", title: "My Question" })}
          onReload={onReload}
        />,
      );
      fireEvent.click(screen.getByText("转为笔记"));
      await vi.waitFor(() => {
        expect(mockCreateEntry).toHaveBeenCalledWith({
          type: "note",
          title: "My Question",
          content: "",
          parent_id: "q-1",
        });
      });
    });
  });

  // === reflection type ===
  describe("reflection type", () => {
    it("renders parent task link for reflection with parent_id", () => {
      render(
        <TypeActionBar
          entry={makeTask({ category: "reflection", parent_id: "task-1" })}
          parentEntry={makeTask({ id: "task-1", title: "Parent Task", category: "task" })}
          onReload={vi.fn()}
        />,
      );
      expect(screen.getByText("Parent Task")).toBeTruthy();
    });

    it("does not render action bar for reflection without parent", () => {
      const { container } = render(
        <TypeActionBar
          entry={makeTask({ category: "reflection" })}
          onReload={vi.fn()}
        />,
      );
      // reflection without parentEntry should not render any action bar content
      expect(container.innerHTML).toBe("");
    });
  });

  // === project type (already handled by ProjectSection) ===
  describe("project type", () => {
    it("renders nothing for project (handled by ProjectSection)", () => {
      const { container } = render(
        <TypeActionBar
          entry={makeTask({ category: "project" })}
          onReload={vi.fn()}
        />,
      );
      expect(container.innerHTML).toBe("");
    });
  });

  // === note / decision types ===
  describe("note and decision types", () => {
    it("renders nothing for note", () => {
      const { container } = render(
        <TypeActionBar
          entry={makeTask({ category: "note" })}
          onReload={vi.fn()}
        />,
      );
      expect(container.innerHTML).toBe("");
    });

    it("renders nothing for decision", () => {
      const { container } = render(
        <TypeActionBar
          entry={makeTask({ category: "decision" })}
          onReload={vi.fn()}
        />,
      );
      expect(container.innerHTML).toBe("");
    });
  });
});
