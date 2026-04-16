import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Header } from "@/components/layout/Header";
import { Plus, Target, Calendar, Archive, CheckCircle2, ListChecks, Tag } from "lucide-react";
import { toast } from "sonner";
import {
  getGoals,
  createGoal,
  updateGoal,
  type Goal,
  type MetricType,
} from "@/services/api";
import { getKnowledgeSearch } from "@/services/api";

// === 度量类型配置 ===
const metricTypeConfig: Record<MetricType, { label: string; icon: typeof Target; color: string }> = {
  count: { label: "手动计数", icon: Target, color: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300" },
  checklist: { label: "检查清单", icon: ListChecks, color: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300" },
  tag_auto: { label: "Tag 追踪", icon: Tag, color: "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300" },
};

// === 创建弹窗 ===
function CreateGoalDialog({ open, onClose, onCreated }: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [metricType, setMetricType] = useState<MetricType>("count");
  const [targetValue, setTargetValue] = useState(5);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [checklistItems, setChecklistItems] = useState<string[]>([""]);
  const [autoTags, setAutoTags] = useState<string[]>([]);
  const [tagSearch, setTagSearch] = useState("");
  const [tagResults, setTagResults] = useState<{ name: string }[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const searchTags = useCallback(async (q: string) => {
    if (!q.trim()) { setTagResults([]); return; }
    try {
      const res = await getKnowledgeSearch(q, 5);
      setTagResults(res.items.map(i => ({ name: i.name })));
    } catch {
      setTagResults([]);
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => searchTags(tagSearch), 300);
    return () => clearTimeout(t);
  }, [tagSearch, searchTags]);

  if (!open) return null;

  const handleSubmit = async () => {
    if (!title.trim()) { toast.error("请输入目标标题"); return; }
    if (targetValue <= 0) { toast.error("目标值必须大于 0"); return; }
    if (metricType === "checklist") {
      const validItems = checklistItems.filter(i => i.trim());
      if (validItems.length === 0) { toast.error("请添加至少一个检查项"); return; }
    }
    if (metricType === "tag_auto" && autoTags.length === 0) {
      toast.error("请选择至少一个标签");
      return;
    }

    setSubmitting(true);
    try {
      await createGoal({
        title: title.trim(),
        description: description.trim() || undefined,
        metric_type: metricType,
        target_value: metricType === "checklist" ? checklistItems.filter(i => i.trim()).length : targetValue,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        auto_tags: metricType === "tag_auto" ? autoTags : undefined,
        checklist_items: metricType === "checklist" ? checklistItems.filter(i => i.trim()) : undefined,
      });
      toast.success("目标创建成功");
      onCreated();
      // reset
      setTitle(""); setDescription(""); setMetricType("count"); setTargetValue(5);
      setStartDate(""); setEndDate(""); setChecklistItems([""]); setAutoTags([]); setTagSearch("");
      onClose();
    } catch (e: any) {
      toast.error(e.message || "创建失败");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="bg-card rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="p-6">
          <h2 className="text-lg font-semibold mb-4">创建目标</h2>

          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">标题 *</label>
              <input className="w-full mt-1 rounded-lg border px-3 py-2 text-sm" placeholder="如：完成 React 学习" value={title} onChange={e => setTitle(e.target.value)} />
            </div>

            <div>
              <label className="text-sm font-medium">描述</label>
              <textarea className="w-full mt-1 rounded-lg border px-3 py-2 text-sm" rows={2} placeholder="可选" value={description} onChange={e => setDescription(e.target.value)} />
            </div>

            <div>
              <label className="text-sm font-medium">衡量方式</label>
              <div className="flex gap-2 mt-1">
                {(["count", "checklist", "tag_auto"] as MetricType[]).map(t => (
                  <Badge key={t} variant={metricType === t ? "default" : "outline"} className="cursor-pointer" onClick={() => setMetricType(t)}>
                    {metricTypeConfig[t].label}
                  </Badge>
                ))}
              </div>
            </div>

            {metricType !== "checklist" && (
              <div>
                <label className="text-sm font-medium">目标值</label>
                <input type="number" className="w-full mt-1 rounded-lg border px-3 py-2 text-sm" min={1} value={targetValue} onChange={e => setTargetValue(Number(e.target.value))} />
              </div>
            )}

            {metricType === "checklist" && (
              <div>
                <label className="text-sm font-medium">检查项</label>
                <div className="space-y-2 mt-1">
                  {checklistItems.map((item, i) => (
                    <div key={i} className="flex gap-2">
                      <input className="flex-1 rounded-lg border px-3 py-2 text-sm" placeholder={`检查项 ${i + 1}`} value={item} onChange={e => {
                        const next = [...checklistItems]; next[i] = e.target.value; setChecklistItems(next);
                      }} />
                      <Button variant="ghost" size="sm" onClick={() => setChecklistItems(checklistItems.filter((_, j) => j !== i))}>X</Button>
                    </div>
                  ))}
                  <Button variant="outline" size="sm" onClick={() => setChecklistItems([...checklistItems, ""])}>+ 添加检查项</Button>
                </div>
                <p className="text-xs text-muted-foreground mt-1">目标值将设为 {checklistItems.filter(i => i.trim()).length}</p>
              </div>
            )}

            {metricType === "tag_auto" && (
              <div>
                <label className="text-sm font-medium">追踪标签</label>
                <div className="flex flex-wrap gap-1 mt-1 mb-2">
                  {autoTags.map(tag => (
                    <Badge key={tag} variant="secondary" className="cursor-pointer" onClick={() => setAutoTags(autoTags.filter(t => t !== tag))}>{tag} x</Badge>
                  ))}
                </div>
                <input className="w-full rounded-lg border px-3 py-2 text-sm" placeholder="搜索标签..." value={tagSearch} onChange={e => setTagSearch(e.target.value)} />
                {tagResults.length > 0 && (
                  <div className="mt-1 border rounded-lg overflow-hidden">
                    {tagResults.filter(r => !autoTags.includes(r.name)).slice(0, 5).map(r => (
                      <div key={r.name} className="px-3 py-2 text-sm hover:bg-accent cursor-pointer" onClick={() => {
                        setAutoTags([...autoTags, r.name]); setTagSearch(""); setTagResults([]);
                      }}>{r.name}</div>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium">开始日期</label>
                <input type="date" className="w-full mt-1 rounded-lg border px-3 py-2 text-sm" value={startDate} onChange={e => setStartDate(e.target.value)} />
              </div>
              <div>
                <label className="text-sm font-medium">截止日期</label>
                <input type="date" className="w-full mt-1 rounded-lg border px-3 py-2 text-sm" value={endDate} onChange={e => setEndDate(e.target.value)} />
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 mt-6">
            <Button variant="outline" onClick={onClose}>取消</Button>
            <Button onClick={handleSubmit} disabled={submitting}>{submitting ? "创建中..." : "创建"}</Button>
          </div>
        </div>
      </div>
    </div>
  );
}

// === 进度环形图 ===
function ProgressRing({ percentage, size = 80 }: { percentage: number; size?: number }) {
  const strokeWidth = 6;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;

  return (
    <svg width={size} height={size} className="transform -rotate-90">
      <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="currentColor" strokeWidth={strokeWidth} className="text-primary/20" />
      <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round" className="text-primary transition-all duration-500" />
    </svg>
  );
}

// === 主页面 ===
export function GoalsPage() {
  const navigate = useNavigate();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [statusFilter, setStatusFilter] = useState<"active" | "completed" | "abandoned">("active");

  const fetchGoals = useCallback(async () => {
    try {
      const res = await getGoals(statusFilter);
      setGoals(res.goals ?? []);
    } catch {
      toast.error("加载目标失败");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { fetchGoals(); }, [fetchGoals]);

  const handleArchive = async (goal: Goal) => {
    try {
      await updateGoal(goal.id, { status: "abandoned" });
      toast.success("已归档");
      fetchGoals();
    } catch (e: any) {
      toast.error(e.message || "操作失败");
    }
  };

  const sortedGoals = [...goals].sort((a, b) => b.progress_percentage - a.progress_percentage);

  return (
    <>
      <Header title="目标追踪" />
      <main className="flex-1 p-6 pb-32">
        <div className="flex items-center justify-between mb-4">
          <div className="flex gap-2">
            {(["active", "completed", "abandoned"] as const).map(s => (
              <Badge key={s} variant={statusFilter === s ? "default" : "outline"} className="cursor-pointer" onClick={() => setStatusFilter(s)}>
                {s === "active" ? "进行中" : s === "completed" ? "已完成" : "已归档"}
              </Badge>
            ))}
          </div>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="h-4 w-4 mr-1" /> 新建
          </Button>
        </div>

        {loading ? (
          <div className="text-center py-8 text-muted-foreground">加载中...</div>
        ) : sortedGoals.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Target className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
              <p className="text-muted-foreground">
                {statusFilter === "active" ? "设定一个目标开始追踪吧" : "暂无目标"}
              </p>
              {statusFilter === "active" && (
                <Button variant="outline" className="mt-3" onClick={() => setShowCreate(true)}>
                  <Plus className="h-4 w-4 mr-1" /> 创建第一个目标
                </Button>
              )}
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {sortedGoals.map(goal => {
              const cfg = metricTypeConfig[goal.metric_type];
              return (
                <Card key={goal.id} className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate(`/goals/${goal.id}`)}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium truncate">{goal.title}</h3>
                        {goal.description && (
                          <p className="text-xs text-muted-foreground truncate mt-0.5">{goal.description}</p>
                        )}
                      </div>
                      <div className="relative ml-3 shrink-0">
                        <ProgressRing percentage={goal.progress_percentage} size={48} />
                        <span className="absolute inset-0 flex items-center justify-center text-xs font-medium">
                          {Math.round(goal.progress_percentage)}%
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="secondary" className={`text-xs ${cfg.color}`}>
                        {cfg.label}
                      </Badge>
                      {goal.end_date && (
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <Calendar className="h-3 w-3" /> {goal.end_date}
                        </span>
                      )}
                    </div>

                    <Progress value={goal.progress_percentage} className="h-1.5" />

                    <div className="flex items-center justify-between mt-2">
                      <span className="text-xs text-muted-foreground">
                        {goal.current_value} / {goal.target_value}
                      </span>
                      {statusFilter === "active" && (
                        <button
                          className="text-xs text-muted-foreground hover:text-foreground p-1"
                          onClick={e => { e.stopPropagation(); handleArchive(goal); }}
                          title="归档"
                        >
                          <Archive className="h-3.5 w-3.5" />
                        </button>
                      )}
                      {statusFilter === "completed" && (
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        <CreateGoalDialog open={showCreate} onClose={() => setShowCreate(false)} onCreated={fetchGoals} />
      </main>
    </>
  );
}
