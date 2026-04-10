import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ServiceUnavailableProps {
  onRetry?: () => void;
}

export function ServiceUnavailable({ onRetry }: ServiceUnavailableProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="flex items-center justify-center w-16 h-16 rounded-full bg-amber-100 mb-6">
        <AlertCircle className="w-8 h-8 text-amber-600" />
      </div>
      <h2 className="text-xl font-semibold text-foreground mb-2">
        服务暂时不可用
      </h2>
      <p className="text-muted-foreground text-center max-w-md mb-6">
        后端服务正在启动中或暂时无法响应，请稍后重试
      </p>
      {onRetry && (
        <Button variant="outline" onClick={onRetry} className="gap-2">
          <RefreshCw className="w-4 h-4" />
          重试
        </Button>
      )}
    </div>
  );
}
