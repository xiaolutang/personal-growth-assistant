import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TaskList } from "@/components/TaskList";
import { Header } from "@/components/layout/Header";
import { ServiceUnavailable } from "@/components/ServiceUnavailable";
import { PullToRefresh } from "@/components/PullToRefresh";
import { Filter, X, Calendar, Loader2, Pencil, Trash2, ClipboardList, SearchX, ArrowUpDown } from "lucide-react";
import { useNavigate, useLocation } from "react-router-dom";
import { statusConfig } from "@/config/constants";
import { useTaskStore } from "@/stores/taskStore";

// Constants & Hooks
import { STATUS_OPTIONS, TASK_QUERY_PARAMS, QUICK_DATE_OPTIONS, PRIORITY_OPTIONS, SORT_OPTIONS, TASK_SUB_TABS } from "./tasks/constants";
import { useTaskFilters } from "./tasks/useTaskFilters";
import { ViewSelector } from "./tasks/ViewSelector";
import { GroupedView } from "./tasks/GroupedView";
import { TimelineView } from "./tasks/TimelineView";
import { useEffect, useRef } from "react";

export function Tasks() {
  const {
    showFilters, setShowFilters,
    selectedStatus, setSelectedStatus,
    selectedPriority, setSelectedPriority,
    quickDate, setQuickDate,
    startDate, setStartDate,
    endDate, setEndDate,
    sortBy, setSortBy,
    clearFilters, hasActiveFilters,
    filteredTasks,
    activeSubTab, setActiveSubTab,
    activeView, setActiveView,
    selectMode, selectedIds, batchLoading,
    enterSelectMode, exitSelectMode,
    toggleSelect, selectAll,
    handleBatchDelete,
    serviceUnavailable, fetchEntries,
  } = useTaskFilters();
  const isLoading = useTaskStore((state) => state.isLoading);
  const allTasks = useTaskStore((state) => state.tasks);
  const navigate = useNavigate();
  const location = useLocation();

  // F03: 路由切换回时自动刷新数据
  const prevPathname = useRef(location.pathname);
  useEffect(() => {
    if (prevPathname.current !== location.pathname && location.pathname === "/tasks") {
      fetchEntries(TASK_QUERY_PARAMS);
    }
    prevPathname.current = location.pathname;
  }, [location.pathname, fetchEntries]);

  // 区分两种空状态：真正无任务 vs 筛选无结果
  const isTotallyEmpty = !isLoading && allTasks.length === 0;
  const isFilterEmpty = !isLoading && allTasks.length > 0 && filteredTasks.length === 0;

  // F03: 返回 100 条时显示「可能还有更多」提示
  const mayHaveMore = allTasks.length === TASK_QUERY_PARAMS.limit;

  const handleRefresh = () => fetchEntries(TASK_QUERY_PARAMS);

  // F08: Render content based on active view
  const renderContent = () => {
    if (isLoading) {
      return <div className="flex items-center justify-center gap-2 py-8 text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />加载中...</div>;
    }

    // Grouped view — F08
    if (activeView === "grouped") {
      if (isTotallyEmpty) {
        return <GroupedView tasks={[]} />;
      }
      return (
        <GroupedView
          tasks={filteredTasks}
          selectable={selectMode}
          selectedIds={selectedIds}
          onSelect={toggleSelect}
        />
      );
    }

    // Timeline view — F09
    if (activeView === "timeline") {
      if (isTotallyEmpty) {
        return <TimelineView tasks={[]} />;
      }
      return (
        <TimelineView
          tasks={filteredTasks}
          selectable={selectMode}
          selectedIds={selectedIds}
          onSelect={toggleSelect}
        />
      );
    }

    // Default list view
    if (isTotallyEmpty) {
      return (
        <TaskList
          tasks={filteredTasks}
          emptyIcon={<ClipboardList className="h-12 w-12 opacity-20" />}
          emptyMessage="还没有任务，开始记录你的第一个任务吧"
          emptyAction={{ label: "去创建任务", onClick: () => navigate("/") }}
          selectable={selectMode}
          selectedIds={selectedIds}
          onSelect={toggleSelect}
          activeSubTab={activeSubTab}
        />
      );
    }
    if (isFilterEmpty) {
      return (
        <TaskList
          tasks={filteredTasks}
          emptyIcon={<SearchX className="h-10 w-10 opacity-30" />}
          emptyMessage="当前筛选条件下没有匹配的任务"
          emptyAction={{ label: "清除筛选", onClick: clearFilters }}
          selectable={selectMode}
          selectedIds={selectedIds}
          onSelect={toggleSelect}
          activeSubTab={activeSubTab}
        />
      );
    }
    return <TaskList tasks={filteredTasks} selectable={selectMode} selectedIds={selectedIds} onSelect={toggleSelect} activeSubTab={activeSubTab} />;
  };

  return (
    <>
      <Header title="任务列表" />
      <main className="flex-1 overflow-y-auto p-6 pb-32">
        {serviceUnavailable ? (
          <ServiceUnavailable onRetry={() => fetchEntries(TASK_QUERY_PARAMS)} />
        ) : (
        <PullToRefresh onRefresh={handleRefresh}>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">所有任务 ({filteredTasks.length})</CardTitle>
            <div className="flex gap-2 items-center">
              {/* F08: View selector */}
              {!selectMode && (
                <ViewSelector activeView={activeView} onViewChange={setActiveView} />
              )}
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

          {/* F03: 类型子 Tab 栏 */}
          <div className="border-b px-6 py-2 flex gap-1">
            {TASK_SUB_TABS.map((tab) => (
              <button
                key={tab.key}
                data-active={activeSubTab === tab.key}
                onClick={() => setActiveSubTab(tab.key)}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                  activeSubTab === tab.key
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

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
                <div className="text-sm font-medium mb-2">优先级</div>
                <div className="flex flex-wrap gap-2">
                  {PRIORITY_OPTIONS.map((opt) => (
                    <Badge
                      key={opt.value}
                      variant={selectedPriority === opt.value ? "default" : "outline"}
                      className="cursor-pointer"
                      onClick={() => setSelectedPriority(selectedPriority === opt.value ? null : opt.value)}
                    >
                      {opt.label}
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

              <div>
                <div className="text-sm font-medium mb-2 flex items-center gap-1"><ArrowUpDown className="h-4 w-4" />排序</div>
                <div className="flex flex-wrap gap-2">
                  {SORT_OPTIONS.map((opt) => (
                    <Badge
                      key={opt.value}
                      variant={sortBy === opt.value ? "default" : "outline"}
                      className="cursor-pointer"
                      onClick={() => setSortBy(opt.value)}
                    >
                      {opt.label}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          )}

          <CardContent>
            {renderContent()}

            {/* F03: 返回数量 == limit 时底部显示「可能还有更多条目」提示 */}
            {mayHaveMore && !isLoading && (
              <div className="text-center text-sm text-muted-foreground py-3 border-t mt-2">
                可能还有更多条目
              </div>
            )}
          </CardContent>
        </Card>
        </PullToRefresh>
        )}

        {/* 底部批量操作栏 — F03: 移除「转笔记」「转灵感」，只保留删除 */}
        {selectMode && selectedIds.size > 0 && (
          <div className="fixed bottom-16 left-0 right-0 z-40 border-t bg-background/95 backdrop-blur px-4 py-3 flex items-center justify-between">
            <span className="text-sm text-muted-foreground">已选 {selectedIds.size} 项</span>
            <div className="flex gap-2">
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
