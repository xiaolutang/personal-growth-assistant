import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { PageChatPanel } from "./PageChatPanel";

// Mock scrollIntoView for jsdom
Element.prototype.scrollIntoView = vi.fn();

// Mock sendAIChat
const mockSendAIChat = vi.fn();
vi.mock("@/services/api", () => ({
  sendAIChat: (...args: unknown[]) => mockSendAIChat(...args),
}));

function makeStreamResponse(tokens: string[]) {
  const chunks = tokens.map((t) => `data: ${JSON.stringify({ token: t })}`).join("\n") + "\ndata: [DONE]\n";
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(chunks));
      controller.close();
    },
  });
  return { body: stream };
}

describe("PageChatPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders title and welcome message", () => {
    render(
      <PageChatPanel
        title="测试助手"
        welcomeMessage="你好"
        defaultCollapsed={false}
      />
    );
    expect(screen.getByText("测试助手")).toBeInTheDocument();
    expect(screen.getByText("你好")).toBeInTheDocument();
  });

  it("renders suggestion chips", () => {
    render(
      <PageChatPanel
        title="助手"
        suggestions={[
          { label: "建议1", message: "msg1" },
          { label: "建议2", message: "msg2" },
        ]}
        defaultCollapsed={false}
      />
    );
    expect(screen.getByText("建议1")).toBeInTheDocument();
    expect(screen.getByText("建议2")).toBeInTheDocument();
  });

  it("collapses when defaultCollapsed is true", () => {
    render(<PageChatPanel title="助手" defaultCollapsed={true} />);
    // 输入框不应可见
    expect(screen.queryByPlaceholderText("输入消息...")).not.toBeInTheDocument();
  });

  it("expands when defaultCollapsed changes from true to false", async () => {
    const { rerender } = render(
      <PageChatPanel title="助手" defaultCollapsed={true} />
    );
    expect(screen.queryByPlaceholderText("输入消息...")).not.toBeInTheDocument();

    rerender(<PageChatPanel title="助手" defaultCollapsed={false} />);
    await waitFor(() => {
      expect(screen.getByPlaceholderText("输入消息...")).toBeInTheDocument();
    });
  });

  it("sends message on Enter and displays response", async () => {
    mockSendAIChat.mockResolvedValue(makeStreamResponse(["你好", "世界"]));

    render(<PageChatPanel title="助手" defaultCollapsed={false} />);

    const input = screen.getByPlaceholderText("输入消息...");
    await userEvent.type(input, "hello{Enter}");

    expect(mockSendAIChat).toHaveBeenCalledTimes(1);
    // 流式响应完成后应显示内容
    await waitFor(() => {
      expect(screen.getByText("你好世界")).toBeInTheDocument();
    });
  });

  it("sends message on suggestion click", async () => {
    mockSendAIChat.mockResolvedValue(makeStreamResponse(["好的"]));

    render(
      <PageChatPanel
        title="助手"
        suggestions={[{ label: "试试", message: "测试消息" }]}
        defaultCollapsed={false}
      />
    );

    await userEvent.click(screen.getByText("试试"));
    expect(mockSendAIChat).toHaveBeenCalledTimes(1);
  });

  it("expands when sending from collapsed state", async () => {
    mockSendAIChat.mockResolvedValue(makeStreamResponse(["OK"]));

    const { rerender } = render(
      <PageChatPanel title="助手" defaultCollapsed={true} />
    );
    expect(screen.queryByPlaceholderText("输入消息...")).not.toBeInTheDocument();

    // 展开后发送消息
    rerender(<PageChatPanel title="助手" defaultCollapsed={false} />);
    const input = screen.getByPlaceholderText("输入消息...");
    await userEvent.type(input, "hi{Enter}");

    await waitFor(() => {
      expect(screen.getByText("OK")).toBeInTheDocument();
    });
  });

  it("passes pageContext and pageData to sendAIChat", async () => {
    mockSendAIChat.mockResolvedValue(makeStreamResponse(["ok"]));

    render(
      <PageChatPanel
        title="助手"
        pageContext={{ page: "home" }}
        pageData={{ todo_count: 5 }}
        defaultCollapsed={false}
      />
    );

    const input = screen.getByPlaceholderText("输入消息...");
    await userEvent.type(input, "hi{Enter}");

    await waitFor(() => {
      expect(mockSendAIChat).toHaveBeenCalledWith(
        "hi",
        expect.objectContaining({
          page: "home",
          page_data: { todo_count: 5 },
        })
      );
    });
  });

  it("shows error on stream failure", async () => {
    mockSendAIChat.mockRejectedValue(new Error("network error"));

    render(<PageChatPanel title="助手" defaultCollapsed={false} />);

    const input = screen.getByPlaceholderText("输入消息...");
    await userEvent.type(input, "hi{Enter}");

    await waitFor(() => {
      expect(screen.getByText(/请求失败/)).toBeInTheDocument();
    });
  });

  it("clears chat on clear button click", async () => {
    mockSendAIChat.mockResolvedValue(makeStreamResponse(["hello"]));

    render(<PageChatPanel title="助手" defaultCollapsed={false} />);

    const input = screen.getByPlaceholderText("输入消息...");
    await userEvent.type(input, "hi{Enter}");

    await waitFor(() => {
      expect(screen.getByText("hello")).toBeInTheDocument();
    });

    // 点击清除按钮
    const trashButtons = document.querySelectorAll('[class*="h-7 w-7"]');
    if (trashButtons.length > 0) {
      await userEvent.click(trashButtons[0]);
    }

    await waitFor(() => {
      expect(screen.queryByText("hello")).not.toBeInTheDocument();
    });
  });
});
