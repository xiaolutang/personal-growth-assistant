import { useState } from "react";
import type { Goal, Milestone } from "@/services/api";

interface GoalTimelineBarProps {
  goal: Goal;
  milestones: Milestone[];
  rangeStart: number; // ms timestamp
  rangeEnd: number;   // ms timestamp
  totalRange: number;  // rangeEnd - rangeStart in ms
  onClick: () => void;
}

const statusColors: Record<string, string> = {
  active: "#6366F1",
  completed: "#22C55E",
  abandoned: "#94A3B8",
};

function dateToPercent(dateStr: string, rangeStart: number, totalRange: number): number {
  const d = new Date(dateStr + "T00:00:00").getTime();
  return ((d - rangeStart) / totalRange) * 100;
}

export function GoalTimelineBar({
  goal,
  milestones,
  rangeStart,
  totalRange,
  onClick,
}: GoalTimelineBarProps) {
  const [hovered, setHovered] = useState<string | null>(null);

  const barColor = statusColors[goal.status] || statusColors.active;

  // Fallback: if no dates, use created_at as start, now as end
  const startDate = goal.start_date || goal.created_at.slice(0, 10);
  const endDate = goal.end_date || new Date().toISOString().slice(0, 10);

  const leftPct = Math.max(0, dateToPercent(startDate, rangeStart, totalRange));
  const rightPct = Math.min(100, dateToPercent(endDate, rangeStart, totalRange));
  const widthPct = Math.max(0.5, rightPct - leftPct); // min 0.5% so it's visible

  return (
    <div className="flex items-center h-12 group">
      {/* Goal name */}
      <div
        className="w-40 shrink-0 pr-3 text-sm truncate cursor-pointer hover:text-primary transition-colors"
        onClick={onClick}
        title={goal.title}
      >
        {goal.title}
      </div>

      {/* Timeline track */}
      <div className="flex-1 relative h-full flex items-center">
        {/* Bar background track */}
        <div className="absolute inset-x-0 h-2 top-1/2 -translate-y-1/2 bg-muted rounded-full" />

        {/* Goal bar */}
        <div
          className="absolute h-5 rounded-md cursor-pointer transition-opacity hover:opacity-80"
          style={{
            left: `${leftPct}%`,
            width: `${widthPct}%`,
            backgroundColor: barColor,
            opacity: goal.status === "abandoned" ? 0.4 : 0.7,
          }}
          onClick={onClick}
          onMouseEnter={() => setHovered("goal")}
          onMouseLeave={() => setHovered(null)}
        >
          {/* Progress fill inside bar */}
          <div
            className="absolute inset-y-0 left-0 rounded-md"
            style={{
              width: `${goal.progress_percentage}%`,
              backgroundColor: barColor,
              opacity: goal.status === "abandoned" ? 0.5 : 1,
            }}
          />
        </div>

        {/* Milestone diamonds */}
        {milestones
          .filter((m) => m.due_date)
          .map((ms) => {
            const pct = dateToPercent(ms.due_date!, rangeStart, totalRange);
            if (pct < 0 || pct > 100) return null;
            const isCompleted = ms.status === "completed";
            return (
              <div
                key={ms.id}
                className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 z-10 cursor-pointer"
                style={{ left: `${pct}%` }}
                onMouseEnter={() => setHovered(`ms-${ms.id}`)}
                onMouseLeave={() => setHovered(null)}
              >
                {/* Diamond shape via CSS */}
                <div
                  className="w-3.5 h-3.5 rotate-45 border-2 border-white shadow-sm"
                  style={{
                    backgroundColor: isCompleted ? "#22C55E" : "#F59E0B",
                  }}
                />
              </div>
            );
          })}

        {/* Tooltip */}
        {hovered && (
          <div
            className="absolute z-20 bg-popover text-popover-foreground border rounded-lg shadow-lg px-3 py-2 text-xs whitespace-nowrap pointer-events-none"
            style={{
              left: hovered === "goal" ? `${leftPct}%` : "50%",
              top: "-8px",
              transform: hovered === "goal" ? "translateY(-100%)" : "translate(-50%, -100%)",
            }}
          >
            {hovered === "goal" ? (
              <>
                <div className="font-medium">{goal.title}</div>
                <div className="text-muted-foreground">
                  {startDate} ~ {endDate}
                </div>
                <div className="text-muted-foreground">
                  进度 {Math.round(goal.progress_percentage)}%{" "}
                  {goal.status === "completed"
                    ? "(已完成)"
                    : goal.status === "abandoned"
                      ? "(已归档)"
                      : ""}
                </div>
              </>
            ) : (() => {
              const ms = milestones.find((m) => `ms-${m.id}` === hovered);
              if (!ms) return null;
              return (
                <>
                  <div className="font-medium">{ms.title}</div>
                  <div className="text-muted-foreground">{ms.due_date}</div>
                  <div className="text-muted-foreground">
                    {ms.status === "completed" ? "已完成" : "待完成"}
                  </div>
                </>
              );
            })()}
          </div>
        )}
      </div>
    </div>
  );
}
