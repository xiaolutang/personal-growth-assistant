/**
 * FloatingChat.tsx — 浮动对话面板（使用 agentStore）
 *
 * 替代旧版基于 chatStore 的实现，现在使用 Agent ReAct 架构：
 * - 使用 agentStore 管理对话状态
 * - SSE 事件由 agentStore 的 sendMessage 处理
 * - 保留浮动面板 UI（拖拽调整高度、路由感知）
 * - 复用 AgentChat 子组件（MessageList、ChatInput 等）
 */
import { useState, useEffect, useCallback, useMemo } from "react";
import { useLocation } from "react-router-dom";
import {
  Sparkles,
  GripHorizontal,
  RotateCcw,
} from "lucide-react";
import { useAgentStore, type AgentPageContext } from "@/stores/agentStore";
import { useUserStore } from "@/stores/userStore";
import { MessageList } from "@/components/AgentChat/MessageList";
import { ChatInput } from "@/components/AgentChat/ChatInput";
import { ThinkingIndicator } from "@/components/AgentChat/ThinkingIndicator";
import { AgentPrompt } from "@/components/AgentChat/AgentPrompt";
import { useIsMobile } from "@/hooks/useIsMobile";
import { trackEvent } from "@/lib/analytics";

// 最小和最大面板高度
const MIN_HEIGHT = 200;
const MAX_HEIGHT_DESKTOP = 600;
const MOBILE_NAV_HEIGHT = 56; // h-14 = 56px
const MOBILE_MAX_RATIO = 0.7; // 移动端面板不超过可视区域 70%

