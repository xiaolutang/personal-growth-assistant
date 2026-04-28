import { AlertCircle, Loader2, Pencil, RefreshCw } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ErrorState } from "@/components/ErrorState";
import { ServiceUnavailable } from "@/components/ServiceUnavailable";
import { TaskList } from "@/components/TaskList";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Header } from "@/components/layout/Header";
import { PullToRefresh } from "@/components/PullToRefresh";
import { useTaskStore } from "@/stores/taskStore";
import type { EntryTemplate } from "@/services/api";

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
import { TABS } from "./explore/utils";

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
  const isCreating = useTaskStore((state) => state.isLoading);

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

  // 批量操作
  const batch = useBatchOperations({
    filteredTasks,
    setEntries,
    setSearchResults,
    onSyncCompleted: () => loadEntries(),
  });

  const showPanel = showSuggestions && !searchQuery.trim();

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
              <Button variant="outline" size="sm" onClick={batch.enterSelectMode}>
                <Pencil className="h-4 w-4 mr-1" />
                编辑
              </Button>
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
            <TaskList
              tasks={filteredTasks}
              emptyMessage={emptyMessage}
              highlightKeyword={searchQuery.trim()}
              selectable={batch.selectMode}
              selectedIds={batch.selectedIds}
              onSelect={batch.toggleSelect}
              disableActions={batch.selectMode}
            />
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
    </main>
  );
}
