import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Header } from "@/components/layout/Header";
import { ArrowLeft, Link2, X, CheckSquare, Square, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { useServiceUnavailable } from "@/hooks/useServiceUnavailable";
import { ServiceUnavailable } from "@/components/ServiceUnavailable";
import {
  getGoal,
  updateGoal,
  getGoalEntries,
  linkGoalEntry,
  unlinkGoalEntry,
  toggleChecklistItem,
  searchEntries,
  type Goal,
  type GoalEntry,
} from "@/services/api";

// === 进度环形图 ===
function ProgressRing({ percentage, size = 120 }: { percentage: number; size?: number }) {
  const strokeWidth = 8;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="transform -rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="currentColor" strokeWidth={strokeWidth} className="text-primary/20" />
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round" className="text-primary transition-all duration-500" />
      </svg>
      <span className="absolute text-2xl font-bold">{Math.round(percentage)}%</span>
    </div>
  );
}

// === 条目搜索弹窗 ===
function EntrySearchDialog({ open, onClose, onSelect }: {
  open: boolean;
  onClose: () => void;
  onSelect: (entryId: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<{ id: string; title: string; category: string }[]>([]);
  const [searching, setSearching] = useState(false);

  const doSearch = useCallback(async () => {
    if (!query.trim()) { setResults([]); return; }
    setSearching(true);
    try {
      const res = await searchEntries(query, 10);
      setResults(res.results.map(r => ({ id: r.id, title: r.title || r.id, category: r.category || "note" })));
    } catch {
      toast.error("搜索失败");
    } finally {
      setSearching(false);
    }
  }, [query]);

  useEffect(() => {
    const t = setTimeout(doSearch, 300);
    return () => clearTimeout(t);
  }, [query, doSearch]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="bg-card rounded-xl shadow-xl w-full max-w-md mx-4 max-h-[80vh] flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="p-4 border-b">
          <h3 className="font-medium mb-2">搜索条目关联</h3>
          <input className="w-full rounded-lg border px-3 py-2 text-sm" placeholder="输入关键词搜索..." autoFocus value={query} onChange={e => setQuery(e.target.value)} />
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {searching && <div className="text-center py-4 text-sm text-muted-foreground">搜索中...</div>}
          {!searching && results.length === 0 && query && <div className="text-center py-4 text-sm text-muted-foreground">无结果</div>}
          {results.map(r => (
            <div key={r.id} className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-accent cursor-pointer" onClick={() => { onSelect(r.id); onClose(); }}>
              <div className="min-w-0 flex-1">
                <p className="text-sm truncate">{r.title}</p>
                <p className="text-xs text-muted-foreground">{r.category}</p>
              </div>
              <Link2 className="h-4 w-4 text-muted-foreground shrink-0 ml-2" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// === 主页面 ===
export function GoalDetail() {
  const { id: goalId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [goal, setGoal] = useState<Goal | null>(null);
  const [entries, setEntries] = useState<GoalEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [showSearch, setShowSearch] = useState(false);
  const { serviceUnavailable, runWith503, retry: retryService } = useServiceUnavailable();

  const fetchData = useCallback(async () => {
    if (!goalId) return;
    try {
      await runWith503(async () => {
        const [goalRes, entriesRes] = await Promise.all([
          getGoal(goalId),
          getGoalEntries(goalId).catch(() => ({ entries: [] })),
        ]);
        setGoal(goalRes);
        setEntries(entriesRes.entries ?? []);
      });
    } catch {
      toast.error("加载目标失败");
    } finally {
      setLoading(false);
    }
  }, [goalId, runWith503]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleLink = async (entryId: string) => {
    if (!goalId) return;
    try {
      await linkGoalEntry(goalId, entryId);
      toast.success("已关联");
      fetchData();
    } catch (e: any) {
      toast.error(e.message || "关联失败");
    }
  };

  const handleUnlink = async (entryId: string) => {
    if (!goalId) return;
    try {
      await unlinkGoalEntry(goalId, entryId);
      toast.success("已取消关联");
      fetchData();
    } catch (e: any) {
      toast.error(e.message || "取消关联失败");
    }
  };

  const handleToggleChecklist = async (itemId: string) => {
    if (!goalId) return;
    try {
      const updated = await toggleChecklistItem(goalId, itemId);
      setGoal(updated);
    } catch (e: any) {
      toast.error(e.message || "操作失败");
    }
  };

  const handleReactivate = async () => {
    if (!goalId) return;
    try {
      const updated = await updateGoal(goalId, { status: "active" });
      setGoal(updated);
      toast.success("已重新激活");
    } catch (e: any) {
      toast.error(e.message || "操作失败");
    }
  };

  const handleArchive = async () => {
    if (!goalId) return;
    try {
      await updateGoal(goalId, { status: "abandoned" });
      navigate("/goals");
    } catch (e: any) {
      toast.error(e.message || "归档失败");
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64 text-muted-foreground">加载中...</div>;
  if (serviceUnavailable) return (
    <div className="flex-1">
      <Header title="目标详情" />
      <main className="p-6">
        <ServiceUnavailable onRetry={() => retryService(fetchData)} />
      </main>
    </div>
  );
  if (!goal) return <div className="text-center py-12 text-muted-foreground">目标不存在</div>;

  const metricLabel = goal.metric_type === "count" ? "手动计数" : goal.metric_type === "checklist" ? "检查清单" : "Tag 追踪";

  return (
    <>
      <Header title="目标详情" />
      <main className="flex-1 p-6 pb-32">
        {/* 返回按钮 */}
        <button className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4" onClick={() => navigate("/goals")}>
          <ArrowLeft className="h-4 w-4" /> 返回目标列表
        </button>

        {/* 顶部概览 */}
        <Card className="mb-4">
          <CardContent className="p-6">
            <div className="flex flex-col sm:flex-row items-center gap-6">
              <ProgressRing percentage={goal.progress_percentage} />
              <div className="flex-1 text-center sm:text-left">
                <h2 className="text-xl font-semibold">{goal.title}</h2>
                {goal.description && <p className="text-sm text-muted-foreground mt-1">{goal.description}</p>}
                <div className="flex flex-wrap items-center gap-2 mt-3">
                  <Badge variant="secondary">{metricLabel}</Badge>
                  <Badge variant={goal.status === "active" ? "default" : goal.status === "completed" ? "success" : "outline"}>
                    {goal.status === "active" ? "进行中" : goal.status === "completed" ? "已完成" : "已归档"}
                  </Badge>
                  {goal.end_date && (
                    <span className="text-xs text-muted-foreground">截止 {goal.end_date}</span>
                  )}
                </div>
                <div className="mt-3">
                  <Progress value={goal.progress_percentage} className="h-2" />
                  <p className="text-xs text-muted-foreground mt-1">{goal.current_value} / {goal.target_value}</p>
                </div>
                <div className="flex gap-2 mt-3">
                  {goal.status === "active" && (
                    <Button variant="outline" size="sm" onClick={handleArchive}>归档</Button>
                  )}
                  {goal.status === "completed" && (
                    <Button variant="outline" size="sm" onClick={handleReactivate}>
                      <RefreshCw className="h-3.5 w-3.5 mr-1" /> 重新激活
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* count 类型：关联条目 */}
        {goal.metric_type === "count" && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">关联条目 ({entries.length})</CardTitle>
              <Button variant="outline" size="sm" onClick={() => setShowSearch(true)}>
                <Link2 className="h-4 w-4 mr-1" /> 关联条目
              </Button>
            </CardHeader>
            <CardContent>
              {entries.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">暂无关联条目，点击上方按钮关联</p>
              ) : (
                <div className="space-y-2">
                  {entries.map(entry => (
                    <div key={entry.id} className="flex items-center justify-between p-3 rounded-lg border">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium truncate">{entry.entry?.title || entry.entry_id}</p>
                        <p className="text-xs text-muted-foreground">{entry.entry?.category} · {entry.entry?.status}</p>
                      </div>
                      <button className="text-muted-foreground hover:text-destructive p-1 shrink-0 ml-2" onClick={() => handleUnlink(entry.entry_id)} title="取消关联">
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* checklist 类型：检查项 */}
        {goal.metric_type === "checklist" && goal.checklist_items && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">检查清单</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {goal.checklist_items.map(item => (
                  <div key={item.id} className="flex items-center gap-3 p-3 rounded-lg border cursor-pointer hover:bg-accent" onClick={() => handleToggleChecklist(item.id)}>
                    {item.checked ? (
                      <CheckSquare className="h-5 w-5 text-primary shrink-0" />
                    ) : (
                      <Square className="h-5 w-5 text-muted-foreground shrink-0" />
                    )}
                    <span className={`text-sm ${item.checked ? "line-through text-muted-foreground" : ""}`}>{item.title}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* tag_auto 类型：匹配信息 */}
        {goal.metric_type === "tag_auto" && goal.auto_tags && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">自动追踪标签</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {goal.auto_tags.map(tag => (
                  <Badge key={tag} variant="secondary">{tag}</Badge>
                ))}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                自动统计包含以上标签的条目数量作为进度
              </p>
            </CardContent>
          </Card>
        )}

        {/* tag_auto 类型：匹配条目列表 */}
        {goal.metric_type === "tag_auto" && (
          <Card className="mt-4">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">匹配条目 ({entries.length})</CardTitle>
            </CardHeader>
            <CardContent>
              {entries.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">
                  暂无匹配条目，创建带有对应标签的条目后会自动计入
                </p>
              ) : (
                <div className="space-y-2">
                  {entries.map(entry => (
                    <div key={entry.id} className="flex items-center justify-between p-3 rounded-lg border">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium truncate">{entry.entry?.title || entry.entry_id}</p>
                        <p className="text-xs text-muted-foreground">{entry.entry?.category} · {entry.entry?.status}</p>
                      </div>
                      <Badge variant="secondary" className="shrink-0 ml-2 text-xs">自动匹配</Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        <EntrySearchDialog open={showSearch} onClose={() => setShowSearch(false)} onSelect={handleLink} />
      </main>
    </>
  );
}
