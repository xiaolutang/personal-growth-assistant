import { useState, useEffect, useMemo } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getActivityHeatmap, type ActivityHeatmapItem } from "@/services/api";
import { useNavigate } from "react-router-dom";

const LEVELS = [
  "bg-muted",
  "bg-primary/20 dark:bg-primary/30",
  "bg-primary/40 dark:bg-primary/50",
  "bg-primary/60 dark:bg-primary/70",
  "bg-primary dark:bg-primary",
];

function getCountLevel(count: number): number {
  if (count === 0) return 0;
  if (count <= 2) return 1;
  if (count <= 5) return 2;
  if (count <= 8) return 3;
  return 4;
}

const MONTH_LABELS = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"];
const DAY_LABELS = ["", "一", "", "三", "", "五", ""];

export function ActivityHeatmap() {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const [items, setItems] = useState<ActivityHeatmapItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [hovered, setHovered] = useState<{ date: string; count: number } | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    getActivityHeatmap(year)
      .then((res) => setItems(res.items))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [year]);

  const dateMap = useMemo(() => {
    const m = new Map<string, number>();
    for (const item of items) m.set(item.date, item.count);
    return m;
  }, [items]);

  // 按周构建网格
  const weeks = useMemo(() => {
    const start = new Date(year, 0, 1);
    // 对齐到周日开始
    const dayOfWeek = start.getDay();
    const gridStart = new Date(start);
    gridStart.setDate(gridStart.getDate() - dayOfWeek);

    const result: { date: string; count: number; inYear: boolean }[][] = [];
    const current = new Date(gridStart);

    while (current.getFullYear() <= year) {
      const week: { date: string; count: number; inYear: boolean }[] = [];
      for (let d = 0; d < 7; d++) {
        const dateStr = `${current.getFullYear()}-${String(current.getMonth() + 1).padStart(2, "0")}-${String(current.getDate()).padStart(2, "0")}`;
        week.push({
          date: dateStr,
          count: dateMap.get(dateStr) || 0,
          inYear: current.getFullYear() === year,
        });
        current.setDate(current.getDate() + 1);
      }
      result.push(week);
    }
    return result;
  }, [year, dateMap]);

  // 月份标签位置
  const monthPositions = useMemo(() => {
    const positions: { label: string; col: number }[] = [];
    let lastMonth = -1;
    weeks.forEach((week, i) => {
      const firstDay = week.find((d) => d.inYear);
      if (firstDay) {
        const m = new Date(firstDay.date).getMonth();
        if (m !== lastMonth) {
          positions.push({ label: MONTH_LABELS[m], col: i });
          lastMonth = m;
        }
      }
    });
    return positions;
  }, [weeks]);

  function handleClick(date: string) {
    navigate(`/explore?start_date=${date}&end_date=${date}`);
  }

  const { totalActivity, activeDays } = useMemo(() => ({
    totalActivity: items.reduce((s, i) => s + i.count, 0),
    activeDays: items.filter((i) => i.count > 0).length,
  }), [items]);

  return (
    <div className="rounded-xl border bg-card p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold">活动热力图</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            {year} 年 · {activeDays} 天活跃 · {totalActivity} 条记录
          </p>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setYear(year - 1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm font-medium w-12 text-center">{year}</span>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setYear(Math.min(year + 1, currentYear))}
            disabled={year >= currentYear}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="text-sm text-muted-foreground py-8 text-center">加载中...</div>
      ) : (
        <div className="relative overflow-x-auto">
          {/* 月份标签 */}
          <div className="flex mb-1" style={{ paddingLeft: "20px" }}>
            {monthPositions.map((m, i) => (
              <span
                key={i}
                className="text-[10px] text-muted-foreground"
                style={{
                  position: "relative",
                  left: `${(m.col - (i > 0 ? monthPositions[i - 1].col : 0)) * 13}px`,
                }}
              >
                {m.label}
              </span>
            ))}
          </div>
          <div className="flex">
            {/* 日标签 */}
            <div className="flex flex-col mr-1">
              {DAY_LABELS.map((label, i) => (
                <div key={i} className="h-[13px] flex items-center">
                  <span className="text-[10px] text-muted-foreground w-4 text-right">{label}</span>
                </div>
              ))}
            </div>
            {/* 热力格子 */}
            <div className="flex gap-[2px] relative">
              {weeks.map((week, wi) => (
                <div key={wi} className="flex flex-col gap-[2px]">
                  {week.map((day, di) => (
                    <div
                      key={di}
                      className={`w-[11px] h-[11px] rounded-[2px] cursor-pointer transition-colors ${day.inYear ? LEVELS[getCountLevel(day.count)] : "bg-transparent"}`}
                      onMouseEnter={() => day.inYear && setHovered({ date: day.date, count: day.count })}
                      onMouseLeave={() => setHovered(null)}
                      onClick={() => day.inYear && day.count > 0 && handleClick(day.date)}
                    />
                  ))}
                </div>
              ))}
              {/* Tooltip */}
              {hovered && (
                <div
                  className="absolute bottom-full mb-2 bg-popover text-popover-foreground text-xs rounded px-2 py-1 shadow-md border pointer-events-none whitespace-nowrap z-10"
                  style={{ left: "50%", transform: "translateX(-50%)" }}
                >
                  {hovered.date} · {hovered.count} 条记录
                </div>
              )}
            </div>
          </div>
          {/* 图例 */}
          <div className="flex items-center justify-end gap-1 mt-2 text-[10px] text-muted-foreground">
            <span>少</span>
            {LEVELS.map((_, i) => (
              <div key={i} className={`w-[11px] h-[11px] rounded-[2px] ${LEVELS[i]}`} />
            ))}
            <span>多</span>
          </div>
        </div>
      )}
    </div>
  );
}
