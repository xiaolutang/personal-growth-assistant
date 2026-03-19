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
import { Badge } from "@/components/ui/badge";
import { useStreamParse } from "@/hooks/useStreamParse";
import { useTaskStore } from "@/stores/taskStore";
import { useChatStore } from "@/stores/chatStore";
import { SearchResultList } from "@/components/SearchResultCard";
import { KnowledgeGraphInline } from "@/components/KnowledgeGraph";
import { QuickCommandHints } from "@/components/QuickCommandHints";
import {
  extractSearchQuery,
  extractConcept,
  extractUpdateTarget,
  extractDeleteTarget,
  extractReviewParams,
  getHelpMessage,
  intentConfig,
  intentIcons,
  detectIntent as detectIntentLocal,
  type Intent,
} from "@/lib/intentDetection";
import { detectIntent as detectIntentApi } from "@/services/api";
import { generateReviewReport, formatShortReview } from "@/lib/reviewFormatter";
import type { SearchResult } from "@/types/task";

// 最小和最大面板高度
const MIN_HEIGHT = 200;
const MAX_HEIGHT = 600;

// 多轮对话状态类型
type PendingAction = {
  type: "delete" | "update";
  items: SearchResult[];
  field?: string;
  value?: string;
} | null;

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
        // 调用后端 API 创建条目
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
        // 更新会话标题（使用第一个任务名称）
        if (currentSession && currentSession.title === "新对话") {
          updateSessionTitle(
            currentSession.id,
            (data.tasks[0].title || "").slice(0, 20)
          );
        }
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading || isSubmitting) return;

    const userMessage = input.trim();
    setIsSubmitting(true);

    // 处理待确认的操作（多轮对话）
    if (pendingAction) {
      const batchKeywords = ["都", "全部", "所有", "两个", "三个", "这几个", "以上"];
      const isBatchAction = batchKeywords.some(k => userMessage.includes(k));

      if (isBatchAction) {
        // 执行批量操作
        const activeSessionId = currentSessionId || createSession();
        addMessage(activeSessionId, { role: "user", content: userMessage });

        let successCount = 0;
        for (const item of pendingAction.items) {
          try {
            if (pendingAction.type === "delete") {
              await useTaskStore.getState().deleteTask(item.id);
              successCount++;
            } else if (pendingAction.type === "update" && pendingAction.field) {
              const updateData = buildUpdateData(
                pendingAction.field,
                pendingAction.value!,
                item.tags
              );
              await updateEntry(item.id, updateData);
              successCount++;
            }
          } catch {
            // 忽略单个失败
          }
        }

        const actionLabel = pendingAction.type === "delete" ? "删除" : "更新";
        addMessage(activeSessionId, {
          role: "assistant",
          content: `已${actionLabel} ${successCount} 个条目`,
        });
        setPendingAction(null);
        setInput("");
        setIsSubmitting(false);
        return;
      }

      // 数字选择
      const num = parseInt(userMessage);
      if (!isNaN(num) && num >= 1 && num <= pendingAction.items.length) {
        const activeSessionId = currentSessionId || createSession();
        addMessage(activeSessionId, { role: "user", content: userMessage });

        const selected = pendingAction.items[num - 1];
        if (pendingAction.type === "delete") {
          await useTaskStore.getState().deleteTask(selected.id);
          addMessage(activeSessionId, { role: "assistant", content: `已删除「${selected.title}」` });
        } else if (pendingAction.type === "update" && pendingAction.field) {
          const updateData = buildUpdateData(
            pendingAction.field,
            pendingAction.value!,
            selected.tags
          );
          await updateEntry(selected.id, updateData);
          addMessage(activeSessionId, {
            role: "assistant",
            content: `已更新「${selected.title}」的${pendingAction.field === "status" ? "状态" : pendingAction.field === "tags" ? "标签" : "内容"}`,
          });
        }
        setPendingAction(null);
        setInput("");
        setIsSubmitting(false);
        return;
      }

      // 取消操作
      if (/取消|算了|不要了|不删|不更/.test(userMessage)) {
        const activeSessionId = currentSessionId || createSession();
        addMessage(activeSessionId, { role: "user", content: userMessage });
        addMessage(activeSessionId, { role: "assistant", content: "操作已取消" });
        setPendingAction(null);
        setInput("");
        setIsSubmitting(false);
        return;
      }
    }

    // 检测意图（优先使用后端 LLM，失败时回退到本地）
    let intent: Intent;

    try {
      const intentResult = await detectIntentApi(userMessage);
      intent = intentResult.intent as Intent;
      setCurrentIntent(intent);
    } catch (error) {
      console.warn("后端意图识别失败，使用本地检测:", error);
      intent = detectIntentLocal(userMessage);
      setCurrentIntent(intent);
    }

    // 确保有会话 ID
    const activeSessionId = currentSessionId || createSession();

    // 根据意图执行不同操作
    switch (intent) {
      case "read": {
        addMessage(activeSessionId, { role: "user", content: userMessage });
        const query = extractSearchQuery(userMessage);
        clearKnowledgeGraph();
        const results = await searchEntries(query);
        addMessage(activeSessionId, {
          role: "assistant",
          content: results.length > 0 ? `找到 ${results.length} 个相关结果` : "没有找到相关内容",
        });
        if (currentSession?.title === "新对话") {
          updateSessionTitle(activeSessionId, `搜索: ${query.slice(0, 15)}`);
        }
        break;
      }

      case "knowledge": {
        addMessage(activeSessionId, { role: "user", content: userMessage });
        const concept = extractConcept(userMessage);
        clearSearchResults();
        const graph = await getKnowledgeGraph(concept);
        addMessage(activeSessionId, {
          role: "assistant",
          content: graph?.center ? `已加载 "${concept}" 的知识图谱` : "没有找到相关知识图谱",
        });
        if (currentSession?.title === "新对话") {
          updateSessionTitle(activeSessionId, `图谱: ${concept.slice(0, 15)}`);
        }
        break;
      }

      case "update": {
        addMessage(activeSessionId, { role: "user", content: userMessage });
        const target = extractUpdateTarget(userMessage);
        clearKnowledgeGraph();
        const results = await searchEntries(target.query);

        if (results.length === 0) {
          addMessage(activeSessionId, { role: "assistant", content: `没找到"${target.query}"相关内容` });
        } else if (results.length === 1) {
          // 唯一匹配，直接更新
          const entry = results[0];
          const updateData: Record<string, unknown> = {};
          if (target.field === "tags") {
            updateData.tags = [...(entry.tags || []), target.value];
          } else if (target.field) {
            updateData[target.field] = target.value;
          }
          await updateEntry(entry.id, updateData);
          addMessage(activeSessionId, {
            role: "assistant",
            content: `已更新「${entry.title}」的${target.field === "status" ? "状态" : target.field === "tags" ? "标签" : "内容"}`,
          });
        } else {
          // 多个匹配，设置 pendingAction 并显示选择列表
          setPendingAction({ type: "update", items: results, field: target.field, value: target.value });
          addMessage(activeSessionId, {
            role: "assistant",
            content: `找到 ${results.length} 个匹配项，请选择：\n${results.map((r, i) => `${i + 1}. ${r.title}`).join("\n")}\n\n输入序号选择，或输入"全部"批量更新`,
          });
        }
        if (currentSession?.title === "新对话") {
          updateSessionTitle(activeSessionId, `更新: ${target.query.slice(0, 15)}`);
        }
        break;
      }

      case "delete": {
        addMessage(activeSessionId, { role: "user", content: userMessage });
        const target = extractDeleteTarget(userMessage);
        clearKnowledgeGraph();
        const results = await searchEntries(target.query);

        if (results.length === 0) {
          addMessage(activeSessionId, { role: "assistant", content: `没找到"${target.query}"相关内容` });
        } else if (results.length === 1) {
          // 唯一匹配，确认后删除
          addMessage(activeSessionId, {
            role: "assistant",
            content: `确认删除「${results[0].title}」？`,
            actionConfirm: { type: "delete", entryId: results[0].id, title: results[0].title },
          });
        } else {
          // 多个匹配，设置 pendingAction 并显示选择列表
          setPendingAction({ type: "delete", items: results });
          addMessage(activeSessionId, {
            role: "assistant",
            content: `找到 ${results.length} 个匹配项，请选择：\n${results.map((r, i) => `${i + 1}. ${r.title}`).join("\n")}\n\n输入序号选择，或输入"都删除"批量删除`,
          });
        }
        if (currentSession?.title === "新对话") {
          updateSessionTitle(activeSessionId, `删除: ${target.query.slice(0, 15)}`);
        }
        break;
      }

      case "review": {
        addMessage(activeSessionId, { role: "user", content: userMessage });
        const params = extractReviewParams(userMessage);
        clearSearchResults();
        clearKnowledgeGraph();

        // 获取数据并生成报告
        const entries = await searchEntries("", 50);
        const report = generateReviewReport(entries, params.type);
        const reviewContent = formatShortReview(report);

        addMessage(activeSessionId, { role: "assistant", content: reviewContent });
        if (currentSession?.title === "新对话") {
          const typeLabel = params.type === "daily" ? "日报" : params.type === "weekly" ? "周报" : "月报";
          updateSessionTitle(activeSessionId, typeLabel);
        }
        break;
      }

      case "help": {
        addMessage(activeSessionId, { role: "user", content: userMessage });
        addMessage(activeSessionId, { role: "assistant", content: getHelpMessage() });
        if (currentSession?.title === "新对话") {
          updateSessionTitle(activeSessionId, "帮助");
        }
        break;
      }

      default: {
        // create 意图
        clearSearchResults();
        clearKnowledgeGraph();
        await parse(userMessage, activeSessionId);
        // parse 是流式的，isLoading 由 useStreamParse 管理，这里不需要重置 isSubmitting
        setInput("");
        return; // 提前返回，不重置 isSubmitting（由 useStreamParse 管理）
      }
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

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging, setPanelHeight]);

  // 渲染意图提示
  const renderIntentBadge = () => {
    if (!currentIntent) return null;
    const config = intentConfig[currentIntent];
    const Icon = intentIcons[currentIntent];
    return (
      <Badge
        variant="secondary"
        className={`absolute right-2 top-1/2 -translate-y-1/2 text-xs ${config.color}`}
      >
        <Icon className="h-3 w-3 mr-1" />
        {config.label}
      </Badge>
    );
  };

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

      {/* 会话列表区域 - 可折叠 */}
      <div className="border-b bg-muted/30 shrink-0">
        <div
          className="flex items-center justify-between p-2 cursor-pointer hover:bg-muted/50"
          onClick={() => setShowSessionList(!showSessionList)}
        >
          <div className="flex items-center gap-2">
            {showSessionList ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            <MessageSquare className="h-4 w-4" />
            <span className="text-sm font-medium truncate">
              {currentSession?.title || "新对话"}
            </span>
          </div>
          <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); handleNewSession(); }}>
            <Plus className="h-4 w-4" />
          </Button>
        </div>

        {/* 展开的会话列表 */}
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
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-5 w-5 shrink-0"
                  onClick={(e) => { e.stopPropagation(); deleteSession(session.id); }}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            ))}
            {sessions.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-2">暂无对话</p>
            )}
          </div>
        )}
      </div>

      {/* 历史消息区域 */}
      {currentSession && currentSession.messages.length > 0 && (
        <div
          ref={messagesContainerRef}
          className="flex-1 overflow-y-auto p-3 border-b bg-muted/20 min-h-0"
        >
          {currentSession.messages.map((msg) => (
            <div
              key={msg.id}
              className={`mb-2 ${msg.role === "user" ? "text-right" : "text-left"}`}
            >
              <span
                className={`inline-block px-3 py-1.5 rounded-lg text-sm max-w-[80%] whitespace-pre-wrap break-words ${
                  msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
                }`}
              >
                {msg.content}
              </span>
            </div>
          ))}

          {/* 搜索结果展示 */}
          {currentIntent === "read" && searchResults.length > 0 && (
            <div className="mb-2">
              <SearchResultList results={searchResults} />
            </div>
          )}

          {/* 知识图谱展示 */}
          {currentIntent === "knowledge" && knowledgeGraph && (
            <div className="mb-2">
              <KnowledgeGraphInline data={knowledgeGraph} />
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      )}

      {/* 输入区域 */}
      <div className="shrink-0">
        {/* 快捷命令提示 */}
        <QuickCommandHints
          isVisible={isInputFocused && !input.trim()}
          onSelectCommand={(example) => {
            setInput(example);
            setCurrentIntent(detectIntentLocal(example));
          }}
        />

        <div className="p-3">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <div className="relative flex-1">
              <Input
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  setCurrentIntent(e.target.value.trim() ? detectIntentLocal(e.target.value.trim()) : null);
                }}
                onFocus={() => setIsInputFocused(true)}
                onBlur={() => setIsInputFocused(false)}
                placeholder="输入内容、帮我搜索、把...改为...、或输入帮助..."
                className="flex-1 pr-20"
                disabled={isLoading || isSubmitting}
              />
              {renderIntentBadge()}
            </div>
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
