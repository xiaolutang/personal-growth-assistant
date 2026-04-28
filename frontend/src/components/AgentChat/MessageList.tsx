import { useEffect, useRef, useCallback } from "react";
import type { AgentMessage as AgentMessageType } from "@/stores/agentStore";
import { UserMessage } from "./UserMessage";
import { AgentMessage } from "./AgentMessage";

interface MessageListProps {
  messages: AgentMessageType[];
  /** 额外的底部内容（如 ThinkingIndicator） */
  footer?: React.ReactNode;
  className?: string;
}

export function MessageList({ messages, footer, className }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  // 消息变化时自动滚动到底部
  useEffect(() => {
    scrollToBottom();
  }, [messages, footer, scrollToBottom]);

  if (messages.length === 0 && !footer) {
    return null;
  }

  return (
    <div className={`flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-0 ${className ?? ""}`}>
      {messages.map((msg) => {
        if (msg.role === "user") {
          return <UserMessage key={msg.id} content={msg.content} />;
        }
        return <AgentMessage key={msg.id} message={msg} />;
      })}
      {footer}
      <div ref={endRef} />
    </div>
  );
}
