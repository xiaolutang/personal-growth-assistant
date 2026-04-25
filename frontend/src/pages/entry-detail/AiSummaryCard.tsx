import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Sparkles,
  ChevronDown,
  ChevronUp,
  Loader2,
  AlertCircle,
  RefreshCw,
  Clock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { EntrySummaryResponse } from "@/services/api";

interface AiSummaryCardProps {
  content: string;
  expanded: boolean;
  loading: boolean;
  error: string | null;
  data: EntrySummaryResponse | null;
  onToggle: () => void;
  onRetry: () => void;
}

export function AiSummaryCard({
  content,
  expanded,
  loading,
  error,
  data,
  onToggle,
  onRetry,
}: AiSummaryCardProps) {
  if (!content || content.trim().length === 0) return null;

  return (
    <Card className="mt-6">
      <CardHeader
        className="pb-2 cursor-pointer select-none"
        onClick={onToggle}
      >
        <CardTitle className="text-base flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            AI 摘要
          </span>
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </CardTitle>
      </CardHeader>
      {expanded && (
        <CardContent>
          {loading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
              <Loader2 className="h-4 w-4 animate-spin" />
              正在生成摘要...
            </div>
          )}
          {error && !loading && (
            <div className="flex items-center justify-between py-2">
              <div className="flex items-center gap-2 text-sm text-destructive">
                <AlertCircle className="h-4 w-4" />
                {error}
              </div>
              <Button variant="outline" size="sm" onClick={onRetry}>
                <RefreshCw className="h-3 w-3 mr-1" />
                重试
              </Button>
            </div>
          )}
          {data && !loading && (
            <div className="space-y-3">
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {data.summary}
                </ReactMarkdown>
              </div>
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                {data.cached && (
                  <Badge variant="secondary" className="text-xs">已缓存</Badge>
                )}
                {data.generated_at && (
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {new Date(data.generated_at).toLocaleString()}
                  </span>
                )}
              </div>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}
