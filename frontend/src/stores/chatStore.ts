import { create } from "zustand";
import type { Intent } from "@/lib/intentDetection";
import { sessionApi, type SessionInfo, type MessageInfo } from "@/services/sessionApi";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  actionConfirm?: {
    type: "delete" | "update";
    entryId: string;
    title: string;
  };
  // 预留元数据：意图、工具调用、Skill 调用
  metadata?: {
    intent?: Intent;
    response?: string;
    toolCalls?: {
      type: "tool" | "skill";
      name: string;
      params?: Record<string, unknown>;
      status: "running" | "success" | "error";
    }[];
  };
}

export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}

// 页面级 AI 上下文
export interface PageContext {
  page_type: string;                    // home / explore / entry / review / graph
  entry_id?: string;                    // 详情页条目 ID
  extra?: Record<string, string | number>; // 扩展字段
}

// 操作状态（用于状态提示条）
export interface OperationStatus {
  type: Intent | "tool" | "skill";  // 操作类型
  name?: string;                     // 工具/Skill 名称
  status: "pending" | "success" | "error";
  message: string;                   // 显示消息
  target?: string;                   // 操作目标（标题）
  timestamp: number;
}

interface ChatStore {
  sessions: ChatSession[];
  currentSessionId: string | null;
  panelHeight: number; // FloatingChat 面板高度
  lastOperation: OperationStatus | null; // 最近操作状态
  isLoading: boolean; // 加载状态
  pageContext: PageContext | null; // 页面级 AI 上下文
  pageExtra: Record<string, string | number> | null; // 页面组件主动写入的额外状态

  // API 操作
  fetchSessions: () => Promise<void>;
  fetchSessionMessages: (sessionId: string) => Promise<void>;
  createSession: () => string;
  deleteSession: (id: string) => Promise<void>;
  switchSession: (id: string) => void;
  updateSessionTitle: (id: string, title: string) => Promise<void>;

  // 本地操作
  addMessage: (
    sessionId: string,
    message: Omit<ChatMessage, "id" | "timestamp">
  ) => void;
  getCurrentSession: () => ChatSession | null;
  clearMessages: (sessionId: string) => void;
  setPanelHeight: (height: number) => void;
  setLastOperation: (op: OperationStatus | null) => void;
  clearLastOperation: () => void;
  setPageContext: (ctx: PageContext | null) => void;
  setPageExtra: (extra: Record<string, string | number> | null) => void;
}

// 默认面板高度
const DEFAULT_PANEL_HEIGHT = 300;

// UI 偏好存储（独立于会话数据）
function loadPanelHeight(): number {
  try {
    const saved = localStorage.getItem("chat-panel-height");
    return saved ? Number(saved) : DEFAULT_PANEL_HEIGHT;
  } catch {
    return DEFAULT_PANEL_HEIGHT;
  }
}

function savePanelHeight(height: number): void {
  try {
    localStorage.setItem("chat-panel-height", String(height));
  } catch {
    // 忽略存储错误
  }
}

// 转换后端消息为前端格式
function convertMessage(msg: MessageInfo): ChatMessage {
  return {
    id: msg.id,
    role: msg.role,
    content: msg.content,
    timestamp: new Date(msg.timestamp).getTime(),
  };
}

// 转换后端会话为前端格式
function convertSession(session: SessionInfo, messages: ChatMessage[] = []): ChatSession {
  return {
    id: session.id,
    title: session.title,
    messages,
    createdAt: new Date(session.created_at).getTime(),
    updatedAt: new Date(session.updated_at).getTime(),
  };
}

export const useChatStore = create<ChatStore>()((set, get) => ({
  sessions: [],
  currentSessionId: null,
  panelHeight: loadPanelHeight(),
  lastOperation: null,
  isLoading: false,
  pageContext: null,
  pageExtra: null,

  fetchSessions: async () => {
    set({ isLoading: true });
    try {
      const sessionList = await sessionApi.list();
      const sessions = sessionList.map((s) => convertSession(s));
      set({ sessions, isLoading: false });
    } catch (error) {
      console.error("Failed to fetch sessions:", error);
      set({ isLoading: false });
    }
  },

  fetchSessionMessages: async (sessionId: string) => {
    try {
      const messages = await sessionApi.getMessages(sessionId);
      set((state) => ({
        sessions: state.sessions.map((session) =>
          session.id === sessionId
            ? { ...session, messages: messages.map(convertMessage) }
            : session
        ),
      }));
    } catch (error) {
      console.error("Failed to fetch session messages:", error);
    }
  },

  createSession: () => {
    const id = `session-${Date.now()}`;
    const newSession: ChatSession = {
      id,
      title: "新对话",
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    set((state) => ({
      sessions: [newSession, ...state.sessions],
      currentSessionId: id,
    }));
    return id;
  },

  deleteSession: async (id: string) => {
    try {
      await sessionApi.delete(id);
      set((state) => {
        const sessions = state.sessions.filter((s) => s.id !== id);
        const currentSessionId =
          state.currentSessionId === id
            ? sessions[0]?.id || null
            : state.currentSessionId;
        return { sessions, currentSessionId };
      });
    } catch (error) {
      console.error("Failed to delete session:", error);
    }
  },

  switchSession: (id: string) => {
    set({ currentSessionId: id });
  },

  updateSessionTitle: async (id: string, title: string) => {
    try {
      await sessionApi.updateTitle(id, title);
      set((state) => ({
        sessions: state.sessions.map((session) =>
          session.id === id ? { ...session, title } : session
        ),
      }));
    } catch (error) {
      console.error("Failed to update session title:", error);
    }
  },

  addMessage: (sessionId: string, message) => {
    set((state) => ({
      sessions: state.sessions.map((session) =>
        session.id === sessionId
          ? {
              ...session,
              messages: [
                ...session.messages,
                {
                  ...message,
                  id: `msg-${Date.now()}`,
                  timestamp: Date.now(),
                },
              ],
              updatedAt: Date.now(),
            }
          : session
      ),
    }));
  },

  getCurrentSession: () => {
    const state = get();
    return (
      state.sessions.find((s) => s.id === state.currentSessionId) || null
    );
  },

  clearMessages: (sessionId: string) => {
    set((state) => ({
      sessions: state.sessions.map((session) =>
        session.id === sessionId
          ? { ...session, messages: [], updatedAt: Date.now() }
          : session
      ),
    }));
  },

  setPanelHeight: (height: number) => {
    set({ panelHeight: height });
    savePanelHeight(height);
  },

  setLastOperation: (op: OperationStatus | null) => {
    set({ lastOperation: op });
  },

  clearLastOperation: () => {
    set({ lastOperation: null });
  },

  setPageContext: (ctx: PageContext | null) => {
    set({ pageContext: ctx });
  },

  setPageExtra: (extra: Record<string, string | number> | null) => {
    set({ pageExtra: extra });
  },
}));
