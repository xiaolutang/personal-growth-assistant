import { useState, useCallback, useRef, useEffect } from "react";
import { Sparkles, RotateCcw } from "lucide-react";
import { useAgentStore } from "@/stores/agentStore";
import { MessageList } from "./MessageList";
import { ChatInput, type ChatInputHandle } from "./ChatInput";
import { ThinkingIndicator } from "./ThinkingIndicator";
import { AgentPrompt } from "./AgentPrompt";

interface AgentChatProps {
  /** 标题 */
  title?: string;
  /** 欢迎文本（无消息时显示） */
  welcomeMessage?: string;
  /** 建议标签列表 */
  suggestions?: { label: string; message: string }[];
  /** 额外 className */
  className?: string;
}

export function AgentChat({
  title = "日知 Agent",
  welcomeMessage = "有什么想聊的？",
  suggestions = [],
  className,
}: AgentChatProps) {
  const [input, setInput] = useState("");
  const chatInputRef = useRef<ChatInputHandle>(null);

  const {
    isLoading,
    isStreaming,
    thinkingContent,
    error,
    getCurrentSession,
    sendMessage,
    resetCurrentSession,
    clearError,
    currentSessionId,
    setFollowUpCallback,
  } = useAgentStore();

  // 注册 ask_user 追问后的自动聚焦回调
  useEffect(() => {
    setFollowUpCallback(() => {
      chatInputRef.current?.focus();
    });
    return () => setFollowUpCallback(null);
  }, [setFollowUpCallback]);

  const currentSession = getCurrentSession();
  const messages = currentSession?.messages ?? [];
  const hasMessages = messages.length > 0;

  // 最后一条 assistant 消息中 isFollowUp 标记
  const lastAssistantMsg = [...messages].reverse().find((m) => m.role === "assistant" && m.type === "text");
  const followUpPrompt = lastAssistantMsg?.isFollowUp ? lastAssistantMsg.content : null;

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    setInput("");
    await sendMessage({
      text,
      sessionId: currentSessionId ?? undefined,
    });
  }, [input, isLoading, sendMessage, currentSessionId]);

  const handleSuggestionClick = useCallback(
    (message: string) => {
      setInput(message);
    },
    [],
  );

  const handleReset = useCallback(() => {
    resetCurrentSession();
    setInput("");
    clearError();
  }, [resetCurrentSession, clearError]);

  // 构建消息列表的 footer（思考指示器或追问提示）
  const footer = isLoading ? (
    <ThinkingIndicator content={thinkingContent || undefined} />
  ) : followUpPrompt ? (
    <AgentPrompt prompt={followUpPrompt} />
  ) : null;

  return (
    <div className={`flex flex-col rounded-xl border border-border bg-background ${className ?? ""}`}>
      {/* 头部 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-indigo-500" />
          <span className="text-sm font-semibold">{title}</span>
          {isStreaming && (
            <span className="text-xs text-indigo-500 animate-pulse">思考中</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {hasMessages && (
            <button
              type="button"
              onClick={handleReset}
              className="h-7 w-7 inline-flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              aria-label="重置对话"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* 空状态 */}
      {!hasMessages && !isLoading && (
        <div className="flex-1 flex flex-col items-center justify-center py-8 px-4 text-center">
          <div className="h-12 w-12 rounded-full bg-indigo-50 dark:bg-indigo-900/30 flex items-center justify-center mb-3">
            <Sparkles className="h-6 w-6 text-indigo-500" />
          </div>
          <p className="text-sm text-muted-foreground mb-4">{welcomeMessage}</p>
          {suggestions.length > 0 && (
            <div className="flex flex-wrap gap-2 justify-center">
              {suggestions.map((s) => (
                <button
                  key={s.label}
                  type="button"
                  onClick={() => handleSuggestionClick(s.message)}
                  className="text-xs px-3 py-1.5 rounded-full border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                >
                  {s.label}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 消息列表 */}
      {(hasMessages || isLoading) && (
        <MessageList messages={messages} footer={footer} className="max-h-96" />
      )}

      {/* 错误提示 */}
      {error && (
        <div className="px-4 py-2 text-xs text-red-500 bg-red-50 dark:bg-red-950/20 border-t border-red-200 dark:border-red-800">
          {error}
        </div>
      )}

      {/* 输入框 */}
      <ChatInput
        ref={chatInputRef}
        value={input}
        onChange={setInput}
        onSend={handleSend}
        isLoading={isLoading}
        placeholder="输入消息..."
      />
    </div>
  );
}
