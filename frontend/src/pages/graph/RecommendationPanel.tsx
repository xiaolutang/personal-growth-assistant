import { useEffect, useState } from "react";
import { Loader2, AlertCircle, BookOpen, RotateCcw, GitBranch, Sparkles } from "lucide-react";
import {
  fetchRecommendations,
  type RecommendationResponse,
  type KnowledgeGapItem,
  type ReviewSuggestionItem,
  type RelatedConceptItem,
} from "@/services/api";
import { masteryColors, masteryLabels } from "./constants";

interface RecommendationPanelProps {
  onSelectConcept: (concept: string) => void;
}

// 单条推荐卡片
function RecommendationCard({
  icon,
  label,
  concept,
  reason,
  mastery,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  concept: string;
  reason: string;
  mastery?: string | null;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left p-3 rounded-xl border bg-card hover:bg-accent/50 transition-colors group"
    >
      <div className="flex items-start gap-2.5">
        <div className="mt-0.5 shrink-0">{icon}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-xs font-medium text-muted-foreground">{label}</span>
            {mastery && (
              <span className="inline-flex items-center gap-1 text-[10px] text-muted-foreground">
                <span
                  className="inline-block w-1.5 h-1.5 rounded-full"
                  style={{ backgroundColor: masteryColors[mastery] ?? "#9ca3af" }}
                />
                {masteryLabels[mastery] ?? mastery}
              </span>
            )}
          </div>
          <p className="text-sm font-medium truncate group-hover:text-primary transition-colors">
            {concept}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{reason}</p>
        </div>
      </div>
    </button>
  );
}

function gapReason(item: KnowledgeGapItem): string {
  if (item.missing_prerequisites.length === 0) return "建议补充相关前置知识";
  return `缺少前置知识: ${item.missing_prerequisites.join("、")}`;
}

function reviewReason(item: ReviewSuggestionItem): string {
  if (item.last_seen_days_ago === 0) return "近期未复习，建议回顾巩固";
  return `${item.last_seen_days_ago} 天前最后接触，建议复习巩固`;
}

function cooccurrenceReason(item: RelatedConceptItem): string {
  return item.source === "neo4j"
    ? "与已掌握概念高度关联，推荐拓展"
    : "与已有记录标签共现，可能感兴趣";
}

export function RecommendationPanel({ onSelectConcept }: RecommendationPanelProps) {
  const [data, setData] = useState<RecommendationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchRecommendations()
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "加载推荐失败");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
        <span className="ml-2 text-sm text-muted-foreground">加载推荐中...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3 py-20">
        <AlertCircle className="h-8 w-8 text-destructive" />
        <p className="text-sm text-destructive">{error}</p>
        <button
          onClick={() => {
            setLoading(true);
            setError(null);
            fetchRecommendations()
              .then(setData)
              .catch((e) => setError(e.message || "加载推荐失败"))
              .finally(() => setLoading(false));
          }}
          className="text-sm text-primary hover:underline"
        >
          重试
        </button>
      </div>
    );
  }

  if (!data) return null;

  const allItems = [
    ...data.knowledge_gaps.map((g) => ({ type: "gap" as const, item: g })),
    ...data.review_suggestions.map((r) => ({ type: "review" as const, item: r })),
    ...data.related_concepts.map((c) => ({ type: "cooccur" as const, item: c })),
  ];

  if (allItems.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3 py-20">
        <Sparkles className="h-10 w-10 text-muted-foreground/50" />
        <p className="text-sm text-muted-foreground">暂无推荐，继续记录学习内容</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
      {/* 知识缺口 */}
      {data.knowledge_gaps.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3">
            <BookOpen className="h-4 w-4 text-orange-500" />
            <h3 className="text-sm font-semibold">知识缺口</h3>
            <span className="text-xs text-muted-foreground">({data.knowledge_gaps.length})</span>
          </div>
          <div className="space-y-2">
            {data.knowledge_gaps.map((item) => (
              <RecommendationCard
                key={`gap-${item.concept}`}
                icon={<BookOpen className="h-4 w-4 text-orange-500" />}
                label="缺口"
                concept={item.concept}
                reason={gapReason(item)}
                onClick={() => onSelectConcept(item.concept)}
              />
            ))}
          </div>
        </section>
      )}

      {/* 复习推荐 */}
      {data.review_suggestions.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3">
            <RotateCcw className="h-4 w-4 text-blue-500" />
            <h3 className="text-sm font-semibold">复习推荐</h3>
            <span className="text-xs text-muted-foreground">({data.review_suggestions.length})</span>
          </div>
          <div className="space-y-2">
            {data.review_suggestions.map((item) => (
              <RecommendationCard
                key={`review-${item.concept}`}
                icon={<RotateCcw className="h-4 w-4 text-blue-500" />}
                label="复习"
                concept={item.concept}
                reason={reviewReason(item)}
                onClick={() => onSelectConcept(item.concept)}
              />
            ))}
          </div>
        </section>
      )}

      {/* 共现推荐 */}
      {data.related_concepts.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3">
            <GitBranch className="h-4 w-4 text-green-500" />
            <h3 className="text-sm font-semibold">共现推荐</h3>
            <span className="text-xs text-muted-foreground">({data.related_concepts.length})</span>
          </div>
          <div className="space-y-2">
            {data.related_concepts.map((item) => (
              <RecommendationCard
                key={`cooccur-${item.concept}`}
                icon={<GitBranch className="h-4 w-4 text-green-500" />}
                label="共现"
                concept={item.concept}
                reason={cooccurrenceReason(item)}
                onClick={() => onSelectConcept(item.concept)}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
