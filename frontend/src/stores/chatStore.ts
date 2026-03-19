import { create } from "zustand";
import { persist } from "zustand/middleware";

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
}

export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}

interface ChatStore {
  sessions: ChatSession[];
  currentSessionId: string | null;
  panelHeight: number; // FloatingChat 面板高度

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
}

// 默认面板高度
const DEFAULT_PANEL_HEIGHT = 300;

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      sessions: [],
      currentSessionId: null,
      panelHeight: DEFAULT_PANEL_HEIGHT,

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
    }),
    { name: "chat-storage" }
  )
);
