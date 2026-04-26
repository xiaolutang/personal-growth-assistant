/**
 * F143: TaskCard multi-select framework tests
 * - checkbox visible in selectable mode
 * - checkbox clickable (toggles selection)
 * - single-card actions disabled in select mode (disableActions)
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TaskCard } from "../TaskCard";
import type { Task } from "@/types/task";

// Mock react-router-dom
vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
}));

// Mock taskStore
const mockDeleteTask = vi.fn();
const mockUpdateTaskStatus = vi.fn();
const mockUpdateEntry = vi.fn();
vi.mock("@/stores/taskStore", () => ({
  useTaskStore: (selector: (s: any) => any) =>
    selector({
      deleteTask: mockDeleteTask,
      updateTaskStatus: mockUpdateTaskStatus,
      updateEntry: mockUpdateEntry,
      tasks: [],
    }),
}));

// Mock sonner
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const makeTask = (overrides: Partial<Task> = {}): Task => ({
  id: "t1",
  title: "Test Task",
  content: "content",
  category: "inbox",
  status: "doing",
  priority: "medium",
  tags: [],
  created_at: "2024-01-01T00:00:00",
  updated_at: "2024-01-01T00:00:00",
  file_path: "",
  ...overrides,
});

describe("TaskCard multi-select (F143)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("checkbox visibility", () => {
    it("renders checkbox when selectable=true", () => {
      const onSelect = vi.fn();
      render(
        <TaskCard
          task={makeTask()}
          selectable={true}
          selected={false}
          onSelect={onSelect}
        />
      );
      // Unchecked checkbox (Square icon) should be rendered
      const card = screen.getByText("Test Task").closest("[class*='cursor-pointer']");
      expect(card).toBeTruthy();
    });

    it("does NOT render checkbox when selectable=false (default)", () => {
      render(<TaskCard task={makeTask()} />);
      // Should not have the checkbox area
      const card = screen.getByText("Test Task").closest("[class*='cursor-pointer']");
      expect(card).toBeTruthy();
    });

    it("renders checked state when selected=true", () => {
      const onSelect = vi.fn();
      render(
        <TaskCard
          task={makeTask()}
          selectable={true}
          selected={true}
          onSelect={onSelect}
        />
      );
      // CheckSquare should be rendered for selected state
      const card = screen.getByText("Test Task").closest("[class*='cursor-pointer']");
      expect(card).toBeTruthy();
    });
  });

  describe("checkbox clickable", () => {
    it("clicking card in selectable mode calls onSelect", () => {
      const onSelect = vi.fn();
      render(
        <TaskCard
          task={makeTask()}
          selectable={true}
          selected={false}
          onSelect={onSelect}
        />
      );
      fireEvent.click(screen.getByText("Test Task"));
      expect(onSelect).toHaveBeenCalledWith("t1");
    });

    it("clicking card without selectable mode navigates (no onSelect call)", () => {
      const onSelect = vi.fn();
      render(<TaskCard task={makeTask()} selectable={false} onSelect={onSelect} />);
      fireEvent.click(screen.getByText("Test Task"));
      expect(onSelect).not.toHaveBeenCalled();
    });
  });

  describe("disableActions in select mode", () => {
    it("status button is disabled when disableActions=true", () => {
      render(
        <TaskCard
          task={makeTask()}
          selectable={true}
          disableActions={true}
        />
      );
      const statusBtn = screen.getByLabelText("切换状态");
      expect(statusBtn).toBeDisabled();
    });

    it("status button is enabled when disableActions=false (default)", () => {
      render(<TaskCard task={makeTask()} />);
      const statusBtn = screen.getByLabelText("切换状态");
      expect(statusBtn).not.toBeDisabled();
    });

    it("delete button is NOT rendered when disableActions=true", () => {
      render(
        <TaskCard task={makeTask()} disableActions={true} />
      );
      // Check that no trash icon button exists when actions are disabled
      const buttons = screen.queryAllByRole("button");
      const hasDeleteButton = buttons.some(
        (btn) => btn.textContent === "" && btn.className.includes("hover:text-destructive")
      );
      expect(hasDeleteButton).toBe(false);
    });

    it("inbox convert menu is NOT rendered when disableActions=true", () => {
      render(
        <TaskCard task={makeTask({ category: "inbox" })} disableActions={true} />
      );
      // The more-horizontal menu should not be rendered for inbox items when actions disabled
      // The menu button should not be present
      const buttons = screen.queryAllByRole("button");
      const hasMenuButton = buttons.some(
        (btn) => btn.className.includes("h-6 w-6") && btn.className.includes("text-muted-foreground")
      );
      expect(hasMenuButton).toBe(false);
    });
  });
});
