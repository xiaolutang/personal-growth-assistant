import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useMorningDigest } from "@/hooks/useMorningDigest";
import {
  Sparkles, ChevronDown, ChevronUp,
  Clock, AlertTriangle, Inbox, BookOpen, Flame, Target, Eye, ArrowRight, Lightbulb,
} from "lucide-react";
import type { MorningDigestResponse } from "@/services/api";
import { DigestStat } from "@/components/review/DigestStat";

// ====== "review" 变体（Review 页面使用，内部获取数据） ======

interface ReviewProps {
  variant: "review";
  visible: boolean;
}

// ====== "home" 变体（首页使用，外部传入数据） ======

interface HomeProps {
  variant: "home";
  digest: MorningDigestResponse | null;
  digestLoading: boolean;
  digestError: string | null;
  onDismiss: () => void;
  onNavigateToEntry: (entryId: string) => void;
}

type MorningDigestCardProps = ReviewProps | HomeProps;

export function MorningDigestCard(props: MorningDigestCardProps) {
  if (props.variant === "review") {
    return <ReviewVariant {...props} />;
  }
  return <HomeVariant {...props} />;
}

// ====== Review 变体 ======

function ReviewVariant({ visible }: { visible: boolean }) {
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

// ====== Home 变体 ======

function HomeVariant({
  digest,
  digestLoading,
  digestError,
  onDismiss,
  onNavigateToEntry,
}: {
  digest: MorningDigestResponse | null;
  digestLoading: boolean;
  digestError: string | null;
  onDismiss: () => void;
  onNavigateToEntry: (entryId: string) => void;
}) {
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

export { MorningDigestCard as default };
