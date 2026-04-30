import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TaskList } from "@/components/TaskList";
import { Header } from "@/components/layout/Header";
import { ServiceUnavailable } from "@/components/ServiceUnavailable";
import { PullToRefresh } from "@/components/PullToRefresh";
import { Filter, X, Calendar, Loader2, Pencil, Trash2, ClipboardList, SearchX, ArrowUpDown, Plus } from "lucide-react";
import { useLocation } from "react-router-dom";
import { statusConfig } from "@/config/constants";
import { useTaskStore } from "@/stores/taskStore";
import { CreateDialog } from "@/components/CreateDialog";

// Constants & Hooks
import { STATUS_OPTIONS, TASK_QUERY_PARAMS, QUICK_DATE_OPTIONS, PRIORITY_OPTIONS, SORT_OPTIONS, TASK_SUB_TABS, ACTIONABLE_CATEGORIES } from "./tasks/constants";
import { useTaskFilters } from "./tasks/useTaskFilters";
import { ViewSelector } from "./tasks/ViewSelector";
import { GroupedView } from "./tasks/GroupedView";
import { TimelineView } from "./tasks/TimelineView";
import { useEffect, useRef, useState, useMemo, useCallback, type ReactNode } from "react";

/** F02: 统一的空状态创建入口，供 list/grouped/timeline 视图复用 */
function EmptyStateCreateEntry({
  icon,
  message,
  onCreateClick,
}: {
  icon: ReactNode;
  message: string;
  onCreateClick: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-3">
      {icon}
      <p>{message}</p>
      <Button variant="outline" size="sm" onClick={onCreateClick}>
        去创建任务
      </Button>
    </div>
  );
}

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
  const location = useLocation();

  // F02: 只计算 actionable 类型的任务数量，保持 actionable-only 语义
  const actionableTaskCount = useMemo(
    () => allTasks.filter((t) => ACTIONABLE_CATEGORIES.includes(t.category)).length,
    [allTasks]
  );

  // F02: CreateDialog 状态
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [emptyStateDefaultType, setEmptyStateDefaultType] = useState<boolean>(false);

  // F02: 根据当前子 Tab 计算 CreateDialog 的 defaultType
  // allowedTypes 统一为 ACTIONABLE_CATEGORIES，defaultType 由子 Tab 预选
  // 空状态强制 defaultType='task'
  const createDialogDefaultType = useMemo(() => {
    if (emptyStateDefaultType) return "task" as const;
    if (activeSubTab === "all") return undefined;
    const tabDef = TASK_SUB_TABS.find(t => t.key === activeSubTab);
    if (tabDef && "category" in tabDef && tabDef.category) return tabDef.category;
    return undefined;
  }, [activeSubTab, emptyStateDefaultType]);

  const handleOpenCreateDialog = useCallback(() => {
    setEmptyStateDefaultType(false);
    setCreateDialogOpen(true);
  }, []);

  // F02: 空状态专用 - 强制 defaultType='task'
  const handleOpenCreateDialogForEmpty = useCallback(() => {
    setEmptyStateDefaultType(true);
    setCreateDialogOpen(true);
  }, []);

  // F02: CreateDialog 使用 skipRefetch 跳过 store 内部无参刷新，
  // 此处以 TASK_QUERY_PARAMS（category_group=actionable, limit=100）精确刷新，
  // 保证任务页数据语义一致，避免双重请求和错误数据集填充。
  const handleCreateSuccess = useCallback(() => {
    fetchEntries(TASK_QUERY_PARAMS);
  }, [fetchEntries]);

  // F03: 路由切换回时自动刷新数据
  const prevPathname = useRef(location.pathname);
  useEffect(() => {
    if (prevPathname.current !== location.pathname && location.pathname === "/tasks") {
      fetchEntries(TASK_QUERY_PARAMS);
    }
    prevPathname.current = location.pathname;
  }, [location.pathname, fetchEntries]);

  // 区分两种空状态：真正无任务 vs 筛选无结果
  // F02: 使用 actionableTaskCount 保持 actionable-only 语义
  const isTotallyEmpty = !isLoading && actionableTaskCount === 0;
  const isFilterEmpty = !isLoading && actionableTaskCount > 0 && filteredTasks.length === 0;

  // F03: 返回 100 条时显示「可能还有更多」提示
  const mayHaveMore = actionableTaskCount >= TASK_QUERY_PARAMS.limit;

  const handleRefresh = () => fetchEntries(TASK_QUERY_PARAMS);

  // F08: Render content based on active view
  const renderContent = () => {
    if (isLoading) {
      return <div className="flex items-center justify-center gap-2 py-8 text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />加载中...</div>;
    }

    // Grouped view — F08
    if (activeView === "grouped") {
      if (isTotallyEmpty) {
        return (
          <EmptyStateCreateEntry
            icon={<ClipboardList className="h-12 w-12 opacity-20" />}
            message="还没有任务，开始记录你的第一个任务吧"
            onCreateClick={handleOpenCreateDialogForEmpty}
          />
        );
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
        return (
          <EmptyStateCreateEntry
            icon={<ClipboardList className="h-12 w-12 opacity-20" />}
            message="还没有任务，开始记录你的第一个任务吧"
            onCreateClick={handleOpenCreateDialogForEmpty}
          />
        );
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
          emptyAction={{ label: "去创建任务", onClick: handleOpenCreateDialogForEmpty }}
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

          {/* F03: 类型子 Tab 栏 + F02: '+New' 按钮 */}
          <div className="border-b px-6 py-2 flex gap-1 items-center justify-between">
            <div className="flex gap-1">
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
            <Button
              variant="outline"
              size="sm"
              onClick={handleOpenCreateDialog}
              aria-label="新建条目"
            >
              <Plus className="h-4 w-4 mr-1" />
              New
            </Button>
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

      {/* F02: CreateDialog - 上下文感知创建 */}
      <CreateDialog
        open={createDialogOpen}
        onOpenChange={(open) => {
          setCreateDialogOpen(open);
          if (!open) setEmptyStateDefaultType(false);
        }}
        defaultType={createDialogDefaultType}
        allowedTypes={ACTIONABLE_CATEGORIES}
        onSuccess={handleCreateSuccess}
        skipStoreRefetch
      />
    </>
  );
}
