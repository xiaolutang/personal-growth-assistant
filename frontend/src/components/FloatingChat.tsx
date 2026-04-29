/**
 * FloatingChat.tsx — 悬浮按钮 + 展开聊天面板
 *
 * 改造为右下角悬浮按钮模式：
 * - 默认收起：右下角 Sparkles 图标悬浮按钮（48x48）
 * - 点击展开：聊天面板从右下角弹出，固定宽度 400px，可拖拽高度
 * - 面板内保留完整功能：消息列表、输入框、拖拽调高、路由感知
 * - 点击面板外部区域或关闭按钮收起面板
 * - 有未读消息或正在对话时悬浮按钮显示脉冲动画
 *
 * 复用 AgentChat 子组件（MessageList、ChatInput 等）
 */
import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useLocation } from "react-router-dom";
import {
  Sparkles,
  GripHorizontal,
  RotateCcw,
  X,
  MessageSquare,
  History,
} from "lucide-react";
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover";
import { FeedbackPanel } from "@/components/FeedbackPanel";
import { SessionList } from "@/components/SessionList";
import { useAgentStore, type AgentPageContext } from "@/stores/agentStore";

import { cn } from "@/lib/utils";
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
const PANEL_WIDTH = 400; // 桌面端面板宽度
const BASE_URL = (import.meta as { env?: { BASE_URL?: string } }).env?.BASE_URL?.replace(/\/$/, "") || "";
const GREETING_SEEN_KEY = "chat-greeting-seen";

/** 路由路径 → AgentPageContext 纯函数映射 */
function parsePageContext(pathname: string): AgentPageContext | null {
  const rp = BASE_URL ? pathname.replace(BASE_URL, "") || "/" : pathname;
  if (rp === "/" || rp === "") return { page_type: "home" };
  if (rp.startsWith("/explore")) return { page_type: "explore" };
  if (rp.startsWith("/entries/")) {
    const entryId = rp.split("/entries/")[1]?.split("/")[0] || undefined;
    return { page_type: "entry", entry_id: entryId };
  }
  if (rp.startsWith("/review")) return { page_type: "review" };
  if (rp.startsWith("/graph")) return { page_type: "graph" };
  return null;
}

