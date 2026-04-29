/**
 * agentStore.ts — Agent 对话状态管理
 *
 * 统一管理 ReAct Agent 对话流程，支持 8 种 SSE 事件类型解析：
 * thinking / tool_call / tool_result / content / created / updated / error / done
 *
 * 设计要点：
 * - 使用 Zustand create() 模式，与现有 chatStore 一致
 * - SSE 通过 fetch + ReadableStream 解析（支持自定义 headers）
 * - Message 类型支持混合内容（文本 + 工具调用卡片）
 * - isLoading 在 thinking 时为 true，done 时为 false
 * - currentToolCalls 跟踪进行中的工具调用
 * - 与 chatStore 共存，不修改现有代码
 */

import { create } from "zustand";
import { API_BASE } from "@/config/api";
import { authFetch } from "@/lib/authFetch";
import { sessionApi, type MessageInfo } from "@/services/sessionApi";

// ═══════════════════════════════════════════
// 类型定义
// ═══════════════════════════════════════════

/** SSE 事件类型（8 种） */
export type SSEEventType =
  | "thinking"
  | "tool_call"
  | "tool_result"
  | "content"
  | "created"
  | "updated"
  | "error"
  | "done";

/** 工具调用状态 */
export type ToolCallStatus = "running" | "success" | "error";

/** 工具调用卡片 */
export interface ToolCallInfo {
  id: string;
  tool: string;
  args: Record<string, unknown>;
  status: ToolCallStatus;
  result?: unknown;
}

/** 条目变更信息（created/updated 事件） */
export interface EntryChange {
  id: string;
  type?: string;     // category (created)
  title?: string;    // (created)
  changes?: string;  // (updated)
}

/** Agent 消息类型 */
export type AgentMessageType = "text" | "tool_call" | "thinking";

/** Agent 消息 */
export interface AgentMessage {
  id: string;
  type: AgentMessageType;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  /** 工具调用卡片信息（type=tool_call 时存在） */
  toolCall?: ToolCallInfo;
  /** 条目变更信息（created/updated 事件关联） */
  entryChange?: EntryChange;
  /** 是否为追问（Agent done 后等待用户输入） */
  isFollowUp?: boolean;
}

/** Agent 会话 */
export interface AgentSession {
  id: string;
  title: string;
  messages: AgentMessage[];
  createdAt: number;
  updatedAt: number;
}

/** 页面级上下文 */
export interface AgentPageContext {
  page_type: string;
  entry_id?: string;
  extra?: Record<string, string | number>;
}

/** SSE 事件数据映射 */
export interface SSEEventData {
  thinking: { content: string };
  tool_call: { id: string; tool: string; args: Record<string, unknown> };
  tool_result: { tool_call_id: string; result: unknown; success: boolean };
  content: { text: string };
  created: { id: string; type: string; title: string };
  updated: { id: string; changes: string };
  error: { message: string };
  done: Record<string, never>;
}

/** 对话发送参数 */
export interface SendMessageParams {
  text: string;
  sessionId?: string;
  pageContext?: AgentPageContext | null;
}

/** Agent 追问回调（done 后输入框聚焦） */
export type FollowUpCallback = (() => void) | null;

// ═══════════════════════════════════════════
// Store 接口
// ═══════════════════════════════════════════

interface AgentStore {
  // ── 状态 ──
  sessions: AgentSession[];
  currentSessionId: string | null;
  isLoading: boolean;
  isStreaming: boolean;
  thinkingContent: string;
  currentToolCalls: Map<string, ToolCallInfo>;
  error: string | null;
  pageContext: AgentPageContext | null;
  pageExtra: Record<string, string | number> | null;
  panelHeight: number;

  // ── 会话管理 ──
  createSession: () => string;
  switchSession: (id: string) => void;
  getCurrentSession: () => AgentSession | null;
  resetCurrentSession: () => void;
  deleteSession: (id: string) => Promise<void>;
  updateSessionTitle: (id: string, title: string) => Promise<void>;
  fetchSessions: () => Promise<void>;
  loadSessionMessages: (sessionId: string) => Promise<void>;

  // ── 对话操作 ──
  sendMessage: (params: SendMessageParams) => Promise<void>;
  cancelStream: () => void;

