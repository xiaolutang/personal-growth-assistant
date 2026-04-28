import { cn } from "@/lib/utils";

interface UserMessageProps {
  content: string;
  className?: string;
}

export function UserMessage({ content, className }: UserMessageProps) {
  return (
    <div className={cn("flex justify-end", className)}>
      <div className="max-w-[85%] rounded-xl bg-indigo-500 px-3.5 py-2.5 text-sm leading-relaxed text-white whitespace-pre-wrap break-words">
        {content}
      </div>
    </div>
  );
}
