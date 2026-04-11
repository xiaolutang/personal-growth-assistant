import { useState, useEffect, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TaskList } from "@/components/TaskList";
import { Header } from "@/components/layout/Header";
import { ServiceUnavailable } from "@/components/ServiceUnavailable";
import { useTaskStore } from "@/stores/taskStore";
import { Filter, X, Calendar } from "lucide-react";
import type { TaskStatus } from "@/types/task";
import { statusConfig } from "@/config/constants";

// 所有可选状态
const STATUS_OPTIONS: TaskStatus[] = ["waitStart", "doing", "complete", "paused", "cancelled"];

// 默认查询参数
const TASK_QUERY_PARAMS = { type: "task" as const, limit: 100 };

// 快捷时间选项
const QUICK_DATE_OPTIONS = [
  { label: "今天", value: "today" },
  { label: "本周", value: "week" },
  { label: "本月", value: "month" },
  { label: "全部", value: "all" },
];

export function Tasks() {
  const allTasks = useTaskStore((state) => state.tasks);
  const fetchEntries = useTaskStore((state) => state.fetchEntries);
  const isLoading = useTaskStore((state) => state.isLoading);
  const serviceUnavailable = useTaskStore((state) => state.serviceUnavailable);

  // 筛选状态
  const [showFilters, setShowFilters] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState<TaskStatus | null>(null);
  const [quickDate, setQuickDate] = useState<string>("all");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");

  // 首次挂载时加载数据（如果 store 为空且服务可用）
  useEffect(() => {
    if (allTasks.length === 0 && !serviceUnavailable) {
      fetchEntries(TASK_QUERY_PARAMS);
    }
  }, []); // 只在首次挂载时执行

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

  // 本地筛选数据（显示所有类型）
  const filteredTasks = useMemo(() => {
    let result = allTasks;

    // 状态筛选
    if (selectedStatus) {
      result = result.filter((task) => task.status === selectedStatus);
    }

    // 日期筛选
    if (startDate) {
      result = result.filter((task) => {
        const taskDate = task.planned_date || task.created_at;
        if (!taskDate) return false;
        const dateStr = taskDate.split("T")[0];
        return dateStr >= startDate;
      });
    }
    if (endDate) {
      result = result.filter((task) => {
        const taskDate = task.planned_date || task.created_at;
        if (!taskDate) return false;
        const dateStr = taskDate.split("T")[0];
        return dateStr <= endDate;
      });
    }

    return result;
  }, [allTasks, selectedStatus, startDate, endDate]);

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
        {serviceUnavailable ? (
          <ServiceUnavailable onRetry={() => fetchEntries(TASK_QUERY_PARAMS)} />
        ) : (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">所有任务 ({filteredTasks.length})</CardTitle>
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
            {isLoading ? (
              <div className="text-center py-8 text-muted-foreground">加载中...</div>
            ) : (
              <TaskList
                tasks={filteredTasks}
                emptyMessage="还没有任务，去首页快速录入吧"
              />
            )}
          </CardContent>
        </Card>
        )}
      </main>
    </>
  );
}
