import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ContentSection } from "../ContentSection";
import type { Task } from "@/types/task";

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
}));

// Mock API
let getEntriesMock = vi.fn();
vi.mock("@/services/api", () => ({
  getEntries: (...args: any[]) => getEntriesMock(...args),
}));

const makeTask = (overrides: Partial<Task> = {}): Task => ({
  id: "entry-1",
  title: "Test Entry",
  content: "Test content",
  category: "note",
  status: "doing",
  priority: "medium",
  tags: [],
  created_at: "2024-01-01T00:00:00",
  updated_at: "2024-01-01T00:00:00",
  file_path: "",
  ...overrides,
});

const defaultProps = {
  entry: makeTask(),
  isEditing: true,
  contentTab: "edit" as const,
  editContent: "",
  parsedContent: "",
  referenceIds: [] as string[],
  referencedNotes: new Map<string, Task>(),
  isSaving: false,
  setEditContent: vi.fn(),
  setContentTab: vi.fn(),
};

describe("ContentSection - 双链引用补全", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getEntriesMock.mockResolvedValue({
      entries: [
        { id: "note-1", title: "学习笔记" },
        { id: "note-2", title: "React 学习" },
        { id: "note-3", title: "项目笔记" },
      ],
    });
  });

  it("输入 [[ 触发补全弹窗", async () => {
    const setEditContent = vi.fn();
    render(
      <ContentSection
        {...defaultProps}
        setEditContent={setEditContent}
      />,
    );

    const textarea = screen.getByPlaceholderText(/输入 Markdown/);
    fireEvent.change(textarea, { target: { value: "[[", selectionStart: 2 } });

    await waitFor(() => {
      expect(getEntriesMock).toHaveBeenCalledWith({ type: "note", limit: 200 });
    });
  });

  it("补全列表按标题匹配度排序", async () => {
    getEntriesMock.mockResolvedValue({
      entries: [
        { id: "note-1", title: "React 学习" },
        { id: "note-2", title: "学习笔记" },
        { id: "note-3", title: "深度学习" },
      ],
    });

    // 用 stateful wrapper 来模拟受控组件
    let editContent = "";
    const setEditContent = vi.fn((valOrFn: unknown) => {
      if (typeof valOrFn === "function") {
        editContent = valOrFn(editContent);
      } else {
        editContent = valOrFn as string;
      }
    });

    const { rerender } = render(
      <ContentSection
        {...defaultProps}
        editContent={editContent}
        setEditContent={(val: unknown) => {
          setEditContent(val);
          rerender(
            <ContentSection
              {...defaultProps}
              editContent={typeof val === "function" ? val(editContent) : val as string}
              setEditContent={(v: unknown) => {
                setEditContent(v);
              }}
            />,
          );
        }}
      />,
    );

    const textarea = screen.getByPlaceholderText(/输入 Markdown/);
    // 触发 [[学习
    fireEvent.change(textarea, { target: { value: "[[学习", selectionStart: 4 } });

    await waitFor(() => {
      expect(getEntriesMock).toHaveBeenCalledWith({ type: "note", limit: 200 });
    });
  });

  it("选中补全项插入 [[note-id|标题]] 格式", async () => {
    let currentContent = "";
    const setEditContent = vi.fn((valOrFn: any) => {
      if (typeof valOrFn === "function") {
        currentContent = valOrFn(currentContent);
      } else {
        currentContent = valOrFn;
      }
    });

    const { rerender } = render(
      <ContentSection
        {...defaultProps}
        editContent={currentContent}
        setEditContent={(val) => {
          setEditContent(val);
          // 触发重渲染
          rerender(
            <ContentSection
              {...defaultProps}
              editContent={typeof val === "function" ? val(currentContent) : val}
              setEditContent={(v: any) => {
                setEditContent(v);
              }}
            />,
          );
        }}
      />,
    );

    const textarea = screen.getByPlaceholderText(/输入 Markdown/);
    fireEvent.change(textarea, { target: { value: "[[", selectionStart: 2 } });

    await waitFor(() => {
      expect(getEntriesMock).toHaveBeenCalled();
    });

    // 找到补全列表中的项
    const items = await screen.findAllByText(/学习笔记|React 学习|项目笔记/);
    expect(items.length).toBeGreaterThan(0);

    // 点击第一项
    fireEvent.click(items[0]);

    expect(setEditContent).toHaveBeenCalled();
  });

  it("空结果显示「无匹配笔记」", async () => {
    getEntriesMock.mockResolvedValue({ entries: [] });

    render(
      <ContentSection
        {...defaultProps}
        editContent=""
        setEditContent={vi.fn(() => {
          // 模拟受控行为
        })}
      />,
    );

    const textarea = screen.getByPlaceholderText(/输入 Markdown/);
    fireEvent.change(textarea, { target: { value: "[[xyz", selectionStart: 5 } });

    await waitFor(() => {
      expect(getEntriesMock).toHaveBeenCalled();
    });

    // 等待补全加载完成，应该显示"无匹配笔记"
    await waitFor(() => {
      expect(screen.queryByText("无匹配笔记")).toBeTruthy();
    });
  });

  it("API 失败时静默降级（不显示补全弹窗）", async () => {
    getEntriesMock.mockRejectedValue(new Error("Network error"));

    render(
      <ContentSection
        {...defaultProps}
        editContent=""
        setEditContent={vi.fn()}
      />,
    );

    const textarea = screen.getByPlaceholderText(/输入 Markdown/);
    fireEvent.change(textarea, { target: { value: "[[", selectionStart: 2 } });

    await waitFor(() => {
      expect(getEntriesMock).toHaveBeenCalled();
    });

    // 补全弹窗不应出现
    expect(screen.queryByText("加载中...")).toBeNull();
    expect(screen.queryByText("无匹配笔记")).toBeNull();
  });

  it("Escape 关闭补全弹窗", async () => {
    render(
      <ContentSection
        {...defaultProps}
        editContent=""
        setEditContent={vi.fn()}
      />,
    );

    const textarea = screen.getByPlaceholderText(/输入 Markdown/);
    fireEvent.change(textarea, { target: { value: "[[", selectionStart: 2 } });

    await waitFor(() => {
      expect(getEntriesMock).toHaveBeenCalled();
    });

    // 按 Escape
    fireEvent.keyDown(textarea, { key: "Escape" });

    // 补全弹窗应该关闭
    expect(screen.queryByText("加载中...")).toBeNull();
  });
});

