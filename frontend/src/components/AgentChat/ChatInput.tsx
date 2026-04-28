import { useRef, useCallback, useImperativeHandle, forwardRef } from "react";
import { Send, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  isLoading?: boolean;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export interface ChatInputHandle {
  focus: () => void;
}

export const ChatInput = forwardRef<ChatInputHandle, ChatInputProps>(function ChatInput({
  value,
  onChange,
  onSend,
  isLoading = false,
  placeholder = "输入消息...",
  disabled = false,
  className,
}, ref) {
  const inputRef = useRef<HTMLInputElement>(null);

  useImperativeHandle(ref, () => ({
    focus: () => inputRef.current?.focus(),
  }));

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (!isLoading && value.trim()) {
          onSend();
        }
      }
    },
    [isLoading, onSend, value],
  );

  const canSend = !isLoading && !disabled && value.trim().length > 0;

  return (
    <div className={cn("border-t border-border p-3", className)}>
      <div className="flex items-center gap-2">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isLoading || disabled}
          className="flex-1 h-9 rounded-lg border border-input bg-background px-3 py-1 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
        />
        <button
          type="button"
          onClick={onSend}
          disabled={!canSend}
          className="h-9 w-9 inline-flex items-center justify-center rounded-lg bg-indigo-500 text-white hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-label="发送"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </button>
      </div>
    </div>
  );
});

/** 暴露 focus 方法给父组件 */
export function useChatInputFocus() {
  // 这个 hook 不再持有 ref，由 ChatInput 内部管理
  // 外部可通过重新渲染触发自动聚焦
  return null;
}
