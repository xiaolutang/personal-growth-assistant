import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { SearchResult } from "@/types/task";
import { categoryConfig } from "@/config/constants";

interface SearchResultCardProps {
  result: SearchResult;
  onClick?: () => void;
}

export function SearchResultCard({ result, onClick }: SearchResultCardProps) {
  const config = categoryConfig[result.type as keyof typeof categoryConfig] || categoryConfig.note;
  const Icon = config.icon;
  const scorePercent = Math.round(result.score * 100);

  return (
    <Card
      className="flex items-start gap-3 p-3 cursor-pointer hover:bg-accent/50 transition-colors"
      onClick={onClick}
    >
      {/* Type Icon */}
      <div className={`flex-shrink-0 mt-0.5 ${config.color}`}>
        <Icon className="h-4 w-4" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium truncate">{result.title}</p>
          <Badge variant="secondary" className="text-xs">
            {config.label}
          </Badge>
        </div>

        {/* Tags */}
        {result.tags && result.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1.5">
            {result.tags.map((tag) => (
              <Badge key={tag} variant="outline" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        )}

        {/* File Path */}
        <p className="text-xs text-muted-foreground mt-1 truncate">
          {result.file_path}
        </p>
      </div>

      {/* Score */}
      <div className="flex-shrink-0 text-right">
        <div className="text-xs font-medium text-primary">{scorePercent}%</div>
        <div className="text-xs text-muted-foreground">相关度</div>
      </div>
    </Card>
  );
}

// 搜索结果列表组件
interface SearchResultListProps {
  results: SearchResult[];
  onItemClick?: (result: SearchResult) => void;
}

export function SearchResultList({ results, onItemClick }: SearchResultListProps) {
  if (results.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        没有找到相关内容
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {results.map((result) => (
        <SearchResultCard
          key={result.id}
          result={result}
          onClick={() => onItemClick?.(result)}
        />
      ))}
    </div>
  );
}
