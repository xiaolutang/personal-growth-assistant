import { useCallback } from "react";
import { cn } from "@/lib/utils";
import { ToolCallCard } from "./ToolCallCard";
import { FeedbackButtons, NEGATIVE_OPTIONS } from "./FeedbackButtons";
import type { FeedbackData } from "./FeedbackButtons";
import { submitFeedback } from "@/services/api";
import type { AgentMessage as AgentMessageType } from "@/stores/agentStore";

interface AgentMessageProps {
  message: AgentMessageType;
  className?: string;
}

/** 将 FeedbackData 映射为 API payload（匹配后端 FeedbackRequest） */
function buildFeedbackPayload(messageId: string, feedback: FeedbackData) {
  const reasonMap = Object.fromEntries(
    NEGATIVE_OPTIONS.map((o) => [o.key, o.key === "other" ? "other_negative" : o.key])
  );

  if (feedback.type === "positive") {
    return {
      title: `[Agent 反馈] 赞 - ${messageId}`,
      description: "用户对 Agent 回复表示满意",
      severity: "low" as const,
      feedback_type: "agent" as const,
      message_id: messageId,
      reason: null,
      detail: null,
    };
  }

  if (feedback.type === "flag") {
    return {
      title: `[Agent 标记] 不当内容 - ${messageId}`,
      description: "用户标记此回复为不当内容",
      severity: "high" as const,
      feedback_type: "agent" as const,
      message_id: messageId,
      reason: null,
      detail: null,
    };
  }

  // negative
  const mappedReason = feedback.reason
    ? reasonMap[feedback.reason] || feedback.reason
    : "other_negative";
  const reasonLabel = feedback.reason
    ? reasonMap[feedback.reason] || feedback.reason
    : "未知原因";
  const detail = feedback.detail
    ? `${reasonLabel}：${feedback.detail}`
    : reasonLabel;

  return {
    title: `[Agent 反馈] 踩 - ${messageId}`,
    description: detail,
    severity: "medium" as const,
    feedback_type: "agent" as const,
    message_id: messageId,
    reason: mappedReason,
    detail: feedback.detail || null,
  };
}

export function AgentMessage({ message, className }: AgentMessageProps) {
  const handleFeedback = useCallback(
    async (feedback: FeedbackData) => {
      try {
        const payload = buildFeedbackPayload(message.id, feedback);
        await submitFeedback(payload);
      } catch (err) {
        // 静默失败，不影响用户体验
        console.error("[FeedbackButtons] 反馈提交失败:", err);
      }
    },
    [message.id],
  );

  // 工具调用类型 → 渲染 ToolCallCard
  if (message.type === "tool_call" && message.toolCall) {
    return (
      <div className={cn("flex items-start gap-2.5", className)}>
        {/* Agent 头像 */}
        <div className="h-7 w-7 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center shrink-0">
          <span className="text-xs font-bold text-indigo-600 dark:text-indigo-300">AI</span>
        </div>
        <div className="flex-1 min-w-0">
          <ToolCallCard toolCall={message.toolCall} />
        </div>
      </div>
    );
  }

  // 文本类型 → 渲染文本气泡 + 反馈按钮
  if (message.type === "text" && message.content) {
    return (
      <div className={cn("flex items-start gap-2.5", className)}>
        {/* Agent 头像 */}
        <div className="h-7 w-7 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center shrink-0">
          <span className="text-xs font-bold text-indigo-600 dark:text-indigo-300">AI</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="max-w-[90%] rounded-xl bg-muted px-3.5 py-2.5 text-sm leading-relaxed text-foreground whitespace-pre-wrap break-words">
            {message.content}
          </div>

          {/* 条目变更信息 */}
          {message.entryChange && (
            <div className="mt-1.5 text-xs text-muted-foreground">
              {message.entryChange.title && (
                <span>已创建: {message.entryChange.title}</span>
              )}
              {message.entryChange.changes && (
                <span>已更新: {message.entryChange.changes}</span>
              )}
            </div>
          )}

          {/* 反馈按钮 */}
          <div className="mt-1.5">
            <FeedbackButtons
              messageId={message.id}
              onSubmit={handleFeedback}
            />
          </div>
        </div>
      </div>
    );
  }

  // 其他类型不渲染
  return null;
}