export function FloatingChat() {
  const isMobile = useIsMobile();
  const [input, setInput] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [showSessionList, setShowSessionList] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

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
    switchSession,
    panelHeight,
    setPanelHeight,
    pageContext,
    setPageContext,
    fetchSessions,
  } = useAgentStore();

  // greeting 防重复发送标记
  const greetingSentRef = useRef(false);

  const currentSession = getCurrentSession();
  const messages = currentSession?.messages ?? [];
  const hasMessages = messages.length > 0;

  // 最后一条 assistant 消息中 isFollowUp 标记（从末尾查找，避免 reverse 拷贝）
  let lastAssistantMsg: typeof messages[0] | undefined;
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === "assistant" && messages[i].type === "text") {
      lastAssistantMsg = messages[i];
      break;
    }
  }
  const followUpPrompt = lastAssistantMsg?.isFollowUp ? lastAssistantMsg.content : null;

  // 是否有活跃对话（正在流式传输或加载中）
  const isActive = isLoading || isStreaming || hasMessages;

  // 路由感知
  const location = useLocation();

  // 挂载时加载会话列表数据（不依赖面板展开）
  useEffect(() => {
    fetchSessions();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 路由变化时更新 pageContext
  useEffect(() => {
    const ctx = parsePageContext(location.pathname);
    const current = pageContext;
    if (
      current?.page_type !== ctx?.page_type ||
      current?.entry_id !== ctx?.entry_id
    ) {
      setPageContext(ctx);
    }
  }, [location.pathname]);

  // 首次展开面板时自动发送 greeting（localStorage 标记，所有用户只触发一次）
  useEffect(() => {
    if (!isExpanded || greetingSentRef.current) return;

    // 已看过引导，跳过
    try {
      if (localStorage.getItem(GREETING_SEEN_KEY)) return;
    } catch {
      return; // SSR 或隐私模式下 localStorage 不可用
    }

    greetingSentRef.current = true;
    try {
      localStorage.setItem(GREETING_SEEN_KEY, "1");
    } catch {
      // 静默降级
    }

    // 创建会话并发送隐藏 greeting
    const sid = createSession();
    sendMessage({
      text: "__greeting__",
      sessionId: sid,
      pageContext: useAgentStore.getState().pageContext ?? undefined,
      hidden: true,
    }).catch(() => {
      // 发送失败静默降级，不阻塞面板使用
    });
  }, [isExpanded]); // eslint-disable-line react-hooks/exhaustive-deps

  // 点击面板外部收起（使用 data-chat-boundary 自有属性标记，不依赖第三方内部 DOM 结构）
  useEffect(() => {
    if (!isExpanded) return;

    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Node;
      // 忽略自有边界内的点击（反馈 Popover 等）
      if ((target as HTMLElement).closest?.("[data-chat-boundary]")) {
        return;
      }
      if (panelRef.current && !panelRef.current.contains(target)) {
        setIsExpanded(false);
        setShowSessionList(false);
      }
    };

    // 延迟添加监听，避免当前点击事件立即触发
    const timer = setTimeout(() => {
      document.addEventListener("mousedown", handleClickOutside);
    }, 0);

    return () => {
      clearTimeout(timer);
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isExpanded]);

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

  // 切换会话
  const handleSwitchSession = useCallback((sessionId: string) => {
    switchSession(sessionId);
    setShowSessionList(false);
  }, [switchSession]);

  // 展开/收起面板
  const handleToggleExpand = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  const handleClosePanel = useCallback(() => {
    setIsExpanded(false);
    setShowSessionList(false);
  }, []);

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

  // 悬浮按钮定位
  const fabBottom = mobileBottomOffset + 16; // 16px 间距

  return (
    <>
      {/* 悬浮按钮（收起状态） */}
      {!isExpanded && (
        <button
          type="button"
          onClick={handleToggleExpand}
          className={`fixed right-4 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-500 text-white shadow-lg transition-transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:ring-offset-2 ${
            isActive ? "animate-pulse" : ""
          }`}
          style={{ bottom: fabBottom }}
          aria-label="打开聊天"
          data-testid="chat-fab"
        >
          <Sparkles className="h-5 w-5" />
        </button>
      )}

      {/* 聊天面板（展开状态） */}
      {isExpanded && (
        <div
          ref={panelRef}
          className={`fixed z-50 flex flex-col rounded-xl border bg-background shadow-2xl ${
            isDragging ? "select-none" : ""
          } ${isMobile ? "left-2 right-2" : ""}`}
          style={{
            height: panelHeight,
            bottom: mobileBottomOffset + 8,
            right: isMobile ? undefined : 16,
            width: isMobile ? undefined : PANEL_WIDTH,
          }}
          data-testid="chat-panel"
        >
          {/* 拖拽条 */}
          <div
            className="flex items-center justify-center h-6 cursor-ns-resize hover:bg-muted/50 border-b shrink-0 rounded-t-xl"
            onMouseDown={handleMouseDown}
            onTouchStart={handleTouchStart}
          >
            <GripHorizontal className="h-4 w-4 text-muted-foreground" />
          </div>

          {/* 当前会话信息 + 关闭按钮 */}
          <div className="flex items-center justify-between px-3 py-2 border-b bg-muted/30 shrink-0">
            <div className="flex items-center gap-2 min-w-0">
              <Sparkles className="h-4 w-4 text-indigo-500 shrink-0" />
              <span className="text-sm font-medium truncate">{currentSession?.title || "新对话"}</span>
              {isStreaming && (
                <span className="text-xs text-indigo-500 animate-pulse shrink-0">思考中</span>
              )}
            </div>
            <div className="flex items-center gap-1 shrink-0">
              <button
                type="button"
                onClick={() => setShowSessionList(!showSessionList)}
                className={cn(
                  "h-6 w-6 inline-flex items-center justify-center rounded-md transition-colors",
                  showSessionList
                    ? "text-indigo-500 bg-indigo-50 dark:bg-indigo-950/30"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                )}
                aria-label="对话历史"
              >
                <History className="h-3.5 w-3.5" />
              </button>
              {hasMessages && !showSessionList && (
                <button
                  type="button"
                  onClick={handleReset}
                  className="h-6 w-6 inline-flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                  aria-label="重置对话"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                </button>
              )}
              <Popover open={feedbackOpen} onOpenChange={setFeedbackOpen}>
                <PopoverTrigger asChild>
                  <button
                    type="button"
                    className="h-6 w-6 inline-flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                    aria-label="反馈"
                  >
                    <MessageSquare className="h-3.5 w-3.5" />
                  </button>
                </PopoverTrigger>
                <PopoverContent
                  side="bottom"
                  align="end"
                  data-chat-boundary
                  className="w-auto p-0 rounded-2xl border border-border bg-background/95 shadow-xl backdrop-blur"
                >
                  <FeedbackPanel isOpen={feedbackOpen} />
                </PopoverContent>
              </Popover>
              <button
                type="button"
                onClick={handleClosePanel}
                className="h-6 w-6 inline-flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                aria-label="关闭聊天面板"
                data-testid="chat-close-btn"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          {/* 会话列表视图 */}
          {showSessionList && (
            <div className="flex-1 min-h-0 overflow-hidden">
              <SessionList
                compact
                showTitle={false}
                maxHeight="100%"
                onSwitchSession={handleSwitchSession}
              />
            </div>
          )}

          {/* 聊天视图 */}
          {!showSessionList && (
            <>
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
            </>
          )}
        </div>
      )}
    </>
  );
}
