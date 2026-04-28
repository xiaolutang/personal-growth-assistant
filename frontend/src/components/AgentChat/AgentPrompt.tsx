import { MessageCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface AgentPromptProps {
  prompt: string;
  className?: string;
}

export function AgentPrompt({ prompt, className }: AgentPromptProps) {
  return (
    <div
      className={cn(
        "flex items-start gap-2 rounded-xl border border-indigo-200 bg-indigo-50/60 dark:border-indigo-800 dark:bg-indigo-950/20 px-3 py-2.5 text-sm",
        className,
      )}
    >
      <MessageCircle className="h-4 w-4 text-indigo-500 shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <span className="text-xs font-medium text-indigo-600 dark:text-indigo-400">
          追问
        </span>
        <p className="mt-0.5 text-foreground leading-relaxed whitespace-pre-wrap break-words">
          {prompt}
        </p>
      </div>
    </div>
  );
}
