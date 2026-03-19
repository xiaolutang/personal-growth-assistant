import { useState, useRef, useEffect, useCallback } from "react";
import {
  Send,
  Loader2,
  Plus,
  MessageSquare,
  Trash2,
  ChevronDown,
  GripHorizontal,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useStreamParse } from "@/hooks/useStreamParse";
import { useTaskStore } from "@/stores/taskStore";
import { useChatStore } from "@/stores/chatStore";
import { SearchResultList } from "@/components/SearchResultCard";
import { KnowledgeGraphInline } from "@/components/KnowledgeGraph";
import { QuickCommandHints } from "@/components/QuickCommandHints";
import { getHelpMessage, type Intent } from "@/lib/intentDetection";
import { generateReviewReport, formatShortReview } from "@/lib/reviewFormatter";
import type { SearchResult } from "@/types/task";

// 最小和最大面板高度
const MIN_HEIGHT = 200;
const MAX_HEIGHT = 600;

// 多轮对话状态类型（可辨识联合）
type PendingAction =
  | { type: "delete"; items: SearchResult[] }
  | { type: "update"; items: SearchResult[]; field: string; value: string }
  | null;

// 辅助函数：构建更新数据
function buildUpdateData(
  field: string,
  value: string,
  existingTags?: string[]
): Record<string, unknown> {
  if (field === "tags") {
    return { tags: [...(existingTags || []), value] };
  }
  return { [field]: value };
}

// 辅助函数：更新会话标题（如果需要）
function updateTitleIfNeeded(
  session: { title: string } | null | undefined,
  updateFn: (title: string) => void,
  newTitle: string
) {
  if (session?.title === "新对话") {
    updateFn(newTitle.slice(0, 20));
  }
}