  // ── 状态操作 ──
  setPageContext: (ctx: AgentPageContext | null) => void;
  setPageExtra: (extra: Record<string, string | number> | null) => void;
  setPanelHeight: (height: number) => void;
  clearError: () => void;
  setFollowUpCallback: (cb: FollowUpCallback) => void;
}

// ═══════════════════════════════════════════
// 内部工具函数
// ═══════════════════════════════════════════

/** 生成唯一 ID */
function generateId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
}

/** 解析 SSE 文本流，提取 event + data */
function parseSSELine(line: string): { event: string; data: string } | null {
  // SSE 格式: "event: xxx\ndata: {...}\n\n"
  // 已经按行拆分，这里处理单行
  if (line.startsWith("event: ")) {
    return { event: line.slice(7).trim(), data: "" };
  }
  if (line.startsWith("data: ")) {
    return { event: "", data: line.slice(6) };
  }
  return null;
}

/** 从 ReadableStream 中解析 SSE 事件 */
async function* parseSSEStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  signal: AbortSignal
): AsyncGenerator<{ event: string; data: unknown }> {
  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "";
  let currentData = "";

  try {
    while (true) {
      if (signal.aborted) break;

      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // 按双换行分割 SSE 事件
      const parts = buffer.split("\n\n");
      // 最后一部分可能不完整，保留在 buffer 中
      buffer = parts.pop() || "";

      for (const part of parts) {
        const lines = part.split("\n");
        currentEvent = "";
        currentData = "";

        for (const line of lines) {
          const parsed = parseSSELine(line);
          if (parsed) {
            if (parsed.event) currentEvent = parsed.event;
            if (parsed.data) currentData = parsed.data;
          }
        }

        if (currentEvent && currentData) {
          try {
            const data = JSON.parse(currentData);
            yield { event: currentEvent, data };
          } catch {
            // JSON 解析失败，跳过
            console.warn(`[agentStore] Failed to parse SSE data for event "${currentEvent}":`, currentData);
          }
        }
      }
    }

    // 处理 buffer 中剩余的内容
    if (buffer.trim()) {
      const lines = buffer.split("\n");
      currentEvent = "";
      currentData = "";

      for (const line of lines) {
        const parsed = parseSSELine(line);
        if (parsed) {
          if (parsed.event) currentEvent = parsed.event;
          if (parsed.data) currentData = parsed.data;
        }
      }

      if (currentEvent && currentData) {
        try {
          const data = JSON.parse(currentData);
          yield { event: currentEvent, data };
        } catch {
          // 忽略解析错误
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ═══════════════════════════════════════════
// Store 实现
// ═══════════════════════════════════════════

/** 当前流式请求的 AbortController */
let _activeAbortController: AbortController | null = null;

/** 追问回调 */
let _followUpCallback: FollowUpCallback = null;

// 面板高度持久化
const DEFAULT_PANEL_HEIGHT = 300;
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

export const useAgentStore = create<AgentStore>()((set, get) => ({
  // ── 初始状态 ──
  sessions: [],
  currentSessionId: null,
  isLoading: false,
  isStreaming: false,
  thinkingContent: "",
  currentToolCalls: new Map<string, ToolCallInfo>(),
  error: null,
  pageContext: null,
  pageExtra: null,
  panelHeight: loadPanelHeight(),

  // ── 会话管理 ──

  createSession: () => {
    const id = generateId("s");
    const newSession: AgentSession = {
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

  switchSession: (id: string) => {
    set({ currentSessionId: id });
    // 如果该会话没有消息，从后端加载历史
    const session = get().sessions.find((s) => s.id === id);
    if (session && session.messages.length === 0) {
      get().loadSessionMessages(id);
    }
  },

  getCurrentSession: () => {
    const state = get();
    return state.sessions.find((s) => s.id === state.currentSessionId) || null;
  },

  resetCurrentSession: () => {
    // 先保存旧 sessionId，再创建新会话
    const oldId = get().currentSessionId;
    const newId = get().createSession();
    // 清理流状态
    set({
      thinkingContent: "",
      currentToolCalls: new Map(),
      error: null,
    });
    // 后台清理旧会话的后端状态（不阻塞 UI）
    if (oldId && oldId !== newId) {
      sessionApi.delete(oldId).catch(() => {
        // 静默失败，不阻塞 UI
      });
    }
  },

  // ── 对话操作 ──

  sendMessage: async (params: SendMessageParams) => {
    const { text, pageContext } = params;
    const sessionId = params.sessionId || get().currentSessionId;

    if (!text.trim()) return;

    // 确保有活跃会话
    let sid = sessionId;
    if (!sid) {
      sid = get().createSession();
    }

    // 清理上一次流的状态
    if (_activeAbortController) {
      _activeAbortController.abort();
    }
    _activeAbortController = new AbortController();
    const signal = _activeAbortController.signal;

    // 添加用户消息
    const userMsg: AgentMessage = {
      id: generateId("msg"),
      type: "text",
      role: "user",
      content: text,
      timestamp: Date.now(),
    };

    set((state) => ({
      sessions: state.sessions.map((s) =>
        s.id === sid
          ? { ...s, messages: [...s.messages, userMsg], updatedAt: Date.now() }
          : s
      ),
      currentSessionId: sid,
      isLoading: true,
      isStreaming: true,
      thinkingContent: "",
      currentToolCalls: new Map(),
      error: null,
    }));

    try {
      // 构建 POST /chat 请求
      const requestBody: Record<string, unknown> = {
        text,
        session_id: sid,
      };

      // 合并 pageContext 和 pageExtra
      const ctx = pageContext || get().pageContext;
      const extra = get().pageExtra;
      if (ctx || extra) {
        requestBody.page_context = {
          ...ctx,
          ...(extra ? { extra } : {}),
        };
      }

      const response = await authFetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
        signal,
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `请求失败: ${response.status}`;
        try {
          const errorJson = JSON.parse(errorText);
          errorMessage = errorJson.detail || errorJson.message || errorMessage;
        } catch {
          // 使用默认错误消息
        }
        set({ isLoading: false, isStreaming: false, error: errorMessage });
        return;
      }

      if (!response.body) {
        set({ isLoading: false, isStreaming: false, error: "响应体为空" });
        return;
      }

      // 使用 ReadableStream 解析 SSE
      const reader = response.body.getReader();
      const sseGenerator = parseSSEStream(reader, signal);

      // 跟踪当前 assistant 消息（用于增量更新 content）
      let currentAssistantMsgId: string | null = null;
      let currentAssistantContent = "";
      // 跟踪最后一个 tool_call 消息 ID（用于关联 tool_result）
      const pendingToolCallMsgIds: Map<string, string> = new Map(); // tool_call_id -> msg_id

      for await (const { event, data } of sseGenerator) {
        if (signal.aborted) break;

        switch (event as SSEEventType) {
          case "thinking": {
            const thinkingData = data as SSEEventData["thinking"];
            set({
              thinkingContent: thinkingData.content,
              isLoading: true,
            });
            break;
          }

          case "tool_call": {
            const toolData = data as SSEEventData["tool_call"];
            const toolCallMsgId = generateId("tool");

            // 更新 currentToolCalls
            const updatedTools = new Map(get().currentToolCalls);
            updatedTools.set(toolData.id, {
              id: toolData.id,
              tool: toolData.tool,
              args: toolData.args,
              status: "running",
            });

            // 跟踪 tool_call_id -> msg_id 映射
            pendingToolCallMsgIds.set(toolData.id, toolCallMsgId);

            // 添加工具调用消息卡片
            const toolCallMsg: AgentMessage = {
              id: toolCallMsgId,
              type: "tool_call",
              role: "assistant",
              content: "",
              timestamp: Date.now(),
              toolCall: {
                id: toolData.id,
                tool: toolData.tool,
                args: toolData.args,
                status: "running",
              },
            };

            set((state) => ({
              sessions: state.sessions.map((s) =>
                s.id === sid
                  ? { ...s, messages: [...s.messages, toolCallMsg], updatedAt: Date.now() }
                  : s
              ),
              currentToolCalls: updatedTools,
            }));
            break;
          }

          case "tool_result": {
            const resultData = data as SSEEventData["tool_result"];
            const updatedTools = new Map(get().currentToolCalls);

            // 更新工具调用状态
            if (updatedTools.has(resultData.tool_call_id)) {
              const existing = updatedTools.get(resultData.tool_call_id)!;
              updatedTools.set(resultData.tool_call_id, {
                ...existing,
                status: resultData.success ? "success" : "error",
                result: resultData.result,
              });

              // 更新对应的消息卡片
              const msgId = pendingToolCallMsgIds.get(resultData.tool_call_id);

              if (msgId) {
                set((state) => ({
                  sessions: state.sessions.map((s) =>
                    s.id === sid
                      ? {
                          ...s,
                          messages: s.messages.map((m) =>
                            m.id === msgId && m.toolCall
                              ? {
                                  ...m,
                                  toolCall: {
                                    ...m.toolCall,
                                    status: resultData.success ? "success" as const : "error" as const,
                                    result: resultData.result,
                                  },
                                }
                              : m
                          ),
                        }
                      : s
                  ),
                  currentToolCalls: updatedTools,
                }));
              }

              // ask_user 追问处理：提取 question 创建追问消息
              if (existing.tool === "ask_user" && resultData.success) {
                const askResult = resultData.result as Record<string, unknown> | undefined;
                const question = (askResult?.question as string) || (existing.args?.question as string) || "";
                if (question) {
                  const followUpMsg: AgentMessage = {
                    id: generateId("followup"),
                    type: "text",
                    role: "assistant",
                    content: question,
                    timestamp: Date.now(),
                    isFollowUp: true,
                  };
                  set((state) => ({
                    sessions: state.sessions.map((s) =>
                      s.id === sid
                        ? { ...s, messages: [...s.messages, followUpMsg], updatedAt: Date.now() }
                        : s
                    ),
                  }));
                }
              }

              pendingToolCallMsgIds.delete(resultData.tool_call_id);
            }
            break;
          }

          case "content": {
            const contentData = data as SSEEventData["content"];
            // content 事件可能包含流式文本片段或完整文本
            const textContent = contentData.text || (data as { content?: string }).content || "";

            if (!currentAssistantMsgId) {
              // 创建新的 assistant 消息
              currentAssistantMsgId = generateId("asst");
              currentAssistantContent = textContent;

              const assistantMsg: AgentMessage = {
                id: currentAssistantMsgId,
                type: "text",
                role: "assistant",
                content: textContent,
                timestamp: Date.now(),
              };

              set((state) => ({
                sessions: state.sessions.map((s) =>
                  s.id === sid
                    ? { ...s, messages: [...s.messages, assistantMsg], updatedAt: Date.now() }
                    : s
                ),
              }));
            } else {
              // 追加到现有 assistant 消息
              currentAssistantContent += textContent;

              set((state) => ({
                sessions: state.sessions.map((s) =>
                  s.id === sid
                    ? {
                        ...s,
                        messages: s.messages.map((m) =>
                          m.id === currentAssistantMsgId
                            ? { ...m, content: currentAssistantContent }
                            : m
                        ),
                      }
                    : s
                ),
              }));
            }
            break;
          }

          case "created": {
            const createdData = data as SSEEventData["created"];
            // 关联到最后的 assistant 消息或用户消息
            if (currentAssistantMsgId) {
              set((state) => ({
                sessions: state.sessions.map((s) =>
                  s.id === sid
                    ? {
                        ...s,
                        messages: s.messages.map((m) =>
                          m.id === currentAssistantMsgId
                            ? {
                                ...m,
                                entryChange: {
                                  id: createdData.id,
                                  type: createdData.type,
                                  title: createdData.title,
                                },
                              }
                            : m
                        ),
                      }
                    : s
                ),
              }));
            }
            break;
          }

          case "updated": {
            const updatedData = data as SSEEventData["updated"];
            if (currentAssistantMsgId) {
              set((state) => ({
                sessions: state.sessions.map((s) =>
                  s.id === sid
                    ? {
                        ...s,
                        messages: s.messages.map((m) =>
                          m.id === currentAssistantMsgId
                            ? {
                                ...m,
                                entryChange: {
                                  id: updatedData.id,
                                  changes: updatedData.changes,
                                },
                              }
                            : m
                        ),
                      }
                    : s
                ),
              }));
            }
            break;
          }

          case "error": {
            const errorData = data as SSEEventData["error"];
            set({ error: errorData.message });
            // 不在这里设置 isLoading=false，等 done 事件
            break;
          }

          case "done": {
            set(() => ({
              isLoading: false,
              isStreaming: false,
              thinkingContent: "",
              // 保留 currentToolCalls 用于 UI 展示，直到下次 sendMessage 时清空
            }));

            // 如果没有 assistant 消息被创建（例如只有 tool_call），
            // 且没有 error，说明 Agent 可能需要追问
            // 触发追问回调让 UI 聚焦输入框
            const session = get().sessions.find((s) => s.id === sid);
            const hasAssistantText = session?.messages.some(
              (m) => m.role === "assistant" && m.type === "text" && m.content.trim()
            );
            // 如果没有 assistant 文本消息但有工具调用，Agent 可能还有后续输出
            // 如果都没有，可能是追问场景
            if (!hasAssistantText && session?.messages.length) {
              // 延迟触发，确保 UI 已更新
              if (_followUpCallback) {
                setTimeout(_followUpCallback, 100);
              }
            }
            break;
          }

          default:
            // 忽略未知事件类型
            break;
        }
      }
    } catch (err: unknown) {
      if (signal.aborted) {
        // 用户主动取消，不视为错误
        return;
      }
      const errorMessage = err instanceof Error ? err.message : "未知错误";
      set({ isLoading: false, isStreaming: false, error: errorMessage });
    } finally {
      // 确保 loading 状态被重置
      set((state) => {
        if (state.isLoading || state.isStreaming) {
          return { isLoading: false, isStreaming: false };
        }
        return {};
      });
    }
  },

  cancelStream: () => {
    if (_activeAbortController) {
      _activeAbortController.abort();
      _activeAbortController = null;
    }
    set({ isLoading: false, isStreaming: false });
  },

  // ── 状态操作 ──

  setPageContext: (ctx: AgentPageContext | null) => {
    set({ pageContext: ctx });
  },

  setPageExtra: (extra: Record<string, string | number> | null) => {
    set({ pageExtra: extra });
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
    } catch {
      // 删除失败不修改本地状态，避免前后端分叉
    }
  },

  updateSessionTitle: async (id: string, title: string) => {
    try {
      await sessionApi.updateTitle(id, title);
      set((state) => ({
        sessions: state.sessions.map((s) =>
          s.id === id ? { ...s, title } : s
        ),
      }));
    } catch {
      // 更新失败不修改本地状态，避免前后端分叉
    }
  },

  fetchSessions: async () => {
    try {
      const data = await sessionApi.list();
      const sessions: AgentSession[] = data.map((s) => ({
        id: s.id,
        title: s.title,
        messages: [],
        createdAt: new Date(s.created_at).getTime(),
        updatedAt: new Date(s.updated_at).getTime(),
      }));
      set({ sessions });
    } catch {
      // 静默处理获取失败
    }
  },

  loadSessionMessages: async (sessionId: string) => {
    try {
      const msgs = await sessionApi.getMessages(sessionId);
      const agentMessages: AgentMessage[] = msgs.flatMap((m: MessageInfo, i: number) => {
        const base = {
          id: m.id || `hist-${i}`,
          role: m.role as "user" | "assistant",
          timestamp: new Date(m.timestamp).getTime(),
        };

        const results: AgentMessage[] = [];

        // 有 tool_calls → 插入 tool_call 消息
        if (m.tool_calls && m.tool_calls.length > 0) {
          for (const tc of m.tool_calls) {
            results.push({
              ...base,
              id: `${base.id}-tc-${tc.id}`,
              type: "tool_call" as const,
              content: "",
              toolCall: {
                id: tc.id,
                tool: tc.name,
                args: tc.args,
                status: "success" as const,
              },
            });
          }
        }

        // 有文本内容 → 插入文本消息
        if (m.content) {
          results.push({
            ...base,
            id: `${base.id}-text`,
            type: "text" as const,
            content: m.content,
          });
        }

        return results;
      });
      set((state) => ({
        sessions: state.sessions.map((s) =>
          s.id === sessionId
            ? { ...s, messages: agentMessages }
            : s
        ),
      }));
    } catch {
      // 加载历史消息失败不影响当前会话
    }
  },

  setPanelHeight: (height: number) => {
    set({ panelHeight: height });
    savePanelHeight(height);
  },

  clearError: () => {
    set({ error: null });
  },

  setFollowUpCallback: (cb: FollowUpCallback) => {
    _followUpCallback = cb;
  },
}));
