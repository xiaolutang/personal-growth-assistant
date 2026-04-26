import { AlertCircle, Loader2, Pencil, RefreshCw } from "lucide-react";
import { ServiceUnavailable } from "@/components/ServiceUnavailable";
import { TaskList } from "@/components/TaskList";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Header } from "@/components/layout/Header";
import { PageChatPanel } from "@/components/PageChatPanel";

// Hooks
import { useSearchHistory } from "./explore/useSearchHistory";
import { useExploreSearch } from "./explore/useExploreSearch";
import { useBatchOperations } from "./explore/useBatchOperations";

// Sub-components
import { SearchBar } from "./explore/SearchBar";
import { FilterBar } from "./explore/FilterBar";
import { BatchActionBar } from "./explore/BatchActionBar";

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
    entries,
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
    autoExpandAssistant,
    emptyMessage,
    serviceUnavailable,
    retryService,
    searchInputRef,
  } = search;

  // 批量操作
  const batch = useBatchOperations({
    filteredTasks,
    setEntries,
    setSearchResults,
  });

  const showPanel = showSuggestions && !searchQuery.trim();

  return (
    <main className="flex-1 p-4 md:p-6 pb-32 overflow-y-auto">
      <Header title="探索" />

      {serviceUnavailable ? (
        <ServiceUnavailable onRetry={() => retryService(loadEntries)} />
      ) : (
      <>
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
          <div className="flex flex-col items-center justify-center py-16 gap-4">
            <div className="flex items-center justify-center w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/30">
              <AlertCircle className="h-8 w-8 text-red-500 dark:text-red-400" />
            </div>
            <p className="text-sm text-muted-foreground">{entriesError}</p>
            <button
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm hover:bg-primary/90 transition-colors"
              onClick={() => loadEntries()}
            >
              <RefreshCw className="h-4 w-4" />
              重试
            </button>
          </div>
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

      {/* 搜索助手 AI */}
      <PageChatPanel
        title="搜索助手"
        welcomeMessage="找不到想要的内容？让我帮你"
        suggestions={[
          { label: "最近内容", message: "最近我记录了哪些内容？" },
          { label: "按类型浏览", message: "帮我看看我的笔记有哪些" },
          { label: "知识关联", message: "帮我找出不同条目之间的关联" },
        ]}
        pageContext={{ page: "explore" }}
        pageData={{
          current_query: searchQuery || "无",
          active_tab: activeTab || "全部",
          result_count: filteredTasks.length,
          total_entries: entries.length,
        }}
        defaultCollapsed={!autoExpandAssistant}
      />
      </>
      )}
    </main>
  );
}
