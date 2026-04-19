import { useCallback } from "react";
import type { Intent } from "@/lib/intentDetection";
import type { IntentResult, ConfirmData, ResultItem } from "./useStreamParse";
import { DEFAULT_SESSION_TITLE, MAX_TITLE_LENGTH } from "@/lib/sessionUtils";

/** PWA 安装使用计数 — 直接操作 localStorage 避免循环依赖 */
function incrementPWAUsage() {
  try {
    const key = "pwa-usage-count";
    const next = (Number(localStorage.getItem(key)) || 0) + 1;
    localStorage.setItem(key, String(next));
    window.dispatchEvent(new CustomEvent("pwa-usage-updated"));
  } catch {}
}

interface OperationStatus {
  type: Intent | "tool" | "skill";
  name?: string;
  status: "pending" | "running" | "success" | "error";
}

interface UseChatActionsOptions {
  currentSessionId: string | null;
  currentSession: { title: string } | null | undefined;
  addMessage: (sessionId: string, message: { role: "user" | "assistant"; content: string }) => void;
  updateSessionTitle: (sessionId: string, title: string) => void | Promise<void>;
  fetchEntries: () => void;
  setSearchResults: (results: unknown[]) => void;
  clearSearchResults: () => void;
  setCurrentAction: (action: OperationStatus | null | ((prev: OperationStatus | null) => OperationStatus | null)) => void;
  setLastOperation: (operation: { type: string; status: string; message: string; timestamp: number } | null) => void;
  setConfirmData: (data: ConfirmData | null) => void;
  setCurrentIntent: (intent: Intent | null) => void;
}

/**
 * 整合 SSE 回调逻辑的 Hook
 *
 * 提供统一的回调处理：
 * - onIntentDetected
 * - onCreated
 * - onUpdated
 * - onDeleted
 * - onConfirm
 * - onResults
 */
export function useChatActions(options: UseChatActionsOptions) {
  const {
    currentSessionId,
    currentSession,
    addMessage,
    updateSessionTitle,
    fetchEntries,
    setSearchResults,
    clearSearchResults,
    setCurrentAction,
    setLastOperation,
    setConfirmData,
    setCurrentIntent,
  } = options;

  // 辅助函数：更新会话标题（如果需要）
  const updateTitleIfNeeded = useCallback(
    (newTitle: string) => {
      if (currentSession?.title === DEFAULT_SESSION_TITLE && currentSessionId) {
        updateSessionTitle(currentSessionId, newTitle.slice(0, MAX_TITLE_LENGTH));
      }
    },
    [currentSessionId, currentSession, updateSessionTitle]
  );

  const onIntentDetected = useCallback(
    (intentResult: IntentResult) => {
      setCurrentAction({
        type: intentResult.intent as Intent,
        name: intentResult.intent,
        status: "running",
      });
    },
    [setCurrentAction]
  );

  const onCreated = useCallback(
    (_ids: string[], count: number) => {
      fetchEntries();
      updateTitleIfNeeded(`创建 ${count} 个条目`);
      setCurrentAction((prev) => (prev ? { ...prev, status: "success" } : null));
      setLastOperation({
        type: "create",
        status: "success",
        message: `已创建 ${count} 个条目`,
        timestamp: Date.now(),
      });
      incrementPWAUsage();
    },
    [fetchEntries, updateTitleIfNeeded, setCurrentAction, setLastOperation]
  );

  const onUpdated = useCallback(() => {
    fetchEntries();
    setCurrentAction((prev) => (prev ? { ...prev, status: "success" } : null));
  }, [fetchEntries, setCurrentAction]);

  const onDeleted = useCallback(() => {
    fetchEntries();
    setCurrentAction((prev) => (prev ? { ...prev, status: "success" } : null));
  }, [fetchEntries, setCurrentAction]);

  const onConfirm = useCallback(
    (data: ConfirmData) => {
      setConfirmData(data);
      if (currentSessionId) {
        const itemList = data.items.map((item, i) => `${i + 1}. ${item.title}`).join("\n");
        const actionLabel = data.action === "delete" ? "删除" : "更新";
        addMessage(currentSessionId, {
          role: "assistant",
          content: `找到 ${data.items.length} 个匹配项，请选择：\n${itemList}\n\n输入序号选择，或输入"全部${actionLabel}"批量操作`,
        });
      }
      setCurrentAction(null);
    },
    [currentSessionId, addMessage, setConfirmData, setCurrentAction]
  );

  const onResults = useCallback(
    (items: ResultItem[]) => {
      clearSearchResults();
      setSearchResults(items);
      setCurrentIntent("read");
      setCurrentAction((prev) => (prev ? { ...prev, status: "success" } : null));
    },
    [clearSearchResults, setSearchResults, setCurrentIntent, setCurrentAction]
  );

  return {
    onIntentDetected,
    onCreated,
    onUpdated,
    onDeleted,
    onConfirm,
    onResults,
    updateTitleIfNeeded,
  };
}
