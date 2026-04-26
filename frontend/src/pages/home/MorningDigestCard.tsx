import { Card, CardContent } from "@/components/ui/card";
import { Sparkles, Clock, AlertTriangle, Inbox, BookOpen, Flame, Target, Eye, ArrowRight, Lightbulb } from "lucide-react";
import type { MorningDigestResponse } from "@/services/api";
import { DigestStat } from "./DigestStat";

interface MorningDigestCardProps {
  digest: MorningDigestResponse | null;
  digestLoading: boolean;
  digestError: string | null;
  onDismiss: () => void;
  onNavigateToEntry: (entryId: string) => void;
}

export function MorningDigestCard({
  digest,
  digestLoading,
  digestError,
  onDismiss,
  onNavigateToEntry,
}: MorningDigestCardProps) {
  return (
    <Card className="border-l-4 border-l-indigo-500 dark:border-l-indigo-400 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950/30 dark:to-purple-950/30">
      <CardContent className="pt-4 pb-4">
        {digestLoading ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-full bg-primary/20 animate-pulse" />
              <div className="h-4 bg-primary/10 rounded animate-pulse flex-1" />
            </div>
            <div className="h-4 bg-primary/10 rounded animate-pulse w-full" />
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-10 bg-primary/10 rounded animate-pulse" />
              ))}
            </div>
          </div>
        ) : digestError ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Sparkles className="h-4 w-4 text-indigo-400" />
            <span>晨报加载失败，请稍后刷新</span>
          </div>
        ) : digest && (
          <div className="space-y-3">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-indigo-500" />
                <span className="text-sm font-medium text-indigo-700 dark:text-indigo-300">
                  日知晨报
                </span>
              </div>
              <div className="flex items-center gap-2">
                {digest.cached_at && (
                  <span className="text-[10px] text-muted-foreground">
                    上次更新于 {new Date(digest.cached_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}
                  </span>
                )}
                <button
                  onClick={onDismiss}
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  收起
                </button>
              </div>
            </div>
            <div className="flex items-start gap-2 p-2.5 rounded-lg bg-indigo-100/50 dark:bg-indigo-900/20 border border-indigo-200/50 dark:border-indigo-800/30">
              <Sparkles className="h-3.5 w-3.5 text-indigo-500 mt-0.5 shrink-0" />
              <p className="text-sm text-indigo-900 dark:text-indigo-100 leading-relaxed">
                {digest.ai_suggestion}
              </p>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <DigestStat
                icon={<Clock className="h-3.5 w-3.5" />}
                label="待办"
                count={digest.todos.length}
                color="text-blue-500 dark:text-blue-400"
              />
              <DigestStat
                icon={<AlertTriangle className="h-3.5 w-3.5" />}
                label="逾期"
                count={digest.overdue.length}
                color="text-red-500 dark:text-red-400"
              />
              <DigestStat
                icon={<Inbox className="h-3.5 w-3.5" />}
                label="待跟进"
                count={digest.stale_inbox.length}
                color="text-yellow-500 dark:text-yellow-400"
              />
              <DigestStat
                icon={<BookOpen className="h-3.5 w-3.5" />}
                label="新概念"
                count={digest.weekly_summary.new_concepts.length}
                color="text-green-500 dark:text-green-400"
              />
            </div>

            {/* 学习连续天数 */}
            {(digest.learning_streak ?? 0) > 0 && (
              <div className="flex items-center gap-2 pt-1">
                <Flame className={`${
                  (digest.learning_streak ?? 0) >= 7
                    ? "h-5 w-5 text-orange-500"
                    : "h-4 w-4 text-orange-400"
                }`} />
                <span className={`text-sm font-medium ${
                  (digest.learning_streak ?? 0) >= 7
                    ? "text-orange-600 dark:text-orange-400"
                    : "text-muted-foreground"
                }`}>
                  连续学习 {(digest.learning_streak ?? 0)} 天
                </span>
                {(digest.learning_streak ?? 0) >= 7 && (
                  <span className="text-xs text-orange-500">太棒了！</span>
                )}
              </div>
            )}

            {/* 今日聚焦 */}
            {digest.daily_focus && (
              <div
                className="flex items-start gap-2 p-2 rounded-lg bg-background/60 cursor-pointer hover:bg-background/80 transition-colors"
                onClick={() => {
                  if (digest.daily_focus?.target_entry_id) {
                    onNavigateToEntry(digest.daily_focus.target_entry_id);
                  }
                }}
              >
                <Target className="h-4 w-4 text-indigo-500 mt-0.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{digest.daily_focus.title}</p>
                  <p className="text-xs text-muted-foreground line-clamp-2">{digest.daily_focus.description}</p>
                </div>
                {digest.daily_focus.target_entry_id && (
                  <ArrowRight className="h-3.5 w-3.5 text-muted-foreground shrink-0 mt-1" />
                )}
              </div>
            )}

            {/* 知识建议 */}
            {digest.knowledge_recommendations && (() => {
              const rec = digest.knowledge_recommendations as {
                knowledge_gaps?: { concept: string; missing_prerequisites?: string[] }[];
                review_suggestions?: { concept: string; last_seen_days_ago?: number }[];
                related_concepts?: { concept: string; score?: number }[];
              };
              // 取 Top 3（缺口 1 + 复习 1 + 共现 1）
              const top3 = [
                ...(rec.knowledge_gaps || []).slice(0, 1).map((g) => ({
                  concept: g.concept,
                  reason: g.missing_prerequisites?.length
                    ? `缺少前置: ${g.missing_prerequisites.join("、")}`
                    : "建议补充相关前置知识",
                })),
                ...(rec.review_suggestions || []).slice(0, 1).map((r) => ({
                  concept: r.concept,
                  reason: r.last_seen_days_ago
                    ? `${r.last_seen_days_ago} 天未复习`
                    : "建议回顾巩固",
                })),
                ...(rec.related_concepts || []).slice(0, 1).map((c) => ({
                  concept: c.concept,
                  reason: "与已掌握概念关联",
                })),
              ];
              if (top3.length === 0) return null;
              return (
                <div className="space-y-1.5">
                  <div className="flex items-center gap-1.5">
                    <Lightbulb className="h-3.5 w-3.5 text-amber-500" />
                    <span className="text-xs font-medium text-muted-foreground">知识建议</span>
                  </div>
                  {top3.map((item, i) => (
                    <div key={i} className="flex items-center gap-2 pl-5">
                      <span className="text-xs font-medium">{item.concept}</span>
                      <span className="text-[10px] text-muted-foreground">— {item.reason}</span>
                    </div>
                  ))}
                </div>
              );
            })()}

            {/* 模式洞察 */}
            {digest.pattern_insights && digest.pattern_insights.length > 0 && (
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5">
                  <Eye className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-xs font-medium text-muted-foreground">洞察</span>
                </div>
                {digest.pattern_insights.map((insight, i) => (
                  <p key={i} className="text-xs text-muted-foreground pl-5">• {insight}</p>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
