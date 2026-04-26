import { useCallback, useEffect, useRef, useState } from "react";
import { Sparkles, Send, Loader2, Trash2, ChevronDown, ChevronUp } from "lucide-react";
import { sendAIChat, type AIChatContext } from "@/services/api";
import { trackEvent } from "@/lib/analytics";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface Suggestion {
  label: string;
  message: string;
}

interface PageChatPanelProps {
  title?: string;
  welcomeMessage?: string;
  greetingMessage?: string;
  suggestions?: Suggestion[];
  pageContext?: AIChatContext;
  pageData?: Record<string, string | number>;
  defaultCollapsed?: boolean;
  onFirstResponse?: () => void;
  className?: string;
}

export function PageChatPanel({
  title = "日知 AI",
  welcomeMessage = "有什么想聊的？",
  greetingMessage,
  suggestions = [],
  pageContext,
  pageData,
  defaultCollapsed = false,
  onFirstResponse,
  className = "",
}: PageChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  // 当外部 defaultCollapsed 变化时同步内部状态（支持父组件驱动展开/收起）
  useEffect(() => {
    setCollapsed(defaultCollapsed);
  }, [defaultCollapsed]);

  // greetingMessage 注入：mount 时将 greeting 显示为初始 assistant 消息
  useEffect(() => {
    if (greetingMessage && messages.length === 0) {
      setMessages([{ role: "assistant", content: greetingMessage }]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  function handleClearChat() {
    setMessages([]);
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setIsStreaming(false);
  }

  async function handleSend(text?: string) {
    const trimmed = (text ?? input).trim();
    if (!trimmed || isStreaming) return;

    const userMessage: ChatMessage = { role: "user", content: trimmed };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput("");
    setIsStreaming(true);
    trackEvent("chat_message_sent", { source: "page_chat", page: pageContext?.page });

    const assistantMessage: ChatMessage = { role: "assistant", content: "" };
    setMessages((prev) => [...prev, assistantMessage]);

    // 展开面板
    if (collapsed) setCollapsed(false);

    try {
      abortRef.current = new AbortController();
      const contextWithHistory: AIChatContext = {
        ...pageContext,
        page_data: pageData,
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
                const token = parsed.token || parsed.content || "";
                if (token) {
                  accumulated += token;
                  const currentContent = accumulated;
                  setMessages((prev) => {
                    const updated = [...prev];
                    updated[updated.length - 1] = { role: "assistant", content: currentContent };
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

        // 收到有效 AI 内容后触发 onFirstResponse（空回复不触发，防重复由父组件管理）
        if (accumulated && onFirstResponse) {
          onFirstResponse();
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

  function handleSuggestionClick(suggestion: Suggestion) {
    handleSend(suggestion.message);
  }

  return (
    <div className={`rounded-xl border border-border bg-background ${className}`}>
      {/* Header */}
      <button
        type="button"
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-muted/50 transition-colors rounded-t-xl"
      >
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-indigo-500" />
          <span className="text-sm font-semibold">{title}</span>
        </div>
        <div className="flex items-center gap-1">
          {messages.length > 0 && !collapsed && (
            <span
              role="button"
              tabIndex={0}
              onClick={(e) => { e.stopPropagation(); handleClearChat(); }}
              onKeyDown={(e) => { if (e.key === "Enter") { e.stopPropagation(); handleClearChat(); } }}
              className="h-7 w-7 inline-flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </span>
          )}
          {collapsed ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </button>

      {/* Body */}
      {!collapsed && (
        <>
          {/* Messages */}
          <div className="px-4 pb-3 space-y-3 max-h-80 overflow-y-auto">
            {messages.length === 0 && (
              <div className="text-center py-4">
                <p className="text-sm text-muted-foreground mb-3">{welcomeMessage}</p>
                {suggestions.length > 0 && (
                  <div className="flex flex-wrap gap-2 justify-center">
                    {suggestions.map((s) => (
                      <button
                        key={s.label}
                        type="button"
                        onClick={() => handleSuggestionClick(s)}
                        className="text-xs px-3 py-1.5 rounded-full border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                      >
                        {s.label}
                      </button>
                    ))}
                  </div>
                )}
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
          <div className="border-t border-border p-3">
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
                onClick={() => handleSend()}
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
        </>
      )}
    </div>
  );
}
