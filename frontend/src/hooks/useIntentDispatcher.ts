import { useCallback } from "react";
import type { Intent } from "@/lib/intentDetection";
import { getHelpMessage } from "@/lib/intentDetection";
import { generateReviewReport, formatShortReview } from "@/lib/reviewFormatter";
import type { SearchResult, KnowledgeGraphResponse } from "@/types/task";
import { DEFAULT_SESSION_TITLE, MAX_TITLE_LENGTH } from "@/lib/sessionUtils";

interface UseIntentDispatcherOptions {
  currentSessionId: string | null;
  currentSession: { title: string } | null | undefined;
  createSession: () => string;
  addMessage: (sessionId: string, message: { role: "user" | "assistant"; content: string }) => void;
  updateSessionTitle: (sessionId: string, title: string) => void;
  searchEntries: (query: string, limit: number) => Promise<SearchResult[]>;
  getKnowledgeGraph: (concept: string, depth: number) => Promise<KnowledgeGraphResponse | null>;
  setKnowledgeGraph: (graph: unknown) => void;
  setCurrentIntent: (intent: Intent | null) => void;
}

/**
 * 处理意图分发的 Hook
 *
 * 处理需要前端额外处理的意图：
 * - review: 本地生成报告
 * - knowledge: 调用知识图谱 API
 * - help: 显示帮助信息
 */
export function useIntentDispatcher(options: UseIntentDispatcherOptions) {
  const {
    currentSessionId,
    currentSession,
    createSession,
    addMessage,
    updateSessionTitle,
    searchEntries,
    getKnowledgeGraph,
    setKnowledgeGraph,
    setCurrentIntent,
  } = options;

  // 辅助函数：更新会话标题（如果需要）
  const updateTitleIfNeeded = useCallback(
    (newTitle: string) => {
      const activeSessionId = currentSessionId || createSession();
      if (currentSession?.title === DEFAULT_SESSION_TITLE) {
        updateSessionTitle(activeSessionId, newTitle.slice(0, MAX_TITLE_LENGTH));
      }
    },
    [currentSessionId, currentSession, createSession, updateSessionTitle]
  );

  const dispatchIntent = useCallback(
    async (
      intent: Intent,
      query: string,
      entities: Record<string, string> | undefined,
      userMessage: string
    ): Promise<boolean> => {
      const activeSessionId = currentSessionId || createSession();

      if (intent === "review") {
        // review 需要前端处理（本地生成报告）
        const period = (entities?.period || "daily") as "daily" | "weekly" | "monthly";
        const entries = await searchEntries("", 50);
        const report = generateReviewReport(entries as any, period);
        addMessage(activeSessionId, { role: "assistant", content: formatShortReview(report) });
        const typeLabel = period === "daily" ? "日报" : period === "weekly" ? "周报" : "月报";
        updateTitleIfNeeded(typeLabel);
        setCurrentIntent("review");
        return true;
      }

      if (intent === "knowledge") {
        // knowledge 需要前端处理（调用知识图谱 API）
        const graph = await getKnowledgeGraph(query || userMessage, 2);
        const hasCenter = graph?.center?.name;
        addMessage(activeSessionId, {
          role: "assistant",
          content: hasCenter ? `已加载 "${query}" 的知识图谱` : "没有找到相关知识图谱",
        });
        updateTitleIfNeeded(`图谱: ${query || ""}`);
        if (graph) {
          setKnowledgeGraph(graph);
        }
        setCurrentIntent("knowledge");
        return true;
      }

      if (intent === "help") {
        addMessage(activeSessionId, { role: "assistant", content: getHelpMessage() });
        updateTitleIfNeeded("帮助");
        return true;
      }

      // 其他意图由后端处理
      return false;
    },
    [
      currentSessionId,
      createSession,
      addMessage,
      searchEntries,
      getKnowledgeGraph,
      setKnowledgeGraph,
      setCurrentIntent,
      updateTitleIfNeeded,
    ]
  );

  return { dispatchIntent, updateTitleIfNeeded };
}
