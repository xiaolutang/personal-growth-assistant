import { useState, useRef, useEffect, useCallback } from "react";
import {
  Send,
  Loader2,
  MessageSquare,
  GripHorizontal,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  useStreamParse,
  type ConfirmData,
} from "@/hooks/useStreamParse";
import { useConfirmHandler } from "@/hooks/useConfirmHandler";
import { useIntentDispatcher } from "@/hooks/useIntentDispatcher";
import { useChatActions } from "@/hooks/useChatActions";
import { useTaskStore } from "@/stores/taskStore";
import { useChatStore } from "@/stores/chatStore";
import { SearchResultList } from "@/components/SearchResultCard";
import { KnowledgeGraphInline } from "@/components/KnowledgeGraph";
import type { Intent } from "@/lib/intentDetection";
import { OperationStatusBar } from "@/components/OperationStatusBar";
import { ActionIndicator } from "@/components/ActionIndicator";

// 最小和最大面板高度
const MIN_HEIGHT = 200;
const MAX_HEIGHT = 600;

export function FloatingChat() {
  const [input, setInput] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [currentIntent, setCurrentIntent] = useState<Intent | null>(null);
  const [confirmData, setConfirmData] = useState<ConfirmData | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentAction, setCurrentAction] = useState<{
    type: Intent | "tool" | "skill";
    name?: string;
    status: "pending" | "running" | "success" | "error";
  } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  // Chat store
  const {
    currentSessionId,
    createSession,
    addMessage,
    getCurrentSession,
    updateSessionTitle,
    panelHeight,
    setPanelHeight,
    lastOperation,
    clearLastOperation,
    fetchSessions,
    fetchSessionMessages,
  } = useChatStore();

  const currentSession = getCurrentSession();

  // 初始化时加载会话列表
  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  // 切换会话时加载消息历史
  useEffect(() => {
    if (currentSessionId) {
      fetchSessionMessages(currentSessionId);
    }
  }, [currentSessionId, fetchSessionMessages]);

  // Task store
  const {
    searchResults,
    knowledgeGraph,
    searchEntries,
    getKnowledgeGraph,
    clearSearchResults,
    clearKnowledgeGraph,
    fetchEntries,
  } = useTaskStore();

  // Chat actions hook
  const {
    onIntentDetected,
    onCreated,
    onUpdated,
    onDeleted,
    onConfirm,
    onResults,
    updateTitleIfNeeded,
  } = useChatActions({
    currentSessionId,
    currentSession,
    addMessage,
    updateSessionTitle,
    fetchEntries,
    setSearchResults: (results) => useTaskStore.setState({ searchResults: results as typeof searchResults }),
    clearSearchResults,
    setCurrentAction,
    setLastOperation: (op) => {
      if (op) {
        useChatStore.getState().setLastOperation({
          type: op.type as any,
          status: op.status as any,
          message: op.message,
          timestamp: op.timestamp,
        });
      } else {
        useChatStore.getState().clearLastOperation();
      }
    },
    setConfirmData,
    setCurrentIntent,
  });

  // Stream parse hook
  const { result, isLoading, error, parse } = useStreamParse({
    onMessage: (role, content) => {
      if (currentSessionId) {
        addMessage(currentSessionId, { role, content });
      }
    },
    onIntentDetected,
    onCreated,
    onUpdated,
    onDeleted,
    onConfirm,
    onResults,
  });

  // Confirm handler hook
  const { handleConfirm } = useConfirmHandler(confirmData, {
    currentSessionId,
    createSession,
    addMessage,
    parse,
  });

  // Intent dispatcher hook
  const { dispatchIntent } = useIntentDispatcher({
    currentSessionId,
    currentSession,
    createSession,
    addMessage,
    updateSessionTitle,
    searchEntries,
    getKnowledgeGraph,
    setKnowledgeGraph: (graph) => useTaskStore.setState({ knowledgeGraph: graph as typeof knowledgeGraph }),
    setCurrentIntent,
  });

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [currentSession?.messages, searchResults, knowledgeGraph]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading || isSubmitting) return;

    const userMessage = input.trim();
    setIsSubmitting(true);

    // 处理确认操作
    if (await handleConfirm(userMessage)) {
      setInput("");
      setIsSubmitting(false);
      return;
    }

    const activeSessionId = currentSessionId || createSession();
    clearSearchResults();
    clearKnowledgeGraph();

    try {
      const response = await parse(userMessage, activeSessionId);
      const intent = response.intent.intent as Intent;
      setCurrentIntent(intent);
      const { query, entities } = response.intent;

      // 更新会话标题
      updateTitleIfNeeded(userMessage.slice(0, 20));

      // 对于需要前端额外处理的意图
      if (!response.operation?.confirm) {
        const handled = await dispatchIntent(intent, query || "", entities, userMessage);
        // 如果 dispatchIntent 返回 false，说明意图由后端处理完成
        if (!handled) {
          // create/update/delete/read 意图由后端处理完成
        }
      }
    } catch (err) {
      console.error("Parse error:", err);
    }

    setInput("");
    setIsSubmitting(false);
  };

  // 拖拽调整高度
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const newHeight = window.innerHeight - e.clientY;
      setPanelHeight(Math.min(MAX_HEIGHT, Math.max(MIN_HEIGHT, newHeight)));
    };

    const handleMouseUp = () => setIsDragging(false);

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging, setPanelHeight]);

  return (
    <div
      className={`fixed bottom-0 left-64 right-0 bg-background border-t z-50 flex flex-col ${
        isDragging ? "select-none" : ""
      }`}
      style={{ height: panelHeight }}
    >
      {/* 拖拽条 */}
      <div
        className="flex items-center justify-center h-6 cursor-ns-resize hover:bg-muted/50 border-b shrink-0"
        onMouseDown={handleMouseDown}
      >
        <GripHorizontal className="h-4 w-4 text-muted-foreground" />
      </div>

      {/* 当前会话信息 */}
      <div className="flex items-center gap-2 px-3 py-2 border-b bg-muted/30 shrink-0">
        <MessageSquare className="h-4 w-4 shrink-0" />
        <span className="text-sm font-medium truncate">{currentSession?.title || "新对话"}</span>
      </div>

      {/* 历史消息区域 */}
      {currentSession && currentSession.messages.length > 0 && (
        <div ref={messagesContainerRef} className="flex-1 overflow-y-auto p-3 border-b bg-muted/20 min-h-0">
          {/* 当前操作指示器 */}
          {currentAction && currentAction.status === "running" && (
            <div className="mb-2">
              <ActionIndicator
                type={currentAction.type === "tool" || currentAction.type === "skill" ? currentAction.type : "intent"}
                name={currentAction.name || (currentAction.type !== "tool" && currentAction.type !== "skill" ? currentAction.type : "")}
                status={currentAction.status}
              />
            </div>
          )}

          {currentSession.messages.map((msg) => (
            <div key={msg.id} className={`mb-2 ${msg.role === "user" ? "text-right" : "text-left"}`}>
              {/* AI 消息时显示操作类型标签 */}
              {msg.role === "assistant" && msg.metadata?.intent && (
                <div className="mb-1">
                  <ActionIndicator
                    type="intent"
                    name={msg.metadata.intent}
                    status="success"
                    compact
                  />
                </div>
              )}
              <span className={`inline-block px-3 py-1.5 rounded-lg text-sm max-w-[80%] whitespace-pre-wrap break-words ${
                msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
              }`}>
                {msg.content}
              </span>
            </div>
          ))}

          {currentIntent === "read" && searchResults.length > 0 && (
            <div className="mb-2"><SearchResultList results={searchResults} /></div>
          )}

          {currentIntent === "knowledge" && knowledgeGraph && (
            <div className="mb-2"><KnowledgeGraphInline data={knowledgeGraph} /></div>
          )}

          <div ref={messagesEndRef} />
        </div>
      )}

      {/* 输入区域 - 固定在底部 */}
      <div className="shrink-0 mt-auto">
        {/* 操作状态提示条 */}
        <OperationStatusBar
          operation={lastOperation}
          onDismiss={clearLastOperation}
        />

        <div className="p-3">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="输入内容、帮我搜索、把...改为...、或输入帮助..."
              className="flex-1"
              disabled={isLoading || isSubmitting}
            />
            <Button type="submit" disabled={!input.trim() || isLoading || isSubmitting}>
              {(isLoading || isSubmitting) ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </form>

          {error && <p className="text-sm text-destructive mt-2">{error.message}</p>}
          {result && result.tasks.length > 0 && (
            <div className="mt-2 text-sm text-muted-foreground">已识别 {result.tasks.length} 个任务</div>
          )}
        </div>
      </div>
    </div>
  );
}
