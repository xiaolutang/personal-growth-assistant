/**
 * F141: TaskCard content snippet tests
 * - Snippet display: shown in search mode, hidden in normal mode, truncated at 100 chars
 * - Keyword highlight: matches highlighted, multiple matches highlighted, no match plain text
 * - UTF-8 safety: multi-byte chars not truncated, emoji not truncated
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { TaskCard, safeTruncate } from "../TaskCard";
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
  content: "content body text",
  category: "inbox",
  status: "doing",
  priority: "medium",
  tags: [],
  created_at: "2024-01-01T00:00:00",
  updated_at: "2024-01-01T00:00:00",
  file_path: "",
  ...overrides,
});

// ============================================================
// safeTruncate unit tests
// ============================================================
describe("safeTruncate", () => {
  it("returns original text when shorter than maxLen", () => {
    expect(safeTruncate("hello", 10)).toBe("hello");
  });

  it("returns original text when equal to maxLen", () => {
    expect(safeTruncate("hello", 5)).toBe("hello");
  });

  it("truncates and appends ellipsis when longer", () => {
    expect(safeTruncate("hello world foo bar", 5)).toBe("hello...");
  });

  it("does not truncate multi-byte CJK characters in the middle", () => {
    const text = "你好世界这是一个测试文本用来验证截取";
    const result = safeTruncate(text, 6);
    // Should be exactly 6 CJK chars + "..." (Array.from respects code points)
    expect(result).toBe("你好世界这是...");
    // Verify no partial characters
    expect([...result.replace("...", "")].length).toBe(6);
  });

  it("does not truncate emoji in the middle", () => {
    const text = "Hello 😀😎🤩🎉🔥 World";
    const result = safeTruncate(text, 8);
    const withoutEllipsis = result.replace("...", "");
    // Each emoji is one grapheme cluster via Array.from
    const chars = [...withoutEllipsis];
    expect(chars.length).toBe(8);
    // Verify no partial emoji - each emoji should be intact
    expect(chars).toContain("😀");
  });

  it("handles mixed ASCII and CJK correctly", () => {
    const text = "abc你好def世界";
    const result = safeTruncate(text, 5);
    expect(result).toBe("abc你好...");
  });
});

// ============================================================
// Snippet display in TaskCard
// ============================================================
describe("TaskCard snippet display (F141)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows snippet in search mode with highlightKeyword", () => {
    render(
      <TaskCard
        task={makeTask({ content: "This is the body content of the entry" })}
        highlightKeyword="body"
      />
    );
    expect(screen.getByText("body")).toBeTruthy();
    // The mark element should wrap the keyword
    const mark = document.querySelector("mark");
    expect(mark).toBeTruthy();
    expect(mark?.textContent).toBe("body");
  });

  it("does NOT show snippet when highlightKeyword is not provided (normal mode)", () => {
    render(
      <TaskCard
        task={makeTask({ content: "This is the body content of the entry" })}
      />
    );
    // No mark element should exist
    expect(document.querySelector("mark")).toBeNull();
    // The snippet paragraph should not be rendered
    const snippetEl = screen.queryByText(/body content/i);
    expect(snippetEl).toBeNull();
  });

  it("does NOT show snippet when highlightKeyword is empty string", () => {
    render(
      <TaskCard
        task={makeTask({ content: "Some content here" })}
        highlightKeyword=""
      />
    );
    expect(document.querySelector("mark")).toBeNull();
  });

  it("prefers content_snippet over content when both exist", () => {
    render(
      <TaskCard
        task={makeTask({
          content_snippet: "snippet text from backend",
          content: "full content text here",
        })}
        highlightKeyword="snippet"
      />
    );
    const mark = document.querySelector("mark");
    expect(mark).toBeTruthy();
    expect(mark?.textContent).toBe("snippet");
    // Should not show "full content"
    expect(screen.queryByText(/full content/i)).toBeNull();
  });

  it("falls back to content when content_snippet is empty", () => {
    render(
      <TaskCard
        task={makeTask({
          content_snippet: "",
          content: "fallback content text",
        })}
        highlightKeyword="fallback"
      />
    );
    const mark = document.querySelector("mark");
    expect(mark).toBeTruthy();
    expect(mark?.textContent).toBe("fallback");
  });

  it("does not render snippet when both content and content_snippet are empty", () => {
    render(
      <TaskCard
        task={makeTask({ content: "", content_snippet: "" })}
        highlightKeyword="search"
      />
    );
    // No mark, and no extra paragraph
    expect(document.querySelector("mark")).toBeNull();
  });
});

// ============================================================
// Keyword highlighting
// ============================================================
describe("TaskCard keyword highlighting (F141)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("highlights matching keyword in snippet", () => {
    render(
      <TaskCard
        task={makeTask({ content: "React hooks are powerful" })}
        highlightKeyword="React"
      />
    );
    const marks = document.querySelectorAll("mark");
    expect(marks.length).toBeGreaterThanOrEqual(1);
    expect(marks[0].textContent).toBe("React");
  });

  it("highlights multiple occurrences of the keyword", () => {
    render(
      <TaskCard
        task={makeTask({ content: "test test test more test" })}
        highlightKeyword="test"
      />
    );
    const marks = document.querySelectorAll("mark");
    // Title "Test Task" has 1 match ("Test") + snippet has 4 matches = 5 total
    expect(marks.length).toBe(5);
  });

  it("highlights case-insensitively", () => {
    render(
      <TaskCard
        task={makeTask({ content: "React REACT react" })}
        highlightKeyword="react"
      />
    );
    const marks = document.querySelectorAll("mark");
    expect(marks.length).toBe(3);
    expect(marks[0].textContent).toBe("React");
    expect(marks[1].textContent).toBe("REACT");
    expect(marks[2].textContent).toBe("react");
  });

  it("renders plain text when no keyword matches", () => {
    render(
      <TaskCard
        task={makeTask({ content: "Hello world" })}
        highlightKeyword="xyz"
      />
    );
    expect(document.querySelectorAll("mark").length).toBe(0);
    // The snippet text should still be rendered (without mark, no ellipsis since < 100 chars)
    expect(screen.getByText("Hello world", { exact: false })).toBeTruthy();
  });
});

// ============================================================
// UTF-8 safety in snippet rendering
// ============================================================
describe("TaskCard UTF-8 safe snippet (F141)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders CJK snippet without broken characters", () => {
    const longCjk = "你好世界".repeat(30); // 120 chars
    render(
      <TaskCard
        task={makeTask({ content: longCjk })}
        highlightKeyword="你好"
      />
    );
    const snippetEl = document.querySelector(".line-clamp-2");
    expect(snippetEl).toBeTruthy();
    // Should contain the highlighted keyword
    const marks = document.querySelectorAll("mark");
    expect(marks.length).toBeGreaterThanOrEqual(1);
    // Verify no broken characters: all text content should be valid
    const text = snippetEl?.textContent ?? "";
    expect(text.length).toBeLessThan(longCjk.length);
  });

  it("renders emoji snippet without broken characters", () => {
    const emojiText = "Start 😀😎🤩🎉🔥💎🌟🍀🎈🎀🎁 End";
    render(
      <TaskCard
        task={makeTask({ content: emojiText })}
        highlightKeyword="Start"
      />
    );
    const snippetEl = document.querySelector(".line-clamp-2");
    expect(snippetEl).toBeTruthy();
    // Emojis should be rendered intact
    expect(snippetEl?.textContent).toContain("😀");
  });
});
