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
import { useTaskStore } from "@/stores/taskStore";
import { useChatStore } from "@/stores/chatStore";
import { SearchResultList } from "@/components/SearchResultCard";
import { KnowledgeGraphInline } from "@/components/KnowledgeGraph";
import { QuickCommandHints } from "@/components/QuickCommandHints";
import { getHelpMessage, type Intent } from "@/lib/intentDetection";
import { generateReviewReport, formatShortReview } from "@/lib/reviewFormatter";

// 最小和最大面板高度
const MIN_HEIGHT = 200;
const MAX_HEIGHT = 600;

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
  const [isDragging, setIsDragging] = useState(false);
  const [currentIntent, setCurrentIntent] = useState<Intent | null>(null);
  const [isInputFocused, setIsInputFocused] = useState(false);
  const [confirmData, setConfirmData] = useState<ConfirmData | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const {
    currentSessionId,
    createSession,
    addMessage,
    getCurrentSession,
    updateSessionTitle,
    panelHeight,
    setPanelHeight,
  } = useChatStore();

  const currentSession = getCurrentSession();
  const { searchResults, knowledgeGraph, searchEntries, getKnowledgeGraph, clearSearchResults, clearKnowledgeGraph, fetchEntries } =
    useTaskStore();

  const { result, isLoading, error, parse } = useStreamParse({
    onMessage: (role, content) => {
      if (currentSessionId) {
        addMessage(currentSessionId, { role, content });
      }
    },
    onCreated: (_ids, count) => {
      // 刷新列表
      fetchEntries();
      if (currentSessionId) {
        updateTitleIfNeeded(
          currentSession,
          (t) => updateSessionTitle(currentSessionId, t),
          `创建 ${count} 个条目`
        );
      }
    },
    onUpdated: () => {
      fetchEntries();
    },
    onDeleted: () => {
      fetchEntries();
    },
    onConfirm: (data) => {
      setConfirmData(data);
      if (currentSessionId) {
        const itemList = data.items.map((item, i) => `${i + 1}. ${item.title}`).join("\n");
        const actionLabel = data.action === "delete" ? "删除" : "更新";
        addMessage(currentSessionId, {
          role: "assistant",
          content: `找到 ${data.items.length} 个匹配项，请选择：\n${itemList}\n\n输入序号选择，或输入"全部${actionLabel}"批量操作`,
        });
      }
    },
    onResults: (items) => {
      // 将结果同步到 taskStore
      clearSearchResults();
      const searchItems: Array<{
        id: string;
        title: string;
        status?: string;
        category?: string;
      }> = items.map((item) => ({
        id: item.id,
        title: item.title,
        status: item.status,
        category: item.category,
      }));
      useTaskStore.setState({ searchResults: searchItems as typeof searchResults });
      setCurrentIntent("read");
    },
  });

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [currentSession?.messages, searchResults, knowledgeGraph]);

  // 处理确认操作（多选场景）
  const handleConfirm = useCallback(
    async (userMessage: string): Promise<boolean> => {
      if (!confirmData) return false;

      const activeSessionId = currentSessionId || createSession();

      // 批量操作
      const batchKeywords = ["都", "全部", "所有", "两个", "三个", "这几个", "以上"];
      if (batchKeywords.some((k) => userMessage.includes(k))) {
        // 批量操作：依次发送确认请求
        const results = [];
        for (const item of confirmData.items) {
          try {
            await parse(
              `${confirmData.action === "delete" ? "删除" : "更新"} ${item.title}`,
              activeSessionId,
              { action: confirmData.action, item_id: item.id }
            );
            results.push({ success: true });
          } catch {
            results.push({ success: false });
          }
        }
        const successCount = results.filter((r) => r.success).length;
        const actionLabel = confirmData.action === "delete" ? "删除" : "更新";
        addMessage(activeSessionId, {
          role: "assistant",
          content: `已${actionLabel} ${successCount} 个条目`,
        });
        setConfirmData(null);
        return true;
      }

      // 数字选择
      const num = parseInt(userMessage);
      if (!isNaN(num) && num >= 1 && num <= confirmData.items.length) {
        const selected = confirmData.items[num - 1];
        try {
          await parse(
            `${confirmData.action === "delete" ? "删除" : "更新"} ${selected.title}`,
            activeSessionId,
            { action: confirmData.action, item_id: selected.id }
          );
        } catch {
          addMessage(activeSessionId, {
            role: "assistant",
            content: "操作失败",
          });
        }
        setConfirmData(null);
        return true;
      }

      // 取消操作
      if (/取消|算了|不要了|不删|不更/.test(userMessage)) {
        addMessage(activeSessionId, { role: "assistant", content: "操作已取消" });
        setConfirmData(null);
        return true;
      }

      return false;
    },
    [confirmData, currentSessionId, createSession, addMessage, parse]
  );

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
      updateTitleIfNeeded(currentSession, (t) => updateSessionTitle(activeSessionId, t), userMessage.slice(0, 20));

      // 对于需要前端额外处理的意图
      if (response.operation?.confirm) {
        // confirm 已在 onConfirm 回调中处理
      } else if (intent === "review") {
        // review 需要前端处理（本地生成报告）
        const period = (entities?.period || "daily") as "daily" | "weekly" | "monthly";
        const entries = await searchEntries("", 50);
        const report = generateReviewReport(entries, period);
        addMessage(activeSessionId, { role: "assistant", content: formatShortReview(report) });
        const typeLabel = period === "daily" ? "日报" : period === "weekly" ? "周报" : "月报";
        updateTitleIfNeeded(currentSession, (t) => updateSessionTitle(activeSessionId, t), typeLabel);
      } else if (intent === "knowledge") {
        // knowledge 需要前端处理（调用知识图谱 API）
        const graph = await getKnowledgeGraph(query || userMessage, 2);
        addMessage(activeSessionId, {
          role: "assistant",
          content: graph?.center ? `已加载 "${query}" 的知识图谱` : "没有找到相关知识图谱",
        });
        updateTitleIfNeeded(currentSession, (t) => updateSessionTitle(activeSessionId, t), `图谱: ${query || ""}`);
      } else if (intent === "help") {
        addMessage(activeSessionId, { role: "assistant", content: getHelpMessage() });
        updateTitleIfNeeded(currentSession, (t) => updateSessionTitle(activeSessionId, t), "帮助");
      }
      // create/update/delete/read 意图由后端处理完成，无需额外操作
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
