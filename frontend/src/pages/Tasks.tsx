import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TaskList } from "@/components/TaskList";
import { Header } from "@/components/layout/Header";
import { useTaskStore } from "@/stores/taskStore";
import { Filter, X, Calendar } from "lucide-react";
import type { TaskStatus } from "@/types/task";
import { statusConfig } from "@/config/constants";

// 所有可选状态
const STATUS_OPTIONS: TaskStatus[] = ["waitStart", "doing", "complete", "paused", "cancelled"];

// 快捷时间选项
const QUICK_DATE_OPTIONS = [
  { label: "今天", value: "today" },
  { label: "本周", value: "week" },
  { label: "本月", value: "month" },
  { label: "全部", value: "all" },
];

export function Tasks() {
  const tasks = useTaskStore((state) => state.tasks);
  const fetchEntries = useTaskStore((state) => state.fetchEntries);

  // 筛选状态
  const [showFilters, setShowFilters] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState<TaskStatus | null>(null);
  const [quickDate, setQuickDate] = useState<string>("all");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");

  // 获取日期范围
  const getDateRange = (option: string) => {
    const now = new Date();
    const today = now.toISOString().split("T")[0];

    switch (option) {
      case "today":
        return { start: today, end: today };
      case "week": {
        const weekStart = new Date(now);
        weekStart.setDate(now.getDate() - now.getDay());
        const weekEnd = new Date(weekStart);
        weekEnd.setDate(weekStart.getDate() + 6);
        return {
          start: weekStart.toISOString().split("T")[0],
          end: weekEnd.toISOString().split("T")[0],
        };
      }
      case "month": {
        const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
        const monthEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0);
        return {
          start: monthStart.toISOString().split("T")[0],
          end: monthEnd.toISOString().split("T")[0],
        };
      }
      default:
        return { start: "", end: "" };
    }
  };

  // 当快捷时间选项改变时，更新日期范围
  useEffect(() => {
    if (quickDate !== "custom") {
      const range = getDateRange(quickDate);
      setStartDate(range.start);
      setEndDate(range.end);
    }
  }, [quickDate]);

  // 从后端获取筛选后的数据
  useEffect(() => {
    fetchEntries({
      type: "task",
      status: selectedStatus || undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      limit: 100,
    });
  }, [selectedStatus, startDate, endDate, fetchEntries]);

  // 清除筛选
  const clearFilters = () => {
    setSelectedStatus(null);
    setQuickDate("all");
    setStartDate("");
    setEndDate("");
  };

  // 计算是否激活了筛选
  const hasActiveFilters = selectedStatus || startDate || endDate;

  return (
    <>
      <Header title="任务列表" />
      <main className="flex-1 p-6 pb-32">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">所有任务 ({tasks.length})</CardTitle>
            <div className="flex gap-2">
              <Button
                variant={showFilters ? "secondary" : "outline"}
                size="sm"
                onClick={() => setShowFilters(!showFilters)}
              >
                <Filter className="h-4 w-4 mr-1" />
                筛选
                {hasActiveFilters && (
                  <Badge variant="default" className="ml-1 h-4 w-4 p-0 flex items-center justify-center text-xs">
                    !
                  </Badge>
                )}
              </Button>
              {hasActiveFilters && (
                <Button variant="ghost" size="sm" onClick={clearFilters}>
                  <X className="h-4 w-4 mr-1" />
                  清除
                </Button>
              )}
            </div>
          </CardHeader>

          {/* 筛选面板 */}
          {showFilters && (
            <div className="border-b px-6 py-4 bg-muted/30 space-y-4">
              {/* 状态筛选 */}
              <div>
                <div className="text-sm font-medium mb-2">状态</div>
                <div className="flex flex-wrap gap-2">
                  {STATUS_OPTIONS.map((status) => (
                    <Badge
                      key={status}
                      variant={selectedStatus === status ? "default" : "outline"}
                      className="cursor-pointer"
                      onClick={() => setSelectedStatus(selectedStatus === status ? null : status)}
                    >
                      {statusConfig[status]?.label || status}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* 时间筛选 */}
              <div>
                <div className="text-sm font-medium mb-2 flex items-center gap-1">
                  <Calendar className="h-4 w-4" />
                  时间范围
                </div>
                <div className="flex flex-wrap gap-2">
                  {QUICK_DATE_OPTIONS.map((opt) => (
                    <Badge
                      key={opt.value}
                      variant={quickDate === opt.value ? "default" : "outline"}
                      className="cursor-pointer"
                      onClick={() => setQuickDate(opt.value)}
                    >
                      {opt.label}
                    </Badge>
                  ))}
                </div>

                {/* 自定义日期 */}
                {quickDate === "all" && (
                  <div className="flex gap-2 mt-2 items-center">
                    <input
                      type="date"
                      value={startDate}
                      onChange={(e) => {
                        setStartDate(e.target.value);
                        setQuickDate("all");
                      }}
                      className="text-sm border rounded px-2 py-1"
                    />
                    <span className="text-muted-foreground">至</span>
                    <input
                      type="date"
                      value={endDate}
                      onChange={(e) => {
                        setEndDate(e.target.value);
                        setQuickDate("all");
                      }}
                      className="text-sm border rounded px-2 py-1"
                    />
                  </div>
                )}
              </div>
            </div>
          )}

          <CardContent>
            <TaskList
              tasks={tasks}
              emptyMessage="还没有任务，去首页快速录入吧"
            />
          </CardContent>
        </Card>
      </main>
    </>
  );
}
