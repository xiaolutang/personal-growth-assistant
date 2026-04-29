import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TypeHistoryTimeline } from "../TypeHistoryTimeline";
import type { Task } from "@/types/task";

describe("TypeHistoryTimeline", () => {
  it("renders nothing when type_history is empty or undefined", () => {
    const { container } = render(
      <TypeHistoryTimeline typeHistory={undefined} />,
    );
    expect(container.innerHTML).toBe("");

    const { container: c2 } = render(
      <TypeHistoryTimeline typeHistory={[]} />,
    );
    expect(c2.innerHTML).toBe("");
  });

  it("renders timeline entries for type_history", () => {
    const history: Task["type_history"] = [
      { from_category: "inbox", to_category: "task", at: "2024-06-01T10:00:00" },
      { from_category: "task", to_category: "note", at: "2024-06-05T14:30:00" },
    ];

    render(<TypeHistoryTimeline typeHistory={history} />);

    expect(screen.getByText("类型变更记录")).toBeTruthy();
    // Verify both transitions are shown
    expect(screen.getByText(/灵感 → 任务/)).toBeTruthy();
    expect(screen.getByText(/任务 → 笔记/)).toBeTruthy();
  });

  it("formats dates correctly", () => {
    const history: Task["type_history"] = [
      { from_category: "inbox", to_category: "task", at: "2024-06-01T10:00:00" },
    ];

    render(<TypeHistoryTimeline typeHistory={history} />);

    // Should show a formatted date
    expect(screen.getByText(/2024/)).toBeTruthy();
  });

  it("shows correct category labels", () => {
    const history: Task["type_history"] = [
      { from_category: "question", to_category: "note", at: "2024-01-01T00:00:00" },
    ];

    render(<TypeHistoryTimeline typeHistory={history} />);

    // question -> 疑问, note -> 笔记 (using categoryConfig labels)
    expect(screen.getByText(/疑问 → 笔记/)).toBeTruthy();
  });
});