export function FloatingChat() {
  const [input, setInput] = useState("");
  const [showSessionList, setShowSessionList] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [currentIntent, setCurrentIntent] = useState<Intent | null>(null);
  const [isInputFocused, setIsInputFocused] = useState(false);
  const [pendingAction, setPendingAction] = useState<PendingAction>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const {
    sessions,
    currentSessionId,
    createSession,
    deleteSession,
    switchSession,
    addMessage,
    getCurrentSession,
    updateSessionTitle,
    panelHeight,
    setPanelHeight,
  } = useChatStore();

  const currentSession = getCurrentSession();
  const { addTasks, searchResults, knowledgeGraph, searchEntries, getKnowledgeGraph, clearSearchResults, clearKnowledgeGraph, updateEntry } =
    useTaskStore();

  const { result, isLoading, error, parse, reset } = useStreamParse({
    onComplete: (data) => {
      if (data.tasks.length > 0) {
        addTasks(
          data.tasks.map((task) => ({
            type: task.category,
            title: task.title || "",
            content: task.content || "",
            category: task.category,
            status: task.status,
            tags: task.tags || [],
          }))
        );
        updateTitleIfNeeded(currentSession, (t) => updateSessionTitle(currentSession!.id, t), data.tasks[0].title || "");
      }
    },
    onMessage: (role, content) => {
      if (currentSessionId) {
        addMessage(currentSessionId, { role, content });
      }
    },
  });

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [currentSession?.messages, searchResults, knowledgeGraph]);

  // 清理状态的辅助函数
  const clearState = useCallback(() => {
    reset();
    clearSearchResults();
    clearKnowledgeGraph();
    setCurrentIntent(null);
    setPendingAction(null);
  }, [reset, clearSearchResults, clearKnowledgeGraph]);

  // 处理待确认操作（多轮对话）
  const handlePendingAction = useCallback(async (userMessage: string): Promise<boolean> => {
    if (!pendingAction) return false;

    const activeSessionId = currentSessionId || createSession();
    addMessage(activeSessionId, { role: "user", content: userMessage });

    // 批量操作
    const batchKeywords = ["都", "全部", "所有", "两个", "三个", "这几个", "以上"];
    if (batchKeywords.some(k => userMessage.includes(k))) {
      const operations = pendingAction.items.map((item) => {
        if (pendingAction.type === "delete") {
          return useTaskStore.getState().deleteTask(item.id);
        }
        const updateData = buildUpdateData(pendingAction.field, pendingAction.value, item.tags);
        return updateEntry(item.id, updateData);
      });

      const results = await Promise.allSettled(operations);
      const successCount = results.filter(r => r.status === "fulfilled").length;
      const actionLabel = pendingAction.type === "delete" ? "删除" : "更新";
      addMessage(activeSessionId, { role: "assistant", content: `已${actionLabel} ${successCount} 个条目` });
      setPendingAction(null);
      return true;
    }

    // 数字选择
    const num = parseInt(userMessage);
    if (!isNaN(num) && num >= 1 && num <= pendingAction.items.length) {
      const selected = pendingAction.items[num - 1];
      if (pendingAction.type === "delete") {
        await useTaskStore.getState().deleteTask(selected.id);
        addMessage(activeSessionId, { role: "assistant", content: `已删除「${selected.title}」` });
      } else {
        const updateData = buildUpdateData(pendingAction.field, pendingAction.value, selected.tags);
        await updateEntry(selected.id, updateData);
        const fieldLabel = pendingAction.field === "status" ? "状态" : pendingAction.field === "tags" ? "标签" : "内容";
        addMessage(activeSessionId, { role: "assistant", content: `已更新「${selected.title}」的${fieldLabel}` });
      }
      setPendingAction(null);
      return true;
    }

    // 取消操作
    if (/取消|算了|不要了|不删|不更/.test(userMessage)) {
      addMessage(activeSessionId, { role: "assistant", content: "操作已取消" });
      setPendingAction(null);
      return true;
    }

    return false;
  }, [pendingAction, currentSessionId, createSession, addMessage, updateEntry]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading || isSubmitting) return;

    const userMessage = input.trim();
    setIsSubmitting(true);

    // 处理待确认的操作
    if (await handlePendingAction(userMessage)) {
      setInput("");
      setIsSubmitting(false);
      return;
    }

    // 统一调用后端接口
    const activeSessionId = currentSessionId || createSession();
    clearSearchResults();
    clearKnowledgeGraph();

    try {
      const response = await parse(userMessage, activeSessionId);
      const { intent, query, entities } = response.intent;
      setCurrentIntent(intent as Intent);

      switch (intent) {
        case "create":
          // 已由 parse() 内部处理
          break;

        case "read": {
          const results = await searchEntries(query || userMessage, 10);
          addMessage(activeSessionId, {
            role: "assistant",
            content: results.length > 0 ? `找到 ${results.length} 个相关结果` : "没有找到相关内容",
          });
          updateTitleIfNeeded(currentSession, (t) => updateSessionTitle(activeSessionId, t), `搜索: ${query || userMessage}`);
          break;
        }

        case "knowledge": {
          const graph = await getKnowledgeGraph(query || userMessage, 2);
          addMessage(activeSessionId, {
            role: "assistant",
            content: graph?.center ? `已加载 "${query}" 的知识图谱` : "没有找到相关知识图谱",
          });
          updateTitleIfNeeded(currentSession, (t) => updateSessionTitle(activeSessionId, t), `图谱: ${query || ""}`);
          break;
        }

        case "update": {
          const field = entities?.field as string;
          const value = entities?.value as string;
          const results = await searchEntries(query || userMessage, 10);

          if (results.length === 0) {
            addMessage(activeSessionId, { role: "assistant", content: `没找到"${query}"相关内容` });
          } else if (results.length === 1) {
            const entry = results[0];
            const updateData = buildUpdateData(field, value, entry.tags);
            await updateEntry(entry.id, updateData);
            const fieldLabel = field === "status" ? "状态" : field === "tags" ? "标签" : "内容";
            addMessage(activeSessionId, { role: "assistant", content: `已更新「${entry.title}」的${fieldLabel}` });
          } else {
            setPendingAction({ type: "update", items: results, field, value });
            addMessage(activeSessionId, {
              role: "assistant",
              content: `找到 ${results.length} 个匹配项，请选择：\n${results.map((r, i) => `${i + 1}. ${r.title}`).join("\n")}\n\n输入序号选择，或输入"全部"批量更新`,
            });
          }
          updateTitleIfNeeded(currentSession, (t) => updateSessionTitle(activeSessionId, t), `更新: ${query || ""}`);
          break;
        }

        case "delete": {
          const results = await searchEntries(query || userMessage, 10);

          if (results.length === 0) {
            addMessage(activeSessionId, { role: "assistant", content: `没找到"${query}"相关内容` });
          } else if (results.length === 1) {
            addMessage(activeSessionId, {
              role: "assistant",
              content: `确认删除「${results[0].title}」？`,
              actionConfirm: { type: "delete", entryId: results[0].id, title: results[0].title },
            });
          } else {
            setPendingAction({ type: "delete", items: results });
            addMessage(activeSessionId, {
              role: "assistant",
              content: `找到 ${results.length} 个匹配项，请选择：\n${results.map((r, i) => `${i + 1}. ${r.title}`).join("\n")}\n\n输入序号选择，或输入"都删除"批量删除`,
            });
          }
          updateTitleIfNeeded(currentSession, (t) => updateSessionTitle(activeSessionId, t), `删除: ${query || ""}`);
          break;
        }

        case "review": {
          const period = (entities?.period || "daily") as "daily" | "weekly" | "monthly";
          const entries = await searchEntries("", 50);
          const report = generateReviewReport(entries, period);
          addMessage(activeSessionId, { role: "assistant", content: formatShortReview(report) });
          const typeLabel = period === "daily" ? "日报" : period === "weekly" ? "周报" : "月报";
          updateTitleIfNeeded(currentSession, (t) => updateSessionTitle(activeSessionId, t), typeLabel);
          break;
        }

        case "help":
          addMessage(activeSessionId, { role: "assistant", content: getHelpMessage() });
          updateTitleIfNeeded(currentSession, (t) => updateSessionTitle(activeSessionId, t), "帮助");
          break;

        default:
          // fallback 到 create
          break;
      }
    } catch (err) {
      console.error("Parse error:", err);
    }

    setInput("");
    setIsSubmitting(false);
  };

  const handleNewSession = () => {
    createSession();
    clearState();
  };

  const handleSwitchSession = (id: string) => {
    switchSession(id);
    clearState();
    setShowSessionList(false);
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

      {/* 会话列表区域 */}
      <div className="border-b bg-muted/30 shrink-0">
        <div
          className="flex items-center justify-between p-2 cursor-pointer hover:bg-muted/50"
          onClick={() => setShowSessionList(!showSessionList)}
        >
          <div className="flex items-center gap-2">
            {showSessionList ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            <MessageSquare className="h-4 w-4" />
            <span className="text-sm font-medium truncate">{currentSession?.title || "新对话"}</span>
          </div>
          <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); handleNewSession(); }}>
            <Plus className="h-4 w-4" />
          </Button>
        </div>

        {showSessionList && (
          <div className="max-h-32 overflow-y-auto border-t">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`flex items-center justify-between px-4 py-1.5 cursor-pointer hover:bg-muted ${
                  session.id === currentSessionId ? "bg-muted" : ""
                }`}
                onClick={() => handleSwitchSession(session.id)}
              >
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <MessageSquare className="h-3 w-3 shrink-0 text-muted-foreground" />
                  <span className="truncate text-sm">{session.title}</span>
                </div>
                <Button variant="ghost" size="icon" className="h-5 w-5 shrink-0" onClick={(e) => { e.stopPropagation(); deleteSession(session.id); }}>
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            ))}
            {sessions.length === 0 && <p className="text-sm text-muted-foreground text-center py-2">暂无对话</p>}
          </div>
        )}
      </div>

      {/* 历史消息区域 */}
      {currentSession && currentSession.messages.length > 0 && (
        <div ref={messagesContainerRef} className="flex-1 overflow-y-auto p-3 border-b bg-muted/20 min-h-0">
          {currentSession.messages.map((msg) => (
            <div key={msg.id} className={`mb-2 ${msg.role === "user" ? "text-right" : "text-left"}`}>
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

      {/* 输入区域 */}
      <div className="shrink-0">
        <QuickCommandHints
          isVisible={isInputFocused && !input.trim()}
          onSelectCommand={(example) => setInput(example)}
        />

        <div className="p-3">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onFocus={() => setIsInputFocused(true)}
              onBlur={() => setIsInputFocused(false)}
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
