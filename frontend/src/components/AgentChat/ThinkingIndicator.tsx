import { cn } from "@/lib/utils";

interface ThinkingIndicatorProps {
  content?: string;
  className?: string;
}

export function ThinkingIndicator({ content, className }: ThinkingIndicatorProps) {
  return (
    <div className={cn("flex items-start gap-2.5", className)}>
      {/* Agent 头像 */}
      <div className="h-7 w-7 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center shrink-0">
        <span className="text-xs font-bold text-indigo-600 dark:text-indigo-300">AI</span>
      </div>

      <div className="flex-1 min-w-0">
        {/* 脉冲点动画 */}
        <div className="inline-flex items-center gap-1 rounded-xl bg-muted px-3 py-2">
          <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-pulse" />
          <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-pulse [animation-delay:200ms]" />
          <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-pulse [animation-delay:400ms]" />
        </div>

        {/* 思考内容 */}
        {content && (
          <p className="mt-1.5 text-xs text-muted-foreground italic line-clamp-2">
            {content}
          </p>
        )}
      </div>
    </div>
  );
}
