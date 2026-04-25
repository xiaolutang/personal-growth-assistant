import {
  Sparkles,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { KnowledgeGraphThumbnail } from "@/components/KnowledgeGraphThumbnail";
import type { KnowledgeContextResponse } from "@/services/api";

interface KnowledgeContextCardProps {
  knowledgeContext: KnowledgeContextResponse | null;
  loading: boolean;
  error: boolean;
  expanded: boolean;
  setExpanded: React.Dispatch<React.SetStateAction<boolean>>;
}

export function KnowledgeContextCard({
  knowledgeContext,
  loading,
  error,
  expanded,
  setExpanded,
}: KnowledgeContextCardProps) {
  if (error) return null;

  return (
    <Card className="mt-6">
      <CardHeader
        className="pb-2 cursor-pointer select-none"
        onClick={() => setExpanded(!expanded)}
      >
        <CardTitle className="text-base flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            知识上下文
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
          <KnowledgeGraphThumbnail
            nodes={knowledgeContext?.nodes ?? []}
            edges={knowledgeContext?.edges ?? []}
            centerConcepts={knowledgeContext?.center_concepts ?? []}
            loading={loading}
          />
          {knowledgeContext && knowledgeContext.nodes.length > 0 && (
            <p className="text-xs text-muted-foreground mt-2 text-center">
              点击概念节点查看详情
            </p>
          )}
        </CardContent>
      )}
    </Card>
  );
}
