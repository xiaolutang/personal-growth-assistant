import { describe, expect, it, vi, afterEach, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { FloatingChat } from "./FloatingChat";
import { useAgentStore } from "@/stores/agentStore";

// Mock hooks
const { mockUseIsMobile } = vi.hoisted(() => ({
  mockUseIsMobile: vi.fn(() => false),
}));

vi.mock("@/hooks/useIsMobile", () => ({
  useIsMobile: () => mockUseIsMobile(),
}));

vi.mock("@/lib/analytics", () => ({
  trackEvent: vi.fn(),
}));

// Mock authFetch for sendMessage SSE
const mockAuthFetch = vi.fn();
vi.mock("@/lib/authFetch", () => ({
  authFetch: (...args: unknown[]) => mockAuthFetch(...args),
}));

vi.mock("@/config/api", () => ({
  API_BASE: "/api",
}));

// Mock react-router-dom
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useLocation: () => ({ pathname: "/tasks" }),
  };
});

// Mock userStore - 默认已登录完成 onboarding
vi.mock("@/stores/userStore", () => ({
  useUserStore: (selector: (state: { user: { onboarding_completed: boolean } | null }) => unknown) =>
    selector({ user: { onboarding_completed: true } }),
}));

// Helper: 构造 SSE 响应流
function createSSEResponse(events: Array<{ event: string; data: unknown }>): Response {
  const chunks: string[] = [];
  for (const { event, data } of events) {
    chunks.push(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
  }
  const fullText = chunks.join("");

  const stream = new ReadableStream({
    start(controller) {
      const encoder = new TextEncoder();
      controller.enqueue(encoder.encode(fullText));
      controller.close();
    },
  });

  return {
    ok: true,
    body: stream,
    status: 200,
  } as Response;
}

describe("FloatingChat", () => {
  beforeEach(() => {
    // Mock scrollIntoView for MessageList
    Element.prototype.scrollIntoView = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
    mockUseIsMobile.mockReturnValue(false);
    useAgentStore.setState({
      sessions: [],
      currentSessionId: null,
      isLoading: false,
      isStreaming: false,
      panelHeight: 300,
    });
  });

  it("默认收起状态显示悬浮按钮", () => {
    render(<FloatingChat />);

    const fab = screen.getByTestId("chat-fab");
    expect(fab).toBeInTheDocument();
    expect(fab).toHaveAttribute("aria-label", "打开聊天");
    // 不应显示面板
    expect(screen.queryByTestId("chat-panel")).not.toBeInTheDocument();
  });

  it("点击悬浮按钮展开聊天面板", async () => {
    const user = userEvent.setup();
    render(<FloatingChat />);

    await user.click(screen.getByTestId("chat-fab"));

    // 悬浮按钮消失，面板出现
    expect(screen.queryByTestId("chat-fab")).not.toBeInTheDocument();
    expect(screen.getByTestId("chat-panel")).toBeInTheDocument();
  });

  it("点击关闭按钮收起面板", async () => {
    const user = userEvent.setup();
    render(<FloatingChat />);

    // 先展开
    await user.click(screen.getByTestId("chat-fab"));
    expect(screen.getByTestId("chat-panel")).toBeInTheDocument();

    // 点击关闭
    await user.click(screen.getByTestId("chat-close-btn"));

    // 面板消失，悬浮按钮出现
    await waitFor(() => {
      expect(screen.queryByTestId("chat-panel")).not.toBeInTheDocument();
    });
    expect(screen.getByTestId("chat-fab")).toBeInTheDocument();
  });

  it("展开面板包含消息输入框", async () => {
    const user = userEvent.setup();
    render(<FloatingChat />);

    await user.click(screen.getByTestId("chat-fab"));

    // 应该有输入框
    expect(screen.getByPlaceholderText("输入消息...")).toBeInTheDocument();
  });

  it("展开面板包含拖拽条", async () => {
    const user = userEvent.setup();
    render(<FloatingChat />);

    await user.click(screen.getByTestId("chat-fab"));

    // 拖拽条区域（包含 GripHorizontal 图标）
    const panel = screen.getByTestId("chat-panel");
    const dragBar = panel.querySelector(".cursor-ns-resize");
    expect(dragBar).toBeInTheDocument();
  });

  it("有对话时悬浮按钮显示脉冲动画", () => {
    // 设置有消息的会话
    const sessionId = useAgentStore.getState().createSession();
    useAgentStore.setState((state) => ({
      currentSessionId: sessionId,
      sessions: state.sessions.map((s) =>
        s.id === sessionId
          ? {
              ...s,
              messages: [
                {
                  id: "msg-1",
                  type: "text",
                  role: "user",
                  content: "hello",
                  timestamp: Date.now(),
                },
              ],
            }
          : s
      ),
    }));

    render(<FloatingChat />);

    const fab = screen.getByTestId("chat-fab");
    expect(fab.className).toContain("animate-pulse");
  });

  it("无对话时悬浮按钮没有脉冲动画", () => {
    render(<FloatingChat />);

    const fab = screen.getByTestId("chat-fab");
    expect(fab.className).not.toContain("animate-pulse");
  });

  it("loading 时悬浮按钮显示脉冲动画", () => {
    useAgentStore.setState({ isLoading: true });

    render(<FloatingChat />);

    const fab = screen.getByTestId("chat-fab");
    expect(fab.className).toContain("animate-pulse");
  });

  it("桌面端面板宽度固定 400px", async () => {
    const user = userEvent.setup();
    mockUseIsMobile.mockReturnValue(false);
    render(<FloatingChat />);

    await user.click(screen.getByTestId("chat-fab"));

    const panel = screen.getByTestId("chat-panel");
    expect(panel).toHaveStyle({ width: "400px" });
  });

  it("移动端面板宽度自适应", async () => {
    const user = userEvent.setup();
    mockUseIsMobile.mockReturnValue(true);
    render(<FloatingChat />);

    await user.click(screen.getByTestId("chat-fab"));

    const panel = screen.getByTestId("chat-panel");
    // 移动端不应设置固定宽度
    expect(panel.style.width).toBe("");
    // 移动端应添加 left-2 right-2 类
    expect(panel.className).toContain("left-2");
    expect(panel.className).toContain("right-2");
  });

  it("发送消息后面板内显示消息", async () => {
    mockAuthFetch.mockResolvedValue(
      createSSEResponse([
        { event: "content", data: { text: "你好" } },
        { event: "done", data: {} },
      ])
    );

    render(<FloatingChat />);

    // 展开面板
    const fab = screen.getByTestId("chat-fab");
    await act(async () => {
      fab.click();
    });

    // 输入消息并发送
    const input = screen.getByPlaceholderText("输入消息...");
    await act(async () => {
      // 模拟用户输入
      const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype,
        "value"
      )?.set;
      nativeInputValueSetter?.call(input, "测试消息");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });

    const sendBtn = screen.getByRole("button", { name: "发送" });
    await act(async () => {
      sendBtn.click();
    });

    // 等待用户消息出现
    await waitFor(() => {
      expect(screen.getByText("测试消息")).toBeInTheDocument();
    });
  });
});
