import { Circle, ArrowRight, GitBranch } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { KnowledgeGraphResponse, ConceptRelation } from "@/types/task";

interface KnowledgeGraphProps {
  data: KnowledgeGraphResponse;
  onConceptClick?: (concept: string) => void;
}

export function KnowledgeGraph({ data, onConceptClick }: KnowledgeGraphProps) {
  const { center, connections } = data;

  if (!center && connections.length === 0) {
    return (
      <Card className="p-4">
        <div className="text-center text-muted-foreground">
          没有找到相关知识图谱
        </div>
      </Card>
    );
  }

  return (
    <Card>
      {/* Center Concept */}
      {center && (
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Circle className="h-5 w-5 text-primary fill-primary/20" />
            <CardTitle className="text-lg">{center.name}</CardTitle>
            {center.category && (
              <Badge variant="secondary" className="text-xs">
                {center.category}
              </Badge>
            )}
          </div>
          {center.description && (
            <p className="text-sm text-muted-foreground mt-1">
              {center.description}
            </p>
          )}
        </CardHeader>
      )}

      {/* Connections */}
      {connections.length > 0 && (
        <CardContent className="pt-0">
          <div className="text-xs text-muted-foreground mb-2 flex items-center gap-1">
            <GitBranch className="h-3 w-3" />
            相关概念 ({connections.length})
          </div>
          <div className="space-y-2">
            {connections.map((conn, index) => (
              <ConceptItem
                key={`${conn.name}-${index}`}
                relation={conn}
                onClick={() => onConceptClick?.(conn.name)}
              />
            ))}
          </div>
        </CardContent>
      )}
    </Card>
  );
}

interface ConceptItemProps {
  relation: ConceptRelation;
  onClick?: () => void;
}

function ConceptItem({ relation, onClick }: ConceptItemProps) {
  return (
    <div
      className="flex items-center gap-2 p-2 rounded-lg hover:bg-accent/50 cursor-pointer transition-colors"
      onClick={onClick}
    >
      <ArrowRight className="h-3 w-3 text-muted-foreground flex-shrink-0" />
      <span className="text-sm font-medium">{relation.name}</span>
      <Badge variant="outline" className="text-xs">
        {relation.relationship}
      </Badge>
      {relation.category && (
        <Badge variant="secondary" className="text-xs">
          {relation.category}
        </Badge>
      )}
    </div>
  );
}

// 简化版知识图谱（用于聊天消息中）
interface KnowledgeGraphInlineProps {
  data: KnowledgeGraphResponse;
  onConceptClick?: (concept: string) => void;
}

export function KnowledgeGraphInline({ data, onConceptClick }: KnowledgeGraphInlineProps) {
  const { center, connections } = data;

  if (!center && connections.length === 0) {
    return <span className="text-muted-foreground">没有找到相关知识图谱</span>;
  }

  return (
    <div className="bg-muted/50 rounded-lg p-3 space-y-2">
      {/* Center */}
      {center && (
        <div className="flex items-center gap-2">
          <Circle className="h-4 w-4 text-primary fill-primary/20" />
          <span className="font-medium">{center.name}</span>
          {center.category && (
            <Badge variant="secondary" className="text-xs">
              {center.category}
            </Badge>
          )}
        </div>
      )}

      {/* Connections */}
      {connections.length > 0 && (
        <div className="pl-6 space-y-1">
          {connections.slice(0, 5).map((conn, index) => (
            <div
              key={`${conn.name}-${index}`}
              className="flex items-center gap-2 text-sm cursor-pointer hover:text-primary"
              onClick={() => onConceptClick?.(conn.name)}
            >
              <ArrowRight className="h-3 w-3 text-muted-foreground" />
              <span>{conn.name}</span>
              <span className="text-xs text-muted-foreground">
                ({conn.relationship})
              </span>
            </div>
          ))}
          {connections.length > 5 && (
            <div className="text-xs text-muted-foreground">
              还有 {connections.length - 5} 个相关概念...
            </div>
          )}
        </div>
      )}
    </div>
  );
}
