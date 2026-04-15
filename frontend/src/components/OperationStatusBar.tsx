import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { OperationStatus } from "@/stores/chatStore";
import { cn } from "@/lib/utils";
import { useEffect, useRef } from "react";
import { getActionIcon } from "@/lib/actionUtils";

interface OperationStatusBarProps {
  operation: OperationStatus | null;
  onDismiss: () => void;
}

export function OperationStatusBar({ operation, onDismiss }: OperationStatusBarProps) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 3秒后自动消失
  useEffect(() => {
    if (operation?.status === "success") {
      timerRef.current = setTimeout(onDismiss, 3000);
    }
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [operation, onDismiss]);

  if (!operation) return null;

  const { type, name, status, message } = operation;
  const IconComponent = getActionIcon(type === "tool" || type === "skill" ? type : "intent", name || type);

  // 获取颜色
  const statusColor =
    status === "success"
      ? "bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300"
      : status === "error"
      ? "bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300"
      : status === "pending"
      ? "bg-muted text-muted-foreground"
      : "";

  return (
    <div
      className={cn(
        "flex items-center gap-2 px-3 py-1.5 rounded-md text-sm border",
        statusColor
      )}
    >
      <IconComponent className={cn("h-4 w-4", status === "success" ? "text-green-600" : "text-muted-foreground")} />
      <span className="flex-1">{message}</span>
      <Button
        variant="ghost"
        size="sm"
        className="h-4 w-4 p-0"
        onClick={onDismiss}
      >
        <X className="h-3 w-3" />
      </Button>
    </div>
  );
}
