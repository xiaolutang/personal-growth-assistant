import { CheckCircle, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { getActionLabel, getActionIcon, getActionColor, type ActionType } from "@/lib/actionUtils";

interface ActionIndicatorProps {
  type: ActionType;  // 操作类型
  name: string;                    // 操作名称
  params?: Record<string, unknown>;  // 参数（工具调用时显示)
  status: "pending" | "running" | "success" | "error";  // 状态
  compact?: boolean;                 // 是否紧凑模式
}

export function ActionIndicator({
  type,
  name,
  params,
  status,
  compact = false,
}: ActionIndicatorProps) {
  const IconComponent = getActionIcon(type, name);
  const color = getActionColor(type, name);
  const label = getActionLabel(type, name);

  return (
    <div
      className={cn(
        "flex items-center gap-2 px-2 py-1 rounded text-xs",
        status === "running" && "animate-pulse",
        status === "success" && "bg-green-50 text-green-700",
        status === "error" && "bg-red-50 text-red-700",
        status === "pending" && "bg-muted"
      )}
    >
      <span className={cn("flex items-center", color)}>
        <IconComponent className="h-4 w-4" />
      </span>
      <span className="font-medium">{label}</span>
      {type === "tool" && params && !compact && (
        <span className="text-muted-foreground text-xs">
          {JSON.stringify(params)}
        </span>
      )}
      {status === "success" && (
        <CheckCircle className="h-3 w-3 text-green-600" />
      )}
      {status === "error" && (
        <X className="h-3 w-3 text-red-600" />
      )}
    </div>
  );
}
