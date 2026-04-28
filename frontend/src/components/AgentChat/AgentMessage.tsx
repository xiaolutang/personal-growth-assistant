import { cn } from "@/lib/utils";
import { ToolCallCard } from "./ToolCallCard";
import type { AgentMessage as AgentMessageType } from "@/stores/agentStore";

interface AgentMessageProps {
  message: AgentMessageType;
  className?: string;
}

export function AgentMessage({ message, className }: AgentMessageProps) {
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

  // 文本类型 → 渲染文本气泡
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
        </div>
      </div>
    );
  }

  // 其他类型不渲染
  return null;
}
