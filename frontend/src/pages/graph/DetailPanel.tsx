import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { X, Loader2, Clock, FileText } from "lucide-react";
import {
  getConceptTimeline,
  type MapNode,
  type ConceptStatsResponse,
  type ConceptTimelineResponse,
} from "@/services/api";
import { masteryColors, masteryLabels, masterySuggestions } from "./constants";

// === 详情面板内容 ===
function DetailPanelContent({
  node,
  stats,
  timeline,
  timelineLoading,
  timelineError,
}: {
  node: MapNode;
  stats: ConceptStatsResponse | null;
  timeline: ConceptTimelineResponse | null;
  timelineLoading: boolean;
  timelineError: string | null;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span
          className="inline-block w-3 h-3 rounded-full"
          style={{ backgroundColor: masteryColors[node.mastery] }}
        />
        <span className="text-sm">{masteryLabels[node.mastery] || node.mastery}</span>
      </div>

      {node.category && (
        <div>
          <span className="text-xs text-muted-foreground">分类：</span>
          <span className="text-sm ml-1">{node.category}</span>
        </div>
      )}

      <div>
        <span className="text-xs text-muted-foreground">关联条目：</span>
        <span className="text-sm ml-1">{node.entry_count} 条</span>
      </div>

      <div className="pt-2 border-t">
        <p className="text-sm text-muted-foreground leading-relaxed">
          {masterySuggestions[node.mastery] || "继续学习这个概念。"}
        </p>
      </div>

      {/* 学习时间线 */}
      <div className="pt-2 border-t space-y-2">
        <div className="flex items-center gap-1.5">
          <Clock className="h-3.5 w-3.5 text-muted-foreground" />
          <p className="text-xs font-medium text-muted-foreground">学习时间线</p>
        </div>

        {timelineLoading && (
          <div className="flex items-center gap-2 py-2">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            <span className="text-xs text-muted-foreground">加载中...</span>
          </div>
        )}

        {timelineError && (
          <p className="text-xs text-destructive">{timelineError}</p>
        )}

        {timeline && timeline.items.length === 0 && !timelineLoading && (
          <p className="text-xs text-muted-foreground">暂无学习记录</p>
        )}

        {timeline && timeline.items.length > 0 && (
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {timeline.items.map((day) => (
              <div key={day.date} className="space-y-1">
                <p className="text-[10px] font-medium text-muted-foreground">{day.date}</p>
                {day.entries.map((entry) => (
                  <Link
                    key={entry.id}
                    to={`/entries/${entry.id}`}
                    className="flex items-center gap-1.5 px-2 py-1 rounded text-xs hover:bg-accent transition-colors"
                  >
                    <FileText className="h-3 w-3 text-muted-foreground shrink-0" />
                    <span className="truncate">{entry.title}</span>
                  </Link>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>

      {stats && (
        <div className="pt-4 border-t space-y-2">
          <p className="text-xs font-medium text-muted-foreground">图谱统计</p>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <p className="text-lg font-semibold">{stats.concept_count}</p>
              <p className="text-xs text-muted-foreground">概念</p>
            </div>
            <div>
              <p className="text-lg font-semibold">{stats.relation_count}</p>
              <p className="text-xs text-muted-foreground">关系</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// === 详情面板 ===
export function DetailPanel({
  node,
  stats,
  onClose,
}: {
  node: MapNode;
  stats: ConceptStatsResponse | null;
  onClose: () => void;
}) {
  // 时间线状态
  const [timeline, setTimeline] = useState<ConceptTimelineResponse | null>(null);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [timelineError, setTimelineError] = useState<string | null>(null);

  useEffect(() => {
    if (!node.name) return;
    let cancelled = false;
    setTimelineLoading(true);
    setTimelineError(null);
    getConceptTimeline(node.name, 30)
      .then((data) => {
        if (!cancelled) setTimeline(data);
      })
      .catch((err: any) => {
        if (!cancelled) setTimelineError(err.message || "加载时间线失败");
      })
      .finally(() => {
        if (!cancelled) setTimelineLoading(false);
      });
    return () => { cancelled = true; };
  }, [node.name]);

  return (
    <>
      {/* 移动端：底部抽屉 */}
      <div className="fixed inset-0 bg-black/50 z-40 md:hidden" onClick={onClose} />
      <div className="fixed bottom-0 left-0 right-0 bg-card border-t rounded-t-xl p-4 z-50 md:hidden max-h-[50vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-base truncate">{node.name}</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>
        <DetailPanelContent node={node} stats={stats} timeline={timeline} timelineLoading={timelineLoading} timelineError={timelineError} />
      </div>

      {/* 桌面端：右侧面板 */}
      <div className="hidden md:flex w-80 border-l bg-card p-4 flex-col gap-4 overflow-y-auto">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-base truncate">{node.name}</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>
        <DetailPanelContent node={node} stats={stats} timeline={timeline} timelineLoading={timelineLoading} timelineError={timelineError} />
      </div>
    </>
  );
}