export function FloatingChat() {
  const isMobile = useIsMobile();
  const user = useUserStore((state) => state.user);
  const [input, setInput] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  const {
    currentSessionId,
    isLoading,
    isStreaming,
    thinkingContent,
    error,
    getCurrentSession,
    sendMessage,
    resetCurrentSession,
    clearError,
    createSession,
    panelHeight,
    setPanelHeight,
    pageContext,
    setPageContext,
  } = useAgentStore();

  const currentSession = getCurrentSession();
  const messages = currentSession?.messages ?? [];
  const hasMessages = messages.length > 0;

  // 最后一条 assistant 消息中 isFollowUp 标记
  const lastAssistantMsg = [...messages].reverse().find((m) => m.role === "assistant" && m.type === "text");
  const followUpPrompt = lastAssistantMsg?.isFollowUp ? lastAssistantMsg.content : null;

  // 路由感知
  const location = useLocation();

  // 新用户首页隐藏 FloatingChat，避免双入口混淆
  const isNewUser = user ? !user.onboarding_completed : false;
  const base = (import.meta as { env?: { BASE_URL?: string } }).env?.BASE_URL?.replace(/\/$/, "") || "";
  const relativePath = base ? location.pathname.replace(base, "") || "/" : location.pathname;
  if (isNewUser && relativePath === "/") {
    return null;
  }

  // 路由变化时更新 pageContext
  useEffect(() => {
    const path = location.pathname;
    const base = (import.meta as { env?: { BASE_URL?: string } }).env?.BASE_URL?.replace(/\/$/, "") || "";
    const rp = base ? path.replace(base, "") || "/" : path;

    let ctx: AgentPageContext | null = null;

    if (rp === "/" || rp === "") {
      ctx = { page_type: "home" };
    } else if (rp.startsWith("/explore")) {
      ctx = { page_type: "explore" };
    } else if (rp.startsWith("/entries/")) {
      const entryId = rp.split("/entries/")[1]?.split("/")[0] || undefined;
      ctx = { page_type: "entry", entry_id: entryId };
    } else if (rp.startsWith("/review")) {
      ctx = { page_type: "review" };
    } else if (rp.startsWith("/graph")) {
      ctx = { page_type: "graph" };
    }

    const current = pageContext;
    if (
      current?.page_type !== ctx?.page_type ||
      current?.entry_id !== ctx?.entry_id
    ) {
      setPageContext(ctx);
    }
  }, [location.pathname]);

  // 发送消息
  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    setInput("");
    trackEvent("chat_message_sent", { source: "floating_agent_chat" });

    // 确保有活跃会话
    let sid = currentSessionId;
    if (!sid) {
      sid = createSession();
    }

    await sendMessage({
      text,
      sessionId: sid,
      pageContext: pageContext ?? undefined,
    });
  }, [input, isLoading, sendMessage, currentSessionId, createSession, pageContext]);

  // 重置对话
  const handleReset = useCallback(() => {
    resetCurrentSession();
    setInput("");
    clearError();
  }, [resetCurrentSession, clearError]);

  // 移动端最大高度
  const mobileMaxHeight = useMemo(
    () => Math.floor(window.innerHeight * MOBILE_MAX_RATIO) - MOBILE_NAV_HEIGHT,
    []
  );
  const effectiveMaxHeight = isMobile ? mobileMaxHeight : MAX_HEIGHT_DESKTOP;

  // 拖拽调整高度
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const newHeight = window.innerHeight - e.clientY;
      setPanelHeight(Math.min(effectiveMaxHeight, Math.max(MIN_HEIGHT, newHeight)));
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 0) return;
      const newHeight = window.innerHeight - e.touches[0].clientY;
      setPanelHeight(Math.min(effectiveMaxHeight, Math.max(MIN_HEIGHT, newHeight)));
    };

    const handleEnd = () => {
      setIsDragging(false);
      document.body.style.overflow = "";
    };

    document.body.style.overflow = "hidden";

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleEnd);
    document.addEventListener("touchmove", handleTouchMove, { passive: false });
    document.addEventListener("touchend", handleEnd);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleEnd);
      document.removeEventListener("touchmove", handleTouchMove);
      document.removeEventListener("touchend", handleEnd);
      document.body.style.overflow = "";
    };
  }, [isDragging, setPanelHeight, effectiveMaxHeight]);

  // 移动端底部留出 NavBar 空间
  const mobileBottomOffset = isMobile ? MOBILE_NAV_HEIGHT : 0;

  // 构建 footer（思考指示器或追问提示）
  const footer = isLoading ? (
    <ThinkingIndicator content={thinkingContent || undefined} />
  ) : followUpPrompt ? (
    <AgentPrompt prompt={followUpPrompt} />
  ) : null;

  return (
    <div
      className={`fixed left-0 right-0 lg:left-64 bg-background border-t z-50 flex flex-col ${
        isDragging ? "select-none" : ""
      }`}
      style={{
        height: panelHeight,
        bottom: mobileBottomOffset,
      }}
    >
      {/* 拖拽条 */}
      <div
        className="flex items-center justify-center h-6 cursor-ns-resize hover:bg-muted/50 border-b shrink-0"
        onMouseDown={handleMouseDown}
        onTouchStart={handleTouchStart}
      >
        <GripHorizontal className="h-4 w-4 text-muted-foreground" />
      </div>

      {/* 当前会话信息 */}
      <div className="flex items-center justify-between px-3 py-2 border-b bg-muted/30 shrink-0">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-indigo-500 shrink-0" />
          <span className="text-sm font-medium truncate">{currentSession?.title || "新对话"}</span>
          {isStreaming && (
            <span className="text-xs text-indigo-500 animate-pulse">思考中</span>
          )}
        </div>
        {hasMessages && (
          <button
            type="button"
            onClick={handleReset}
            className="h-6 w-6 inline-flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            aria-label="重置对话"
          >
            <RotateCcw className="h-3 w-3" />
          </button>
        )}
      </div>

      {/* 消息列表 */}
      {(hasMessages || isLoading) && (
        <MessageList messages={messages} footer={footer} className="flex-1 min-h-0" />
      )}

      {/* 错误提示 */}
      {error && (
        <div className="px-3 py-1.5 text-xs text-red-500 bg-red-50 dark:bg-red-950/20 border-t border-red-200 dark:border-red-800">
          {error}
        </div>
      )}

      {/* 输入区域 */}
      <ChatInput
        value={input}
        onChange={setInput}
        onSend={handleSend}
        isLoading={isLoading}
        placeholder="输入消息..."
      />
    </div>
  );
}
