/**
 * chatStore.ts 单元测试
 *
 * 注意：部分方法（deleteSession, updateSessionTitle）现在是异步的，
 * 会调用后端 API。这些测试需要 mock API 或跳过。
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { act } from "@testing-library/react";
import { useChatStore } from "./chatStore";

// Mock sessionApi
vi.mock("@/services/sessionApi", () => ({
  sessionApi: {
    list: vi.fn().mockResolvedValue([]),
    getMessages: vi.fn().mockResolvedValue([]),
    updateTitle: vi.fn().mockResolvedValue({}),
    delete: vi.fn().mockResolvedValue(undefined),
  },
}));

describe("chatStore", () => {
  // 每次测试前重置 store
  beforeEach(async () => {
    // 使用 act 确保状态更新
    await act(async () => {
      useChatStore.setState({
        sessions: [],
        currentSessionId: null,
        panelHeight: 300,
        lastOperation: null,
        isLoading: false,
      });
    });
  });

  describe("createSession", () => {
    it("应该创建新会话并返回 ID", () => {
      const sessionId = useChatStore.getState().createSession();

      expect(sessionId).toBeDefined();
      expect(sessionId.startsWith("session-")).toBe(true);

      const session = useChatStore.getState().sessions.find((s) => s.id === sessionId);
      expect(session).toBeDefined();
      expect(session?.title).toBe("新对话");
      expect(session?.messages).toEqual([]);
    });

    it("应该将新会话设为当前会话", () => {
      const sessionId = useChatStore.getState().createSession();

      expect(useChatStore.getState().currentSessionId).toBe(sessionId);
    });

    it("应该将新会话添加到列表开头", () => {
      const id1 = useChatStore.getState().createSession();
      const id2 = useChatStore.getState().createSession();

      const sessions = useChatStore.getState().sessions;
      expect(sessions[0].id).toBe(id2);
      expect(sessions[1].id).toBe(id1);
    });
  });

  describe("switchSession", () => {
    it("应该切换到指定会话", () => {
      const id1 = useChatStore.getState().createSession();
      useChatStore.getState().createSession(); // 创建第二个会话

      useChatStore.getState().switchSession(id1);

      expect(useChatStore.getState().currentSessionId).toBe(id1);
    });
  });

  describe("addMessage", () => {
    it("应该向指定会话添加消息", () => {
      const sessionId = useChatStore.getState().createSession();

      useChatStore.getState().addMessage(sessionId, {
        role: "user",
        content: "Hello",
      });

      const session = useChatStore.getState().sessions.find((s) => s.id === sessionId);
      expect(session?.messages.length).toBe(1);
      expect(session?.messages[0].content).toBe("Hello");
      expect(session?.messages[0].role).toBe("user");
    });

    it("应该自动生成消息 ID 和时间戳", () => {
      const sessionId = useChatStore.getState().createSession();

      useChatStore.getState().addMessage(sessionId, {
        role: "user",
        content: "Test",
      });

      const session = useChatStore.getState().sessions.find((s) => s.id === sessionId);
      expect(session?.messages[0].id).toBeDefined();
      expect(session?.messages[0].timestamp).toBeDefined();
    });

    it("不应该影响其他会话的消息", async () => {
      const id1 = useChatStore.getState().createSession();
      // 稍微延迟以确保 ID 不同
      await new Promise((r) => setTimeout(r, 10));
      const id2 = useChatStore.getState().createSession();

      // 确认两个会话 ID 不同
      expect(id1).not.toBe(id2);

      // 确认两个会话都存在且消息为空
      const sessionsBefore = useChatStore.getState().sessions;
      expect(sessionsBefore.length).toBe(2);

      useChatStore.getState().addMessage(id1, {
        role: "user",
        content: "To session 1",
      });

      // 验证 id1 会话有消息
      const session1 = useChatStore.getState().sessions.find((s) => s.id === id1);
      expect(session1?.messages.length).toBe(1);

      // 验证 id2 会话没有消息
      const session2 = useChatStore.getState().sessions.find((s) => s.id === id2);
      expect(session2?.messages.length).toBe(0);
    });
  });

  describe("getCurrentSession", () => {
    it("应该返回当前会话", () => {
      const sessionId = useChatStore.getState().createSession();

      const session = useChatStore.getState().getCurrentSession();
      expect(session?.id).toBe(sessionId);
    });

    it("没有当前会话时应该返回 null", () => {
      const session = useChatStore.getState().getCurrentSession();
      expect(session).toBeNull();
    });
  });

  describe("clearMessages", () => {
    it("应该清空指定会话的消息", () => {
      const sessionId = useChatStore.getState().createSession();
      useChatStore.getState().addMessage(sessionId, { role: "user", content: "Test" });

      useChatStore.getState().clearMessages(sessionId);

      const session = useChatStore.getState().sessions.find((s) => s.id === sessionId);
      expect(session?.messages.length).toBe(0);
    });
  });

  describe("panelHeight", () => {
    it("应该更新面板高度", () => {
      useChatStore.getState().setPanelHeight(400);
      expect(useChatStore.getState().panelHeight).toBe(400);
    });
  });

  describe("lastOperation", () => {
    it("应该设置最后操作状态", () => {
      const op = {
        type: "create" as const,
        status: "success" as const,
        message: "已创建",
        timestamp: Date.now(),
      };

      useChatStore.getState().setLastOperation(op);

      expect(useChatStore.getState().lastOperation).toEqual(op);
    });

    it("应该清除最后操作状态", () => {
      useChatStore.getState().setLastOperation({
        type: "create",
        status: "success",
        message: "已创建",
        timestamp: Date.now(),
      });

      useChatStore.getState().clearLastOperation();

      expect(useChatStore.getState().lastOperation).toBeNull();
    });
  });

  describe("pageContext", () => {
    it("应该设置页面上下文", () => {
      const ctx = { page_type: "entry", entry_id: "inbox-abc123" };
      useChatStore.getState().setPageContext(ctx);
      expect(useChatStore.getState().pageContext).toEqual(ctx);
    });

    it("应该清除页面上下文", () => {
      useChatStore.getState().setPageContext({ page_type: "home" });
      useChatStore.getState().setPageContext(null);
      expect(useChatStore.getState().pageContext).toBeNull();
    });
  });

  describe("pageExtra", () => {
    it("应该设置页面额外状态", () => {
      const extra = { current_tab: "note", search_query: "test" };
      useChatStore.getState().setPageExtra(extra);
      expect(useChatStore.getState().pageExtra).toEqual(extra);
    });

    it("应该清除页面额外状态", () => {
      useChatStore.getState().setPageExtra({ current_tab: "all" });
      useChatStore.getState().setPageExtra(null);
      expect(useChatStore.getState().pageExtra).toBeNull();
    });

    it("切换 pageContext 时 pageExtra 不自动清空（由 FloatingChat 负责清理）", () => {
      useChatStore.getState().setPageExtra({ current_tab: "note" });
      useChatStore.getState().setPageContext({ page_type: "home" });
      // pageExtra 保持不变，FloatingChat 路由变化时负责清空
      expect(useChatStore.getState().pageExtra).toEqual({ current_tab: "note" });
    });
  });
});
