import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { TemplateSelector } from "../TemplateSelector";
import type { EntryTemplate } from "@/services/api";

// Mock fetchTemplates
vi.mock("@/services/api", () => ({
  fetchTemplates: vi.fn(),
}));

import { fetchTemplates } from "@/services/api";
const mockFetchTemplates = vi.mocked(fetchTemplates);

const mockTemplates: EntryTemplate[] = [
  {
    id: "learning",
    name: "学习笔记",
    category: "note",
    description: "记录学习内容和心得",
    content: "# 学习笔记\n\n## 今日学习\n\n\n## 心得体会\n",
  },
  {
    id: "reading",
    name: "读书笔记",
    category: "note",
    description: "记录阅读的书籍内容",
    content: "# 读书笔记\n\n## 书名\n\n\n## 核心观点\n",
  },
  {
    id: "meeting",
    name: "会议记录",
    category: "note",
    description: "记录会议内容和决议",
    content: "# 会议记录\n\n## 参会人\n\n\n## 议题\n",
  },
];

describe("TemplateSelector", () => {
  const mockOnTemplateSelected = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchTemplates.mockResolvedValue({ templates: mockTemplates });
  });

  it("模板列表正确渲染", async () => {
    render(
      <TemplateSelector activeTab="note" onTemplateSelected={mockOnTemplateSelected} />
    );

    await waitFor(() => {
      expect(screen.getByText("学习笔记")).toBeInTheDocument();
      expect(screen.getByText("读书笔记")).toBeInTheDocument();
      expect(screen.getByText("会议记录")).toBeInTheDocument();
    });
  });

  it("选择模板后回调 onTemplateSelected", async () => {
    render(
      <TemplateSelector activeTab="note" onTemplateSelected={mockOnTemplateSelected} />
    );

    await waitFor(() => {
      expect(screen.getByText("学习笔记")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("学习笔记"));
    expect(mockOnTemplateSelected).toHaveBeenCalledTimes(1);
    expect(mockOnTemplateSelected).toHaveBeenCalledWith(mockTemplates[0]);
  });

  it("非 note 类型不显示模板选择器", async () => {
    const { container } = render(
      <TemplateSelector activeTab="inbox" onTemplateSelected={mockOnTemplateSelected} />
    );
    expect(container.innerHTML).toBe("");
    expect(mockFetchTemplates).not.toHaveBeenCalled();
  });

  it("不选择模板时默认行为不变", async () => {
    render(
      <TemplateSelector activeTab="note" onTemplateSelected={mockOnTemplateSelected} />
    );

    await waitFor(() => {
      expect(screen.getByText("学习笔记")).toBeInTheDocument();
    });

    // 没有点击任何模板，回调不应被调用
    expect(mockOnTemplateSelected).not.toHaveBeenCalled();
  });

  it("模板 API 失败时静默降级（不阻塞创建流程）", async () => {
    mockFetchTemplates.mockRejectedValue(new Error("Network error"));

    const { container } = render(
      <TemplateSelector activeTab="note" onTemplateSelected={mockOnTemplateSelected} />
    );

    await waitFor(() => {
      expect(mockFetchTemplates).toHaveBeenCalledWith("note");
    });

    // 失败后不应有模板渲染，也不应崩溃
    expect(container.querySelectorAll("button").length).toBe(0);
  });

  it("模板列表为空时创建流程正常", async () => {
    mockFetchTemplates.mockResolvedValue({ templates: [] });

    const { container } = render(
      <TemplateSelector activeTab="note" onTemplateSelected={mockOnTemplateSelected} />
    );

    await waitFor(() => {
      expect(mockFetchTemplates).toHaveBeenCalledWith("note");
    });

    // 空模板列表不应渲染任何内容
    expect(container.querySelectorAll("button").length).toBe(0);
  });

  it("切换 category 后模板选择器正确显隐", async () => {
    const { rerender, container } = render(
      <TemplateSelector activeTab="note" onTemplateSelected={mockOnTemplateSelected} />
    );

    await waitFor(() => {
      expect(screen.getByText("学习笔记")).toBeInTheDocument();
    });

    // 切换到非 note 类型
    rerender(
      <TemplateSelector activeTab="task" onTemplateSelected={mockOnTemplateSelected} />
    );

    // 模板选择器应消失
    expect(container.innerHTML).toBe("");
  });

  it("已有 content 时重新选择模板不覆盖（再次点击同一模板取消选择）", async () => {
    render(
      <TemplateSelector activeTab="note" onTemplateSelected={mockOnTemplateSelected} />
    );

    await waitFor(() => {
      expect(screen.getByText("学习笔记")).toBeInTheDocument();
    });

    // 第一次点击选择模板
    fireEvent.click(screen.getByText("学习笔记"));
    expect(mockOnTemplateSelected).toHaveBeenCalledWith(mockTemplates[0]);

    // 再次点击同一模板取消选择
    mockOnTemplateSelected.mockClear();
    fireEvent.click(screen.getByText("学习笔记"));
    expect(mockOnTemplateSelected).not.toHaveBeenCalled();
  });
});
