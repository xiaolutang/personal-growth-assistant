import { AlertCircle, Loader2, Pencil, Plus, RefreshCw } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { CreateDialog } from "@/components/CreateDialog";
import { ErrorState } from "@/components/ErrorState";
import { ServiceUnavailable } from "@/components/ServiceUnavailable";
import { TaskList } from "@/components/TaskList";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Header } from "@/components/layout/Header";
import { PullToRefresh } from "@/components/PullToRefresh";
import { useTaskStore } from "@/stores/taskStore";
import type { EntryTemplate } from "@/services/api";
import type { Category } from "@/types/task";

// Hooks
import { useSearchHistory } from "./explore/useSearchHistory";
import { useExploreSearch } from "./explore/useExploreSearch";
import { useBatchOperations } from "./explore/useBatchOperations";

// Sub-components
import { SearchBar } from "./explore/SearchBar";
import { FilterBar } from "./explore/FilterBar";
import { BatchActionBar } from "./explore/BatchActionBar";
import { TemplateSelector } from "./explore/TemplateSelector";

// Utils
import { TABS, EXPLORE_CATEGORIES, groupSearchResultsByType } from "./explore/utils";
import type { Task } from "@/types/task";

// F04: 支持创建表单的 tab 集合（模块顶层常量）
const TABS_WITH_CREATE: ReadonlySet<Category> = new Set(["inbox", "reflection", "question"]);

