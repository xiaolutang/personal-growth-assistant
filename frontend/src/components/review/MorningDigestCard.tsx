import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useMorningDigest } from "@/hooks/useMorningDigest";
import { Sparkles, ChevronDown, ChevronUp } from "lucide-react";

interface MorningDigestCardProps {
  visible: boolean;
}

export function MorningDigestCard({ visible }: MorningDigestCardProps) {
  const { data: morningDigest } = useMorningDigest();
  const [morningDigestExpanded, setMorningDigestExpanded] = useState(false);

  if (!visible) return null;
  if (!morningDigest) return null;

  const hasContent = morningDigest.ai_suggestion || morningDigest.todos.length > 0 || morningDigest.overdue.length > 0 || morningDigest.stale_inbox.length > 0 || (morningDigest.learning_streak != null && morningDigest.learning_streak > 0);

  return (
    <Card className="border-l-4 border-l-amber-500 dark:border-l-amber-400">
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-amber-500" />
          今日晨报
          {morningDigest.learning_streak != null && morningDigest.learning_streak > 0 && (
            <Badge variant="secondary" className="text-xs">
              连续 {morningDigest.learning_streak} 天
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {hasContent ? (
          <div>
            {/* AI 建议 */}
            {morningDigest.ai_suggestion && (
              <div className={`text-sm leading-relaxed mb-3 ${!morningDigestExpanded ? "line-clamp-2" : ""}`}>
                {morningDigest.ai_suggestion}
              </div>
            )}

            {/* 统计摘要 */}
            <div className="flex flex-wrap gap-3 mb-2">
              {morningDigest.todos.length > 0 && (
                <span className="text-xs text-muted-foreground">
                  待办 {morningDigest.todos.length} 项
                </span>
              )}
              {morningDigest.overdue.length > 0 && (
                <span className="text-xs text-red-500">
                  过期 {morningDigest.overdue.length} 项
                </span>
              )}
              {morningDigest.stale_inbox.length > 0 && (
                <span className="text-xs text-muted-foreground">
                  灵感提醒 {morningDigest.stale_inbox.length} 项
                </span>
              )}
            </div>

            {/* 展开后显示详细列表 */}
            {morningDigestExpanded && (
              <div className="space-y-2 mt-2 pt-2 border-t">
                {morningDigest.todos.length > 0 && (
                  <div>
                    <div className="text-xs font-medium text-muted-foreground mb-1">待办任务</div>
                    {morningDigest.todos.slice(0, 5).map((t) => (
                      <div key={t.id} className="text-sm truncate">• {t.title}</div>
                    ))}
                  </div>
                )}
                {morningDigest.overdue.length > 0 && (
                  <div>
                    <div className="text-xs font-medium text-red-500 mb-1">过期任务</div>
                    {morningDigest.overdue.slice(0, 3).map((t) => (
                      <div key={t.id} className="text-sm truncate">• {t.title}</div>
                    ))}
                  </div>
                )}
                {morningDigest.stale_inbox.length > 0 && (
                  <div>
                    <div className="text-xs font-medium text-muted-foreground mb-1">待处理灵感</div>
                    {morningDigest.stale_inbox.slice(0, 3).map((t) => (
                      <div key={t.id} className="text-sm truncate">• {t.title}</div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 展开/收起 */}
            {(morningDigest.ai_suggestion && morningDigest.ai_suggestion.length > 80 || morningDigest.todos.length > 0 || morningDigest.overdue.length > 0) && (
              <button
                onClick={() => setMorningDigestExpanded(!morningDigestExpanded)}
                className="mt-2 text-xs text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300 flex items-center gap-1"
              >
                {morningDigestExpanded ? (
                  <>收起 <ChevronUp className="h-3 w-3" /></>
                ) : (
                  <>展开详情 <ChevronDown className="h-3 w-3" /></>
                )}
              </button>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground/60 italic">今日暂无晨报内容</p>
        )}
      </CardContent>
    </Card>
  );
}

export { MorningDigestCard as default };
