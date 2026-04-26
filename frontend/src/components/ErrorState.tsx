import type { LucideIcon } from "lucide-react";
import { AlertCircle, RefreshCw } from "lucide-react";

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
  icon?: LucideIcon;
}

export function ErrorState({ message, onRetry, icon: Icon = AlertCircle }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-4">
      <div className="flex items-center justify-center w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/30">
        <Icon className="h-8 w-8 text-red-500 dark:text-red-400" />
      </div>
      <p className="text-sm text-muted-foreground">{message}</p>
      {onRetry && (
        <button
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm hover:bg-primary/90 transition-colors"
          onClick={onRetry}
        >
          <RefreshCw className="h-4 w-4" />
          重试
        </button>
      )}
    </div>
  );
}