export function Explore() {
  // 搜索历史
  const { searchHistory, removeHistory, refresh: refreshHistory } = useSearchHistory();

  // 搜索 & 过滤
  const search = useExploreSearch(refreshHistory);
  const {
    activeTab,
    handleTabChange,
    isLoading,
    entriesError,
    loadEntries,
    setEntries,
    setSearchResults,
    searchQuery,
    setSearchQuery,
    searchResults,
    searchError,
    isSearching,
    handleKeyDown,
    timeRange,
    setTimeRange,
    selectedTags,
    handleTagFilter,
    handleClearFilters,
    hasActiveFilters,
    showSuggestions,
    setShowSuggestions,
    popularTags,
    filteredTasks,
    emptyMessage,
    serviceUnavailable,
    retryService,
    searchInputRef,
  } = search;

  // 模板创建
  const navigate = useNavigate();
  const createEntry = useTaskStore((state) => state.createEntry);
  const isCreating = useTaskStore((state) => state.isCreating);

  const handleTemplateSelected = async (template: EntryTemplate) => {
    try {
      const entry = await createEntry({
        type: "note",
        title: template.name,
        content: template.content,
        template_id: template.id,
      });
      toast.success(`已创建笔记：${template.name}`);
      navigate(`/entries/${entry.id}`);
    } catch {
      toast.error("创建笔记失败，请重试");
    }
  };

  const showPanel = showSuggestions && !searchQuery.trim();

  // F06: 搜索模式下 task/decision/project 点击跳转到任务页
  const isSearchMode = searchResults !== null;

  // F04: 创建表单集成（inbox/reflection/question tab 的 '+New' 按钮）
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createDialogType, setCreateDialogType] = useState<Category>("inbox");

  const handleOpenCreateDialog = (type: string) => {
    if (TABS_WITH_CREATE.has(type as Category)) {
      setCreateDialogType(type as Category);
      setCreateDialogOpen(true);
    }
  };

  const showCreateButton = !isSearchMode && !searchQuery.trim() && TABS_WITH_CREATE.has(activeTab as Category);

  // 批量操作
  const batch = useBatchOperations({
    filteredTasks,
    setEntries,
    setSearchResults,
    onSyncCompleted: () => loadEntries(),
  });
  const handleSearchCardClick = (task: Task) => {
    if (!EXPLORE_CATEGORIES.has(task.category)) {
      navigate(`/tasks?tab=${task.category}`);
    } else {
      navigate(`/entries/${task.id}`);
    }
  };

  // F07: 转化成功后从列表移除条目
  const handleConvertSuccess = (task: Task) => {
    setEntries((prev) => prev.filter((e) => e.id !== task.id));
    setSearchResults((prev) => prev ? prev.filter((e) => e.id !== task.id) : null);
  };

  // F10: 识别 URL 中的 entry_id 参数，数据加载后定位并展开该条目
  const [searchParams, setSearchParamsLocal] = useSearchParams();
  const entryIdFromUrl = searchParams.get("entry_id");

  // 加载完成后，如果 URL 有 entry_id，导航到该条目详情页
  const handledEntryIdRef = useRef<string | null>(null);
  useEffect(() => {
    if (entryIdFromUrl && !isLoading && filteredTasks.length > 0 && handledEntryIdRef.current !== entryIdFromUrl) {
      const targetEntry = filteredTasks.find((e) => e.id === entryIdFromUrl);
      if (targetEntry) {
        handledEntryIdRef.current = entryIdFromUrl;
        // 清除 URL 中的 entry_id 参数，保留 type
        const newParams = new URLSearchParams(searchParams);
        newParams.delete("entry_id");
        setSearchParamsLocal(newParams, { replace: true });
        navigate(`/entries/${entryIdFromUrl}`);
      }
    }
  }, [entryIdFromUrl, isLoading, filteredTasks, navigate, searchParams, setSearchParamsLocal]);

  return (
    <main className="flex-1 overflow-y-auto p-4 md:p-6 pb-32">
      <Header title="探索" />

      {serviceUnavailable ? (
        <ServiceUnavailable onRetry={() => retryService(loadEntries)} />
      ) : (
      <PullToRefresh onRefresh={loadEntries}>
      {/* 搜索栏 */}
      <SearchBar
        searchQuery={searchQuery}
        onSearchQueryChange={setSearchQuery}
        onKeyDown={handleKeyDown}
        inputRef={searchInputRef}
        onFocus={() => setShowSuggestions(true)}
        onBlur={() => setShowSuggestions(false)}
        showPanel={showPanel}
        searchHistory={searchHistory}
        onDeleteHistory={removeHistory}
        onSuggestionClick={(q) => { setSearchQuery(q); setShowSuggestions(false); }}
        popularTags={popularTags}
        selectedTags={selectedTags}
        onTagFilter={handleTagFilter}
      />

      {/* 过滤器 */}
      <FilterBar
        timeRange={timeRange}
        setTimeRange={setTimeRange}
        selectedTags={selectedTags}
        onTagFilter={handleTagFilter}
        onClearFilters={handleClearFilters}
        hasActiveFilters={hasActiveFilters}
      />

      {/* 类型 Tab */}
      <div className="flex gap-2 mb-6 overflow-x-auto scrollbar-hide">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              ref={isActive ? (el) => el?.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" }) : undefined}
              onClick={() => handleTabChange(tab.key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                isActive
                  ? "bg-indigo-500 text-white"
                  : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* 笔记模板选择器（仅在 note tab 时显示） */}
      <TemplateSelector
        activeTab={activeTab}
        onTemplateSelected={handleTemplateSelected}
      />
      {isCreating && activeTab === "note" && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          创建笔记中...
        </div>
      )}

      {/* 内容区域 */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>
            {searchResults !== null
              ? `搜索结果 (${filteredTasks.length})`
              : activeTab
                ? `${TABS.find((t) => t.key === activeTab)?.label} (${filteredTasks.length})`
                : `全部 (${filteredTasks.length})`}
          </CardTitle>
          {!isLoading && !entriesError && filteredTasks.length > 0 && !searchError && (
            !batch.selectMode ? (
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={batch.enterSelectMode}>
                  <Pencil className="h-4 w-4 mr-1" />
                  编辑
                </Button>
              </div>
            ) : (
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={batch.selectAll}>
                  全选
                </Button>
                <Button variant="ghost" size="sm" onClick={batch.exitSelectMode}>
                  取消
                </Button>
              </div>
            )
          )}
          {showCreateButton && (
            <Button variant="outline" size="sm" onClick={() => handleOpenCreateDialog(activeTab)}>
              <Plus className="h-4 w-4 mr-1" />
              新建
            </Button>
          )}
        </CardHeader>
        {isLoading ? (
          <div className="flex items-center justify-center gap-2 p-4 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            加载中...
          </div>
        ) : entriesError && filteredTasks.length === 0 ? (
          <ErrorState message={entriesError} onRetry={() => loadEntries()} />
        ) : isSearching ? (
          <div className="flex items-center justify-center gap-2 p-4 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            搜索中...
          </div>
        ) : searchError ? (
          <div className="p-4 text-center text-red-500 dark:text-red-400">{searchError}</div>
        ) : (
          <div onTouchStart={batch.selectMode ? undefined : undefined}>
            {/* 部分失败提示条：有错误但已有数据时显示 */}
            {entriesError && filteredTasks.length > 0 && (
              <div className="flex items-center justify-between gap-2 mx-4 mt-2 mb-3 px-3 py-2 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
                <div className="flex items-center gap-2 text-sm text-amber-700 dark:text-amber-300">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>部分数据加载失败</span>
                </div>
                <button
                  className="flex items-center gap-1 text-xs text-amber-700 dark:text-amber-300 hover:text-amber-900 dark:hover:text-amber-100 transition-colors"
                  onClick={() => loadEntries()}
                >
                  <RefreshCw className="h-3 w-3" />
                  重试
                </button>
              </div>
            )}
            {isSearchMode && filteredTasks.length > 0 ? (
              // F12: 搜索结果按类型分组展示
              groupSearchResultsByType(filteredTasks).map((group) => {
                const GroupIcon = group.icon;
                return (
                  <div key={group.type} className="mb-4">
                    <div className="flex items-center gap-2 px-1 mb-2 text-sm font-medium text-muted-foreground">
                      <GroupIcon className="h-4 w-4" />
                      <span>{group.label}</span>
                      <span className="text-xs">({group.count})</span>
                    </div>
                    <TaskList
                      tasks={group.tasks}
                      emptyMessage=""
                      highlightKeyword={searchQuery.trim()}
                      selectable={batch.selectMode}
                      selectedIds={batch.selectedIds}
                      onSelect={batch.toggleSelect}
                      disableActions={batch.selectMode}
                      onCardClick={handleSearchCardClick}
                      onConvertSuccess={handleConvertSuccess}
                    />
                  </div>
                );
              })
            ) : (
              <TaskList
                tasks={filteredTasks}
                emptyMessage={emptyMessage}
                highlightKeyword={searchQuery.trim()}
                selectable={batch.selectMode}
                selectedIds={batch.selectedIds}
                onSelect={batch.toggleSelect}
                disableActions={batch.selectMode}
                onCardClick={isSearchMode ? handleSearchCardClick : undefined}
                onConvertSuccess={handleConvertSuccess}
              />
            )}
          </div>
        )}
      </Card>

      {/* 底部批量操作栏 */}
      {batch.selectMode && batch.selectedIds.size > 0 && (
        <BatchActionBar
          selectedCount={batch.selectedIds.size}
          batchLoading={batch.batchLoading}
          onBatchCategory={batch.handleBatchCategory}
          onBatchDelete={batch.handleBatchDelete}
          onBatchConvert={batch.handleBatchConvert}
          allSelectedInbox={batch.allSelectedInbox}
        />
      )}

      {/* 离线批量操作提示 */}
      {batch.offlineMode && batch.selectMode && (
        <div className="fixed bottom-20 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-lg bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-700 text-sm text-amber-700 dark:text-amber-300 shadow-lg">
          当前离线，操作将在联网后自动同步
        </div>
      )}

      {/* 部分失败条目提示 */}
      {batch.failedItems.length > 0 && (
        <div className="fixed bottom-20 left-1/2 -translate-x-1/2 z-50 max-w-sm px-4 py-3 rounded-lg bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 shadow-lg">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-4 w-4 mt-0.5 text-red-500 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-red-700 dark:text-red-300">
                {batch.failedItems.length} 条操作失败
              </p>
              <p className="text-xs text-red-600 dark:text-red-400 mt-1 truncate">
                {batch.failedItems.map((f) => f.title).join("、")}
              </p>
            </div>
            <button
              className="text-xs text-red-500 hover:text-red-700 dark:hover:text-red-300 shrink-0"
              onClick={batch.clearFailedItems}
            >
              关闭
            </button>
          </div>
        </div>
      )}

      </PullToRefresh>
      )}

      {/* F04: 创建表单（inbox/reflection/question tab 的 '+New' 触发） */}
      <CreateDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        defaultType={createDialogType}
        allowedTypes={[createDialogType]}
        onSuccess={() => { loadEntries(); }}
      />
    </main>
  );
}
