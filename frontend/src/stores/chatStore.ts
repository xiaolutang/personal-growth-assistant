import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Intent } from "@/lib/intentDetection";

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

  // Actions
  createSession: () => string;
  deleteSession: (id: string) => void;
  switchSession: (id: string) => void;
  addMessage: (
    sessionId: string,
    message: Omit<ChatMessage, "id" | "timestamp">
  ) => void;
  getCurrentSession: () => ChatSession | null;
  updateSessionTitle: (id: string, title: string) => void;
  clearMessages: (sessionId: string) => void;
  setPanelHeight: (height: number) => void;
  setLastOperation: (op: OperationStatus | null) => void;
  clearLastOperation: () => void;
}

// 默认面板高度
const DEFAULT_PANEL_HEIGHT = 300;

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      sessions: [],
      currentSessionId: null,
      panelHeight: DEFAULT_PANEL_HEIGHT,
      lastOperation: null,

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

      deleteSession: (id) => {
        set((state) => {
          const sessions = state.sessions.filter((s) => s.id !== id);
          const currentSessionId =
            state.currentSessionId === id
              ? sessions[0]?.id || null
              : state.currentSessionId;
          return { sessions, currentSessionId };
        });
      },

      switchSession: (id) => {
        set({ currentSessionId: id });
      },

      addMessage: (sessionId, message) => {
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

      updateSessionTitle: (id, title) => {
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === id ? { ...session, title } : session
          ),
        }));
      },

      clearMessages: (sessionId) => {
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === sessionId
              ? { ...session, messages: [], updatedAt: Date.now() }
              : session
          ),
        }));
      },

      setPanelHeight: (height) => {
        set({ panelHeight: height });
      },

      setLastOperation: (op) => {
        set({ lastOperation: op });
      },

      clearLastOperation: () => {
        set({ lastOperation: null });
      },
    }),
    { name: "chat-storage", partialize: (state) => ({ sessions: state.sessions, currentSessionId: state.currentSessionId, panelHeight: state.panelHeight }) }
  )
);
