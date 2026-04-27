import { useState, useEffect, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { getMilestones, type Goal, type Milestone } from "@/services/api";
import { GoalTimelineBar } from "./GoalTimelineBar";

interface TimelineViewProps {
  goals: Goal[];
}

/** Minimum range = 30 days in ms */
const MIN_RANGE_MS = 30 * 24 * 60 * 60 * 1000;

function parseDate(dateStr: string): number {
  return new Date(dateStr + "T00:00:00").getTime();
}

export function TimelineView({ goals }: TimelineViewProps) {
  const navigate = useNavigate();
  const [milestonesMap, setMilestonesMap] = useState<Record<string, Milestone[]>>({});
  const [loading, setLoading] = useState(true);

  const goalsIdKey = goals.map(g => g.id).join(',');
  const fetchMilestones = useCallback(async () => {
    const map: Record<string, Milestone[]> = {};
    await Promise.all(
      goals.map(async (g) => {
        try {
          const res = await getMilestones(g.id);
          map[g.id] = res.milestones ?? [];
        } catch {
          map[g.id] = [];
        }
      }),
    );
    setMilestonesMap(map);
    setLoading(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps -- goalsIdKey 是 goals id 的稳定序列化，避免 goals 引用变化导致无限重取
  }, [goalsIdKey]);

  useEffect(() => {
    if (goals.length === 0) {
      setLoading(false);
      return;
    }
    fetchMilestones();
  }, [fetchMilestones, goals.length]);

  // Compute time range
  const { rangeStart, rangeEnd, totalRange, monthMarkers } = useMemo(() => {
    const now = Date.now();
    let start = Infinity;
    let end = -Infinity;

    for (const g of goals) {
      const s = g.start_date ? parseDate(g.start_date) : parseDate(g.created_at.slice(0, 10));
      const e = g.end_date ? parseDate(g.end_date) : now;
      if (s < start) start = s;
      if (e > end) end = e;
    }

    // Also consider milestone due_dates
    for (const g of goals) {
      const ms = milestonesMap[g.id] ?? [];
      for (const m of ms) {
        if (m.due_date) {
          const d = parseDate(m.due_date);
          if (d < start) start = d;
          if (d > end) end = d;
        }
      }
    }

    // Fallback if no goals
    if (start === Infinity) {
      start = now - 15 * 24 * 60 * 60 * 1000;
      end = now + 15 * 24 * 60 * 60 * 1000;
    }

    // Add 5% padding on each side
    const rawRange = end - start;
    const padding = rawRange * 0.05;
    start -= padding;
    end += padding;

    // Enforce minimum range
    let total = end - start;
    if (total < MIN_RANGE_MS) {
      const diff = (MIN_RANGE_MS - total) / 2;
      start -= diff;
      end += diff;
      total = MIN_RANGE_MS;
    }

    // Generate month markers
    const markers: { pct: number; label: string; key: string }[] = [];
    const d = new Date(start);
    d.setDate(1);
    d.setHours(0, 0, 0, 0);
    // Move to first of each month
    while (d.getTime() < start) {
      d.setMonth(d.getMonth() + 1);
    }
    while (d.getTime() <= end) {
      const pct = ((d.getTime() - start) / total) * 100;
      markers.push({
        pct,
        label: `${d.getMonth() + 1}月`,
        key: `${d.getFullYear()}-${d.getMonth() + 1}`,
      });
      d.setMonth(d.getMonth() + 1);
    }

    return { rangeStart: start, rangeEnd: end, totalRange: total, monthMarkers: markers };
  }, [goals, milestonesMap]);

  // Today line position
  const todayPct = useMemo(() => {
    return ((Date.now() - rangeStart) / totalRange) * 100;
  }, [rangeStart, totalRange]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-5 w-5 animate-spin mr-2" />
        <span className="text-sm text-muted-foreground">加载时间线...</span>
      </div>
    );
  }

  if (goals.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        暂无目标数据
      </div>
    );
  }

  return (
    <div className="w-full overflow-x-auto">
      <div className="min-w-[600px]">
        {/* Month header */}
        <div className="flex items-center h-8 ml-40 relative">
          {monthMarkers.map((m) => (
            <span
              key={m.key}
              className="absolute text-xs text-muted-foreground"
              style={{ left: `${m.pct}%`, transform: "translateX(-50%)" }}
            >
              {m.label}
            </span>
          ))}
        </div>

        {/* Goal rows */}
        <div className="relative">
          {/* Today line */}
          {todayPct >= 0 && todayPct <= 100 && (
            <div
              className="absolute top-0 bottom-0 z-10 pointer-events-none"
              style={{
                left: `calc(10rem + ${todayPct}% * (100% - 10rem) / 100%)`,
              }}
            >
              <div className="w-0.5 h-full bg-red-500 opacity-60" />
            </div>
          )}

          {goals.map((goal) => (
            <GoalTimelineBar
              key={goal.id}
              goal={goal}
              milestones={milestonesMap[goal.id] ?? []}
              rangeStart={rangeStart}
              rangeEnd={rangeEnd}
              totalRange={totalRange}
              onClick={() => navigate(`/goals/${goal.id}`)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
