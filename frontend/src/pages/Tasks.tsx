import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TaskList } from "@/components/TaskList";
import { Header } from "@/components/layout/Header";
import { ServiceUnavailable } from "@/components/ServiceUnavailable";
import { Filter, X, Calendar, Loader2, Pencil, Trash2, FolderInput, ClipboardList, SearchX } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { statusConfig } from "@/config/constants";
import { useTaskStore } from "@/stores/taskStore";

// Constants & Hooks
import { STATUS_OPTIONS, TASK_QUERY_PARAMS, QUICK_DATE_OPTIONS } from "./tasks/constants";
import { useTaskFilters } from "./tasks/useTaskFilters";

export function Tasks() {
  const {
    showFilters, setShowFilters,
    selectedStatus, setSelectedStatus,
    quickDate, setQuickDate,
    startDate, setStartDate,
    endDate, setEndDate,
    clearFilters, hasActiveFilters,
    filteredTasks,
    selectMode, selectedIds, batchLoading,
    enterSelectMode, exitSelectMode,
    toggleSelect, selectAll,
    handleBatchDelete, handleBatchCategory,
    serviceUnavailable, fetchEntries,
  } = useTaskFilters();
  const isLoading = useTaskStore((state) => state.isLoading);
  const allTasks = useTaskStore((state) => state.tasks);
  const navigate = useNavigate();

  // 区分两种空状态：真正无任务 vs 筛选无结果
  const isTotallyEmpty = !isLoading && allTasks.length === 0;
  const isFilterEmpty = !isLoading && allTasks.length > 0 && filteredTasks.length === 0;

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
                  <Pencil className="h-4 w-4 mr-1" />编辑
                </Button>
              ) : (
                <>
                  <Button variant="outline" size="sm" onClick={selectAll}>全选</Button>
                  <Button variant="ghost" size="sm" onClick={exitSelectMode}>取消</Button>
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
                  <Badge variant="default" className="ml-1 h-4 w-4 p-0 flex items-center justify-center text-xs">!</Badge>
                )}
              </Button>
              {hasActiveFilters && (
                <Button variant="ghost" size="sm" onClick={clearFilters}>
                  <X className="h-4 w-4 mr-1" />清除
                </Button>
              )}
              </>
              )}
            </div>
          </CardHeader>

          {/* 筛选面板 */}
          {showFilters && (
            <div className="border-b px-6 py-4 bg-muted/30 space-y-4">
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

              <div>
                <div className="text-sm font-medium mb-2 flex items-center gap-1"><Calendar className="h-4 w-4" />时间范围</div>
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

                {quickDate === "all" && (
                  <div className="flex gap-2 mt-2 items-center">
                    <input type="date" value={startDate} onChange={(e) => { setStartDate(e.target.value); setQuickDate("all"); }} className="text-sm border rounded px-2 py-1" />
                    <span className="text-muted-foreground">至</span>
                    <input type="date" value={endDate} onChange={(e) => { setEndDate(e.target.value); setQuickDate("all"); }} className="text-sm border rounded px-2 py-1" />
                  </div>
                )}
              </div>
            </div>
          )}

          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center gap-2 py-8 text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />加载中...</div>
            ) : isTotallyEmpty ? (
              <TaskList
                tasks={filteredTasks}
                emptyIcon={<ClipboardList className="h-12 w-12 opacity-20" />}
                emptyMessage="还没有任务，开始记录你的第一个任务吧"
                emptyAction={{ label: "去创建任务", onClick: () => navigate("/") }}
                selectable={selectMode}
                selectedIds={selectedIds}
                onSelect={toggleSelect}
              />
            ) : isFilterEmpty ? (
              <TaskList
                tasks={filteredTasks}
                emptyIcon={<SearchX className="h-10 w-10 opacity-30" />}
                emptyMessage="当前筛选条件下没有匹配的任务"
                emptyAction={{ label: "清除筛选", onClick: clearFilters }}
                selectable={selectMode}
                selectedIds={selectedIds}
                onSelect={toggleSelect}
              />
            ) : (
              <TaskList tasks={filteredTasks} selectable={selectMode} selectedIds={selectedIds} onSelect={toggleSelect} />
            )}
          </CardContent>
        </Card>
        )}

        {/* 底部批量操作栏 */}
        {selectMode && selectedIds.size > 0 && (
          <div className="fixed bottom-16 left-0 right-0 z-40 border-t bg-background/95 backdrop-blur px-4 py-3 flex items-center justify-between">
            <span className="text-sm text-muted-foreground">已选 {selectedIds.size} 项</span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => handleBatchCategory("note")} disabled={batchLoading}>
                {batchLoading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <FolderInput className="h-4 w-4 mr-1" />}转笔记
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleBatchCategory("inbox")} disabled={batchLoading}>
                {batchLoading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <FolderInput className="h-4 w-4 mr-1" />}转灵感
              </Button>
              <Button variant="destructive" size="sm" onClick={handleBatchDelete} disabled={batchLoading}>
                {batchLoading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Trash2 className="h-4 w-4 mr-1" />}删除
              </Button>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