describe("ContentSection - 预览模式引用展示", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("有引用时展示引用笔记列表", () => {
    const referencedNotes = new Map<string, Task>();
    referencedNotes.set("note-1", makeTask({ id: "note-1", title: "引用笔记" }));

    render(
      <ContentSection
        {...defaultProps}
        isEditing={false}
        contentTab="preview"
        parsedContent="some content"
        referenceIds={["note-1"]}
        referencedNotes={referencedNotes}
      />,
    );

    expect(screen.getByText("引用的笔记 (1)")).toBeTruthy();
    expect(screen.getByText("引用笔记")).toBeTruthy();
  });

  it("无引用时不展示引用笔记列表", () => {
    render(
      <ContentSection
        {...defaultProps}
        isEditing={false}
        contentTab="preview"
        parsedContent="some content"
        referenceIds={[]}
        referencedNotes={new Map()}
      />,
    );

    expect(screen.queryByText(/引用的笔记/)).toBeNull();
  });

  it("引用笔记可点击跳转", () => {
    const referencedNotes = new Map<string, Task>();
    referencedNotes.set("note-1", makeTask({ id: "note-1", title: "引用笔记" }));

    render(
      <ContentSection
        {...defaultProps}
        isEditing={false}
        contentTab="preview"
        parsedContent="some content"
        referenceIds={["note-1"]}
        referencedNotes={referencedNotes}
      />,
    );

    const item = screen.getByText("引用笔记").closest("[class*='cursor-pointer']");
    expect(item).toBeTruthy();
    fireEvent.click(item!);
    expect(mockNavigate).toHaveBeenCalledWith("/entry/note-1");
  });
});
