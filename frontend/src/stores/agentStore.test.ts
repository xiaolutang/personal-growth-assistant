/**
 * agentStore.ts 单元测试
 *
 * 测试覆盖：
 * - 会话创建/切换
 * - 消息管理
 * - SSE 事件解析（8 种事件类型）
 * - isLoading 状态管理
 * - currentToolCalls 跟踪
 * - 错误处理
 * - 追问回调
 */

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { act } from "@testing-library/react";
import { useAgentStore } from "./agentStore";

// Mock authFetch
const mockAuthFetch = vi.fn();
vi.mock("@/lib/authFetch", () => ({
  authFetch: (...args: unknown[]) => mockAuthFetch(...args),
}));

// Mock API_BASE
vi.mock("@/config/api", () => ({
  API_BASE: "/api",
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

// Helper: 构造错误响应
function createErrorResponse(status: number, message: string): Response {
  return {
    ok: false,
    status,
    text: async () => JSON.stringify({ detail: message }),
  } as Response;
}

describe("agentStore", () => {
  beforeEach(async () => {
    await act(async () => {
      useAgentStore.setState({
        sessions: [],
        currentSessionId: null,
        isLoading: false,
        isStreaming: false,
        thinkingContent: "",
        currentToolCalls: new Map(),
        error: null,
        pageContext: null,
      });
    });
    vi.clearAllMocks();
    useAgentStore.getState().setFollowUpCallback(null);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ── 会话管理 ──

  describe("createSession", () => {
    it("应该创建新会话并返回 ID", () => {
      const sessionId = useAgentStore.getState().createSession();

      expect(sessionId).toBeDefined();
      expect(sessionId.startsWith("agent-session-")).toBe(true);

      const session = useAgentStore.getState().sessions.find((s) => s.id === sessionId);
      expect(session).toBeDefined();
      expect(session?.title).toBe("新对话");
      expect(session?.messages).toEqual([]);
    });

    it("应该将新会话设为当前会话", () => {
      const sessionId = useAgentStore.getState().createSession();
      expect(useAgentStore.getState().currentSessionId).toBe(sessionId);
    });

    it("应该将新会话添加到列表开头", () => {
      const id1 = useAgentStore.getState().createSession();
      const id2 = useAgentStore.getState().createSession();

      const sessions = useAgentStore.getState().sessions;
      expect(sessions[0].id).toBe(id2);
      expect(sessions[1].id).toBe(id1);
    });
  });

  describe("switchSession", () => {
    it("应该切换到指定会话", () => {
      const id1 = useAgentStore.getState().createSession();
      useAgentStore.getState().createSession();

      useAgentStore.getState().switchSession(id1);
      expect(useAgentStore.getState().currentSessionId).toBe(id1);
    });
  });

  describe("getCurrentSession", () => {
    it("应该返回当前会话", () => {
      const sessionId = useAgentStore.getState().createSession();
      const session = useAgentStore.getState().getCurrentSession();
      expect(session?.id).toBe(sessionId);
    });

    it("没有当前会话时应该返回 null", () => {
      expect(useAgentStore.getState().getCurrentSession()).toBeNull();
    });
  });

  describe("resetCurrentSession", () => {
    it("应该清空当前会话的消息和状态", async () => {
      const sessionId = useAgentStore.getState().createSession();
      useAgentStore.getState().switchSession(sessionId);

      // 手动添加一条消息
      await act(async () => {
        useAgentStore.setState((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId
              ? {
                  ...s,
                  messages: [
                    {
                      id: "test-msg",
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
      });

      useAgentStore.getState().resetCurrentSession();

      const session = useAgentStore.getState().getCurrentSession();
      expect(session?.messages).toEqual([]);
    });
  });

  // ── SSE 事件解析 ──

  describe("sendMessage - SSE 解析", () => {
    it("应该正确解析 thinking 事件", async () => {
      mockAuthFetch.mockResolvedValue(
        createSSEResponse([
          { event: "thinking", data: { content: "让我想想..." } },
          { event: "done", data: {} },
        ])
      );

      await act(async () => {
        await useAgentStore.getState().sendMessage({ text: "测试" });
      });

      // thinking 时 isLoading 为 true，done 后为 false
      expect(useAgentStore.getState().isLoading).toBe(false);
    });

    it("应该正确解析 content 事件并生成 assistant 消息", async () => {
      mockAuthFetch.mockResolvedValue(
        createSSEResponse([
          { event: "content", data: { text: "你好" } },
          { event: "content", data: { text: "世界" } },
          { event: "done", data: {} },
        ])
      );

      const sessionId = useAgentStore.getState().createSession();

      await act(async () => {
        await useAgentStore.getState().sendMessage({ text: "测试", sessionId });
      });

      const session = useAgentStore.getState().getCurrentSession();
      expect(session).not.toBeNull();

      // 应该有 1 条用户消息 + 1 条 assistant 消息
      const assistantMessages = session!.messages.filter(
        (m) => m.role === "assistant" && m.type === "text"
      );
      expect(assistantMessages.length).toBe(1);
      expect(assistantMessages[0].content).toBe("你好世界");
    });

    it("应该正确解析 tool_call 事件并创建卡片消息", async () => {
      mockAuthFetch.mockResolvedValue(
        createSSEResponse([
          {
            event: "tool_call",
            data: {
              id: "tc-123",
              tool: "create_entry",
              args: { title: "测试任务" },
            },
          },
          {
            event: "tool_result",
            data: {
              tool_call_id: "tc-123",
              result: { id: "entry-1", title: "测试任务", category: "task" },
              success: true,
            },
          },
          { event: "done", data: {} },
        ])
      );

      const sessionId = useAgentStore.getState().createSession();

      await act(async () => {
        await useAgentStore.getState().sendMessage({ text: "创建一个测试任务", sessionId });
      });

      const session = useAgentStore.getState().getCurrentSession();
      const toolCallMessages = session!.messages.filter((m) => m.type === "tool_call");
      expect(toolCallMessages.length).toBe(1);

      const toolMsg = toolCallMessages[0];
      expect(toolMsg.toolCall).toBeDefined();
      expect(toolMsg.toolCall!.tool).toBe("create_entry");
      expect(toolMsg.toolCall!.status).toBe("success");
      expect(toolMsg.toolCall!.args).toEqual({ title: "测试任务" });
    });

    it("应该正确解析 tool_result 更新工具状态", async () => {
      mockAuthFetch.mockResolvedValue(
        createSSEResponse([
          {
            event: "tool_call",
            data: { id: "tc-err", tool: "delete_entry", args: { id: "nonexistent" } },
          },
          {
            event: "tool_result",
            data: {
              tool_call_id: "tc-err",
              result: { error: "条目不存在" },
              success: false,
            },
          },
          { event: "done", data: {} },
        ])
      );

      const sessionId = useAgentStore.getState().createSession();

      await act(async () => {
        await useAgentStore.getState().sendMessage({ text: "删除", sessionId });
      });

      const session = useAgentStore.getState().getCurrentSession();
      const toolMsg = session!.messages.find((m) => m.type === "tool_call");
      expect(toolMsg?.toolCall?.status).toBe("error");
    });

    it("应该正确解析 created 事件并关联到消息", async () => {
      mockAuthFetch.mockResolvedValue(
        createSSEResponse([
          { event: "content", data: { text: "已创建" } },
          {
            event: "created",
            data: { id: "entry-new", type: "task", title: "新任务" },
          },
          { event: "done", data: {} },
        ])
      );

      const sessionId = useAgentStore.getState().createSession();

      await act(async () => {
        await useAgentStore.getState().sendMessage({ text: "新建任务", sessionId });
      });

      const session = useAgentStore.getState().getCurrentSession();
      const assistantMsg = session!.messages.find(
        (m) => m.role === "assistant" && m.type === "text"
      );
      expect(assistantMsg?.entryChange).toBeDefined();
      expect(assistantMsg?.entryChange?.id).toBe("entry-new");
      expect(assistantMsg?.entryChange?.title).toBe("新任务");
    });

    it("应该正确解析 updated 事件", async () => {
      mockAuthFetch.mockResolvedValue(
        createSSEResponse([
          { event: "content", data: { text: "已更新" } },
          {
            event: "updated",
            data: { id: "entry-exist", changes: "状态已改为完成" },
          },
          { event: "done", data: {} },
        ])
      );

      const sessionId = useAgentStore.getState().createSession();

      await act(async () => {
        await useAgentStore.getState().sendMessage({ text: "更新状态", sessionId });
      });

      const session = useAgentStore.getState().getCurrentSession();
      const assistantMsg = session!.messages.find(
        (m) => m.role === "assistant" && m.type === "text"
      );
      expect(assistantMsg?.entryChange).toBeDefined();
      expect(assistantMsg?.entryChange?.id).toBe("entry-exist");
      expect(assistantMsg?.entryChange?.changes).toBe("状态已改为完成");
    });

    it("应该正确解析 error 事件", async () => {
      mockAuthFetch.mockResolvedValue(
        createSSEResponse([
          { event: "error", data: { message: "参数错误" } },
          { event: "done", data: {} },
        ])
      );

      const sessionId = useAgentStore.getState().createSession();

      await act(async () => {
        await useAgentStore.getState().sendMessage({ text: "测试", sessionId });
      });

      expect(useAgentStore.getState().error).toBe("参数错误");
      expect(useAgentStore.getState().isLoading).toBe(false);
    });

    it("应该在 done 事件后重置 loading 状态", async () => {
      mockAuthFetch.mockResolvedValue(
        createSSEResponse([
          { event: "thinking", data: { content: "思考中..." } },
          { event: "content", data: { text: "完成" } },
          { event: "done", data: {} },
        ])
      );

      const sessionId = useAgentStore.getState().createSession();

      await act(async () => {
        await useAgentStore.getState().sendMessage({ text: "测试", sessionId });
      });

      expect(useAgentStore.getState().isLoading).toBe(false);
      expect(useAgentStore.getState().isStreaming).toBe(false);
      expect(useAgentStore.getState().thinkingContent).toBe("");
    });

    it("应该处理 HTTP 错误响应", async () => {
      mockAuthFetch.mockResolvedValue(
        createErrorResponse(500, "服务器内部错误")
      );

      const sessionId = useAgentStore.getState().createSession();

      await act(async () => {
        await useAgentStore.getState().sendMessage({ text: "测试", sessionId });
      });

      expect(useAgentStore.getState().error).toContain("服务器内部错误");
      expect(useAgentStore.getState().isLoading).toBe(false);
    });
  });

  // ── isLoading 状态管理 ──

  describe("isLoading 状态", () => {
    it("thinking 时 isLoading 为 true，done 后为 false", async () => {
      // 使用含 thinking + done 的完整 SSE 流
      mockAuthFetch.mockResolvedValue(
        createSSEResponse([
          { event: "thinking", data: { content: "思考中..." } },
          { event: "content", data: { text: "完成" } },
          { event: "done", data: {} },
        ])
      );

      const sessionId = useAgentStore.getState().createSession();

      await act(async () => {
        await useAgentStore.getState().sendMessage({ text: "测试", sessionId });
      });

      // done 后 isLoading 应该为 false
      expect(useAgentStore.getState().isLoading).toBe(false);
    });
  });

  // ── currentToolCalls 跟踪 ──

  describe("currentToolCalls", () => {
    it("应该跟踪进行中的工具调用", async () => {
      mockAuthFetch.mockResolvedValue(
        createSSEResponse([
          {
            event: "tool_call",
            data: { id: "tc-1", tool: "search_entries", args: { query: "测试" } },
          },
          {
            event: "tool_result",
            data: {
              tool_call_id: "tc-1",
              result: { results: [] },
              success: true,
            },
          },
          {
            event: "tool_call",
            data: { id: "tc-2", tool: "create_entry", args: { title: "新条目" } },
          },
          {
            event: "tool_result",
            data: {
              tool_call_id: "tc-2",
              result: { id: "e1", title: "新条目", category: "task" },
              success: true,
            },
          },
          { event: "done", data: {} },
        ])
      );

      const sessionId = useAgentStore.getState().createSession();

      await act(async () => {
        await useAgentStore.getState().sendMessage({ text: "搜索并创建", sessionId });
      });

      const session = useAgentStore.getState().getCurrentSession();
      const toolMessages = session!.messages.filter((m) => m.type === "tool_call");
      expect(toolMessages.length).toBe(2);

      // 验证两个工具调用的最终状态
      expect(toolMessages[0].toolCall!.tool).toBe("search_entries");
      expect(toolMessages[0].toolCall!.status).toBe("success");
      expect(toolMessages[1].toolCall!.tool).toBe("create_entry");
      expect(toolMessages[1].toolCall!.status).toBe("success");
    });
  });

  // ── 混合内容消息 ──

  describe("混合内容消息", () => {
    it("应该支持文本和工具调用的混合消息", async () => {
      mockAuthFetch.mockResolvedValue(
        createSSEResponse([
          { event: "thinking", data: { content: "我来帮你查找" } },
          {
            event: "tool_call",
            data: { id: "tc-search", tool: "search_entries", args: { query: "MCP" } },
          },
          {
            event: "tool_result",
            data: {
              tool_call_id: "tc-search",
              result: { results: [{ id: "1", title: "MCP 笔记" }] },
              success: true,
            },
          },
          { event: "content", data: { text: "找到了你的 MCP 笔记" } },
          { event: "done", data: {} },
        ])
      );

      const sessionId = useAgentStore.getState().createSession();

      await act(async () => {
        await useAgentStore.getState().sendMessage({ text: "找 MCP 笔记", sessionId });
      });

      const session = useAgentStore.getState().getCurrentSession();
      // 1 user + 1 tool_call + 1 assistant text
      expect(session!.messages.length).toBe(3);

      const userMsg = session!.messages.find((m) => m.role === "user");
      expect(userMsg?.content).toBe("找 MCP 笔记");

      const toolMsg = session!.messages.find((m) => m.type === "tool_call");
      expect(toolMsg?.toolCall?.tool).toBe("search_entries");

      const textMsg = session!.messages.find(
        (m) => m.role === "assistant" && m.type === "text"
      );
      expect(textMsg?.content).toBe("找到了你的 MCP 笔记");
    });
  });

  // ── 状态操作 ──

  describe("setPageContext", () => {
    it("应该设置页面上下文", () => {
      const ctx = { page_type: "entry", entry_id: "entry-abc" };
      useAgentStore.getState().setPageContext(ctx);
      expect(useAgentStore.getState().pageContext).toEqual(ctx);
    });

    it("应该清除页面上下文", () => {
      useAgentStore.getState().setPageContext({ page_type: "home" });
      useAgentStore.getState().setPageContext(null);
      expect(useAgentStore.getState().pageContext).toBeNull();
    });
  });

  describe("clearError", () => {
    it("应该清除错误状态", () => {
      useAgentStore.setState({ error: "测试错误" });
      useAgentStore.getState().clearError();
      expect(useAgentStore.getState().error).toBeNull();
    });
  });

  // ── cancelStream ──

  describe("cancelStream", () => {
    it("应该取消流式请求并重置状态", () => {
      useAgentStore.setState({ isLoading: true, isStreaming: true });
      useAgentStore.getState().cancelStream();
      expect(useAgentStore.getState().isLoading).toBe(false);
      expect(useAgentStore.getState().isStreaming).toBe(false);
    });
  });

  // ── 追问回调 ──

  describe("追问回调", () => {
    it("done 后如果没有 assistant 文本消息，应该触发追问回调", async () => {
      const followUpSpy = vi.fn();
      useAgentStore.getState().setFollowUpCallback(followUpSpy);

      // 只有 tool_call，没有 assistant text
      mockAuthFetch.mockResolvedValue(
        createSSEResponse([
          {
            event: "tool_call",
            data: { id: "tc-1", tool: "create_entry", args: { title: "测试" } },
          },
          {
            event: "tool_result",
            data: {
              tool_call_id: "tc-1",
              result: { success: true },
              success: true,
            },
          },
          { event: "done", data: {} },
        ])
      );

      const sessionId = useAgentStore.getState().createSession();

      await act(async () => {
        await useAgentStore.getState().sendMessage({ text: "创建", sessionId });
      });

      // 等待 setTimeout(100ms) 执行
      await act(async () => {
        await new Promise((r) => setTimeout(r, 200));
      });

      expect(followUpSpy).toHaveBeenCalled();
    });

    it("done 后如果有 assistant 文本消息，不应该触发追问回调", async () => {
      const followUpSpy = vi.fn();
      useAgentStore.getState().setFollowUpCallback(followUpSpy);

      mockAuthFetch.mockResolvedValue(
        createSSEResponse([
          { event: "content", data: { text: "已完成" } },
          { event: "done", data: {} },
        ])
      );

      const sessionId = useAgentStore.getState().createSession();

      await act(async () => {
        await useAgentStore.getState().sendMessage({ text: "测试", sessionId });
      });

      await act(async () => {
        await new Promise((r) => setTimeout(r, 200));
      });

      expect(followUpSpy).not.toHaveBeenCalled();
    });
  });

  // ── 自动创建会话 ──

  describe("自动创建会话", () => {
    it("没有 sessionId 时应自动创建会话", async () => {
      mockAuthFetch.mockResolvedValue(
        createSSEResponse([
          { event: "done", data: {} },
        ])
      );

      // 没有预设 session
      expect(useAgentStore.getState().currentSessionId).toBeNull();

      await act(async () => {
        await useAgentStore.getState().sendMessage({ text: "测试" });
      });

      // 应该自动创建了会话
      expect(useAgentStore.getState().currentSessionId).not.toBeNull();
      expect(useAgentStore.getState().sessions.length).toBe(1);
    });
  });
});
