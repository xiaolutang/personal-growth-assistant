import { useCallback, useEffect, useRef, useState, useMemo } from "react";
import { Sparkles, X, Send, Loader2, Trash2 } from "lucide-react";
import { useLocation } from "react-router-dom";
import { sendAIChat, type AIChatContext } from "@/services/api";
import { useChatStore } from "@/stores/chatStore";
import { useTaskStore } from "@/stores/taskStore";
import { useIsMobile } from "@/hooks/useIsMobile";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface PageAIAssistantProps {
  pageContext?: AIChatContext;
  pageData?: Record<string, string | number>;
}

const FLOATING_GAP = 16;
const MOBILE_NAV_HEIGHT = 56;

export function PageAIAssistant({ pageContext, pageData }: PageAIAssistantProps) {
  const panelHeight = useChatStore((state) => state.panelHeight);
  const isMobile = useIsMobile();
  const location = useLocation();
  const tasks = useTaskStore((state) => state.tasks);
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // 自动感知当前页面并生成上下文
  const autoPageData = useMemo((): Record<string, string | number> => {
    const path = location.pathname;
    const today = new Date().toISOString().split("T")[0];

    if (path === "/" || path === "") {
      const todayTasks = tasks.filter((t) =>
        t.planned_date?.startsWith(today) || t.created_at?.startsWith(today)
      );
      const overdue = tasks.filter((t) =>
        t.planned_date && t.planned_date.split("T")[0] < today && t.status !== "complete"
      );
      return { todo_count: todayTasks.length, overdue_count: overdue.length, total_tasks: tasks.length };
    }
    if (path === "/explore") {
      const recentTitles = tasks.slice(0, 5).map((t) => t.title).join(", ");
      return { total_entries: tasks.length, recent_titles: recentTitles || "暂无" };
    }
    if (path === "/tasks") {
      const doing = tasks.filter((t) => t.category === "task" && t.status === "doing").length;
      const complete = tasks.filter((t) => t.category === "task" && t.status === "complete").length;
      return { total_tasks: tasks.filter((t) => t.category === "task").length, doing, complete };
    }
    if (path === "/review") {
      return { total_entries: tasks.length };
    }
    return {};
  }, [location.pathname, tasks]);

  const effectivePageData = pageData ?? autoPageData;

  // 计算 bottom 偏移：FloatingChat panelHeight + FeedbackButton 区域(~80px) + gap
  const bottomOffset = panelHeight + 80 + FLOATING_GAP + (isMobile ? MOBILE_NAV_HEIGHT : 0);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  function handleClose() {
    setIsOpen(false);
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }

  function handleToggle() {
    if (isOpen) {
      handleClose();
    } else {
      setIsOpen(true);
    }
  }

  function handleClearChat() {
    setMessages([]);
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setIsStreaming(false);
  }

  async function handleSend() {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;

    const userMessage: ChatMessage = { role: "user", content: trimmed };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput("");
    setIsStreaming(true);

    const assistantMessage: ChatMessage = { role: "assistant", content: "" };
    setMessages((prev) => [...prev, assistantMessage]);

    try {
      abortRef.current = new AbortController();
      // 构建带历史消息和页面数据的上下文
      const contextWithHistory: AIChatContext = {
        ...pageContext,
        page_data: effectivePageData,
        messages: newMessages.slice(-10).map((m) => ({ role: m.role, content: m.content })),
      };
      const response = await sendAIChat(trimmed, contextWithHistory);
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (reader) {
        let accumulated = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const text = decoder.decode(value, { stream: true });
          const lines = text.split("\n");

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = line.slice(6);
              if (data === "[DONE]") continue;
              try {
                const parsed = JSON.parse(data);
                if (parsed.token) {
                  accumulated += parsed.token;
                  const currentContent = accumulated;
                  setMessages((prev) => {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                      role: "assistant",
                      content: currentContent,
                    };
                    return updated;
                  });
                }
                if (parsed.content && !parsed.token) {
                  accumulated += parsed.content;
                  const currentContent = accumulated;
                  setMessages((prev) => {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                      role: "assistant",
                      content: currentContent,
                    };
                    return updated;
                  });
                }
              } catch {
                // non-JSON data
              }
            }
          }
        }

        if (!accumulated) {
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              role: "assistant",
              content: "抱歉，AI 暂时无法回复，请稍后重试。",
            };
            return updated;
          });
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name !== "AbortError") {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: `请求失败：${error.message}`,
          };
          return updated;
        });
      }
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div
      className="fixed right-4 z-50 flex flex-col items-end gap-3 sm:right-6"
      style={{ bottom: `${bottomOffset}px` }}
    >
      {/* Chat Panel */}
      {isOpen && (
        <div className="w-[min(24rem,calc(100vw-2rem))] rounded-2xl border border-border bg-background/95 shadow-xl backdrop-blur overflow-hidden flex flex-col"
          style={{ maxHeight: "500px" }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-indigo-500" />
              <span className="text-sm font-semibold">日知 AI</span>
            </div>
            <div className="flex items-center gap-1">
              {messages.length > 0 && (
                <button
                  type="button"
                  onClick={handleClearChat}
                  className="h-7 w-7 inline-flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                  aria-label="清空对话"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
              <button
                type="button"
                onClick={handleClose}
                className="h-7 w-7 inline-flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                aria-label="关闭"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3" style={{ minHeight: "200px" }}>
            {messages.length === 0 && (
              <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                向日知 AI 提问吧
              </div>
            )}
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-xl px-3 py-2 text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-indigo-500 text-white"
                      : "bg-muted text-foreground"
                  }`}
                >
                  {msg.content || (
                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="border-t border-border p-3 shrink-0">
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入消息..."
                disabled={isStreaming}
                className="flex-1 h-9 rounded-lg border border-input bg-background px-3 py-1 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
              />
              <button
                type="button"
                onClick={handleSend}
                disabled={!input.trim() || isStreaming}
                className="h-9 w-9 inline-flex items-center justify-center rounded-lg bg-indigo-500 text-white hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                aria-label="发送"
              >
                {isStreaming ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Floating Button */}
      <button
        type="button"
        onClick={handleToggle}
        className="h-12 w-12 rounded-full shadow-lg flex items-center justify-center bg-indigo-500 text-white hover:bg-indigo-600 transition-colors"
        aria-label={isOpen ? "关闭日知 AI" : "打开日知 AI"}
      >
        <Sparkles className="h-5 w-5" />
      </button>
    </div>
  );
}
