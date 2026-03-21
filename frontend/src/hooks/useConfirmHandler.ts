import { useCallback } from "react";
import type { ConfirmData, ConfirmRequest } from "./useStreamParse";

interface UseConfirmHandlerOptions {
  currentSessionId: string | null;
  createSession: () => string;
  addMessage: (sessionId: string, message: { role: "user" | "assistant"; content: string }) => void;
  parse: (text: string, sessionId: string, confirm?: ConfirmRequest) => Promise<unknown>;
}

/**
 * 处理确认操作（多选场景）的 Hook
 *
 * 支持：
 * - 批量操作（全部、都、所有等关键词）
 * - 数字选择
 * - 取消操作
 */
export function useConfirmHandler(
  confirmData: ConfirmData | null,
  options: UseConfirmHandlerOptions
) {
  const { currentSessionId, createSession, addMessage, parse } = options;

  const handleConfirm = useCallback(
    async (userMessage: string): Promise<boolean> => {
      if (!confirmData) return false;

      const activeSessionId = currentSessionId || createSession();

      // 批量操作关键词
      const batchKeywords = ["都", "全部", "所有", "两个", "三个", "这几个", "以上"];
      if (batchKeywords.some((k) => userMessage.includes(k))) {
        // 批量操作：并行发送所有确认请求
        const actionLabel = confirmData.action === "delete" ? "删除" : "更新";
        const results = await Promise.allSettled(
          confirmData.items.map((item) =>
            parse(
              `${actionLabel} ${item.title}`,
              activeSessionId,
              { action: confirmData.action, item_id: item.id }
            )
          )
        );
        const successCount = results.filter((r) => r.status === "fulfilled").length;
        addMessage(activeSessionId, {
          role: "assistant",
          content: `已${actionLabel} ${successCount} 个条目`,
        });
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
        return true;
      }

      // 取消操作
      if (/取消|算了|不要了|不删|不更/.test(userMessage)) {
        addMessage(activeSessionId, { role: "assistant", content: "操作已取消" });
        return true;
      }

      return false;
    },
    [confirmData, currentSessionId, createSession, addMessage, parse]
  );

  return { handleConfirm };
}
