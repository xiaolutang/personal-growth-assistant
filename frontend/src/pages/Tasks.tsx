import { useState, useEffect, useMemo, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TaskList } from "@/components/TaskList";
import { Header } from "@/components/layout/Header";
import { ServiceUnavailable } from "@/components/ServiceUnavailable";
import { useTaskStore } from "@/stores/taskStore";
import { Filter, X, Calendar, Loader2, Pencil, Trash2, FolderInput } from "lucide-react";
import type { TaskStatus, Category } from "@/types/task";
import { statusConfig } from "@/config/constants";
import { toast } from "sonner";

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

  // 多选状态
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [batchLoading, setBatchLoading] = useState(false);
  const deleteTask = useTaskStore((state) => state.deleteTask);
  const storeUpdateEntry = useTaskStore((state) => state.updateEntry);

  // 首次挂载时加载数据（如果 store 为空且服务可用）
  // 使用 getState() 读取实时值，避免 deps=[] 导致闭包捕获初始值
  useEffect(() => {
    const state = useTaskStore.getState();
    if (state.tasks.length === 0 && !state.serviceUnavailable) {
      state.fetchEntries(TASK_QUERY_PARAMS);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- 故意只执行一次

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

  // 多选操作
  const enterSelectMode = useCallback(() => {
    setSelectMode(true);
    setSelectedIds(new Set());
  }, []);

  const exitSelectMode = useCallback(() => {
    setSelectMode(false);
    setSelectedIds(new Set());
  }, []);

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    setSelectedIds(new Set(filteredTasks.map((t) => t.id)));
  }, [filteredTasks]);

  // ESC 键退出多选模式
  useEffect(() => {
    if (!selectMode) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") exitSelectMode();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [selectMode, exitSelectMode]);

  // 批量删除
  const handleBatchDelete = async () => {
    setBatchLoading(true);
    let failed = 0;
    for (const id of selectedIds) {
      try { await deleteTask(id); } catch { failed++; }
    }
    setBatchLoading(false);
    if (failed === 0) {
      toast.success(`已删除 ${selectedIds.size} 条任务`);
      exitSelectMode();
    } else {
      toast.error(`${failed} 条删除失败`);
    }
  };

  // 批量转分类
  const handleBatchCategory = async (category: Category) => {
    setBatchLoading(true);
    let failed = 0;
    for (const id of selectedIds) {
      try { await storeUpdateEntry(id, { category }); } catch { failed++; }
    }
    setBatchLoading(false);
    const label = category === "task" ? "任务" : category === "note" ? "笔记" : "灵感";
    if (failed === 0) {
      toast.success(`已转为${label} ${selectedIds.size} 条`);
      exitSelectMode();
    } else {
      toast.error(`${failed} 条转换失败`);
    }
  };

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
              {!selectMode ? (
                <Button variant="outline" size="sm" onClick={enterSelectMode}>
                  <Pencil className="h-4 w-4 mr-1" />
                  编辑
                </Button>
              ) : (
                <>
                  <Button variant="outline" size="sm" onClick={selectAll}>
                    全选
                  </Button>
                  <Button variant="ghost" size="sm" onClick={exitSelectMode}>
                    取消
                  </Button>
                </>
              )}
              {!selectMode && (
              <>
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
              </>
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
              <div className="flex items-center justify-center gap-2 py-8 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                加载中...
              </div>
            ) : (
              <TaskList
                tasks={filteredTasks}
                emptyMessage="还没有任务，去首页快速录入吧"
                selectable={selectMode}
                selectedIds={selectedIds}
                onSelect={toggleSelect}
              />
            )}
          </CardContent>
        </Card>
        )}

        {/* 底部批量操作栏 */}
        {selectMode && selectedIds.size > 0 && (
          <div className="fixed bottom-16 left-0 right-0 z-40 border-t bg-background/95 backdrop-blur px-4 py-3 flex items-center justify-between">
            <span className="text-sm text-muted-foreground">已选 {selectedIds.size} 项</span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleBatchCategory("note")}
                disabled={batchLoading}
              >
                {batchLoading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <FolderInput className="h-4 w-4 mr-1" />}
                转笔记
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleBatchCategory("inbox")}
                disabled={batchLoading}
              >
                {batchLoading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <FolderInput className="h-4 w-4 mr-1" />}
                转灵感
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleBatchDelete}
                disabled={batchLoading}
              >
                {batchLoading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Trash2 className="h-4 w-4 mr-1" />}
                删除
              </Button>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
