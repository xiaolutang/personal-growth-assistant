import { useState, useMemo, useCallback, useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { Search, Lightbulb, FileText, Folder, Layers, Clock, X, TrendingUp, Scale, RotateCcw, HelpCircle, Loader2, Calendar, Tag, Pencil, Trash2, FolderInput } from "lucide-react";
import { getEntries, searchEntries } from "../services/api";
import type { SearchFilterOptions } from "../services/api";
import { useTaskStore } from "@/stores/taskStore";
import { toast } from "sonner";
import { PageChatPanel } from "@/components/PageChatPanel";
import { TaskList } from "../components/TaskList";
import type { Task, Category, TaskStatus, Priority, SearchResult } from "../types/task";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "../components/ui/card";
import { Header } from "../components/layout/Header";
import { useChatStore } from "@/stores/chatStore";

/**
 * 将搜索结果归一化为 Task 类型，补齐缺失字段
 */
function normalizeSearchResult(r: SearchResult): Task {
  return {
    id: r.id ?? "",
    title: r.title ?? "",
    content: "",
    category: (r.category ?? "note") as Category,
    status: (r.status ?? "doing") as TaskStatus,
    priority: (r.priority ?? "medium") as Priority,
    tags: r.tags ?? [],
    created_at: r.created_at ?? "",
    updated_at: "",
    file_path: r.file_path ?? "",
    parent_id: undefined,
    content_snippet: r.content_snippet,
  };
}

const TABS = [
  { key: "", label: "全部", icon: Layers },
  { key: "inbox", label: "灵感", icon: Lightbulb },
  { key: "note", label: "笔记", icon: FileText },
  { key: "project", label: "项目", icon: Folder },
  { key: "decision", label: "决策", icon: Scale },
  { key: "reflection", label: "复盘", icon: RotateCcw },
  { key: "question", label: "疑问", icon: HelpCircle },
] as const;

// 探索页只展示 inbox/note/project/decision/reflection/question，不含 task
const EXPLORE_CATEGORIES = new Set(["inbox", "note", "project", "decision", "reflection", "question"]);

// === 时间范围快选 ===
type TimeRange = "today" | "week" | "month" | "";

const TIME_RANGE_LABELS: Record<TimeRange, string> = {
  today: "今天",
  week: "本周",
  month: "本月",
  "": "全部",
};

function computeTimeRange(range: TimeRange): { startTime?: string; endTime?: string } {
  const now = new Date();
  const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const endOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59);

  if (range === "today") {
    const s = startOfDay(now);
    const e = endOfDay(now);
    return { startTime: s.toISOString(), endTime: e.toISOString() };
  }
  if (range === "week") {
    // 本周一到周日
    const day = now.getDay() || 7; // 周日=7
    const monday = new Date(now);
    monday.setDate(now.getDate() - day + 1);
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    return { startTime: startOfDay(monday).toISOString(), endTime: endOfDay(sunday).toISOString() };
  }
  if (range === "month") {
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
    const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    return { startTime: startOfDay(firstDay).toISOString(), endTime: endOfDay(lastDay).toISOString() };
  }
  return {};
}

// === 搜索历史管理 ===
const SEARCH_HISTORY_KEY = "search_history";
const MAX_HISTORY = 5;

function getSearchHistory(): string[] {
  try {
    const raw = localStorage.getItem(SEARCH_HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function addToSearchHistory(query: string) {
  if (!query.trim()) return;
  const history = getSearchHistory().filter((h) => h !== query.trim());
  history.unshift(query.trim());
  localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(history.slice(0, MAX_HISTORY)));
}

function removeFromSearchHistory(query: string) {
  const history = getSearchHistory().filter((h) => h !== query);
  localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(history));
}

// === 热门标签（基于条目 tags 频率） ===
function getPopularTags(entries: Task[], limit = 5): string[] {
  const tagCount: Record<string, number> = {};
  for (const entry of entries) {
    for (const tag of entry.tags || []) {
      tagCount[tag] = (tagCount[tag] || 0) + 1;
    }
  }
  return Object.entries(tagCount)
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([tag]) => tag);
}

function filterByCategory(entries: Task[], tab: string): Task[] {
  const filtered = entries.filter((t) => EXPLORE_CATEGORIES.has(t.category));
  if (!tab) return filtered;
  return filtered.filter((t) => t.category === tab);
}

export function Explore() {
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [searchParams, setSearchParams] = useSearchParams();

  const urlType = searchParams.get("type") ?? "";
  const [activeTab, setActiveTab] = useState(urlType);
  const [entries, setEntries] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Task[] | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [entriesError, setEntriesError] = useState<string | null>(null);
  const { setPageExtra } = useChatStore();

  // 同步 activeTab/searchQuery 到 chatStore.pageExtra
  useEffect(() => {
    const extra: Record<string, string> = { current_tab: activeTab || "all" };
    if (searchQuery.trim()) {
      extra.search_query = searchQuery.trim();
    }
    setPageExtra(extra);
    return () => setPageExtra(null);
  }, [activeTab, searchQuery, setPageExtra]);
  const [isSearching, setIsSearching] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [searchHistory, setSearchHistory] = useState<string[]>(getSearchHistory());
  const [timeRange, setTimeRange] = useState<TimeRange>("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  // 多选状态
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [batchLoading, setBatchLoading] = useState(false);
  const deleteTask = useTaskStore((state) => state.deleteTask);
  const storeUpdateEntry = useTaskStore((state) => state.updateEntry);

  // 监听 AppLayout 派发的聚焦事件（由全局 Cmd+K 触发）
  useEffect(() => {
    const handleFocusSearch = () => searchInputRef.current?.focus();
    window.addEventListener("focus-explore-search", handleFocusSearch);
    return () => window.removeEventListener("focus-explore-search", handleFocusSearch);
  }, []);

  // 根据 URL 参数同步 Tab
  useEffect(() => {
    const t = searchParams.get("type") ?? "";
    if (t !== activeTab) setActiveTab(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  // 构造搜索过滤器
  const searchFilters = useMemo<SearchFilterOptions>(() => {
    const range = computeTimeRange(timeRange);
    const filters: SearchFilterOptions = {};
    if (range.startTime) filters.startTime = range.startTime;
    if (range.endTime) filters.endTime = range.endTime;
    if (selectedTags.length > 0) filters.tags = selectedTags;
    return filters;
  }, [timeRange, selectedTags]);

  const hasActiveFilters = timeRange !== "" || selectedTags.length > 0;

  // 防抖搜索：输入 300ms 后自动触发（含过滤参数）
  const debounceTimer = useRef<ReturnType<typeof setTimeout>>(null);
  useEffect(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current);

    // 空查询 + 无过滤器：清空搜索结果
    if (!searchQuery.trim() && !hasActiveFilters) {
      setSearchResults(null);
      setSearchError(null);
      return;
    }

    // 有查询或有过滤器时触发搜索
    if (!searchQuery.trim() && !hasActiveFilters) return;

    let cancelled = false;
    debounceTimer.current = setTimeout(async () => {
      setIsSearching(true);
      setSearchError(null);
      try {
        const result = await searchEntries(
          searchQuery.trim() || "",
          20,
          activeTab || undefined,
          searchFilters,
        );
        if (!cancelled) {
          const mapped: Task[] = (result.results ?? []).map(normalizeSearchResult);
          setSearchResults(mapped);
          if (searchQuery.trim()) {
            addToSearchHistory(searchQuery.trim());
            setSearchHistory(getSearchHistory());
          }
        }
      } catch {
        if (!cancelled) {
          setSearchResults(null);
          setSearchError("搜索失败，请稍后重试");
        }
      } finally {
        if (!cancelled) setIsSearching(false);
      }
    }, 300);
    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
      cancelled = true;
    };
  }, [searchQuery, searchFilters, activeTab, hasActiveFilters]);

  // 独立获取探索页数据（不复用全局 taskStore）
  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setEntriesError(null);
    getEntries({ limit: 100 })
      .then((res) => {
        if (!cancelled) {
          setEntries(res.entries ?? []);
        }
      })
      .catch(() => {
        if (!cancelled) setEntriesError("加载失败，请重试");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  // 热门标签
  const popularTags = useMemo(() => getPopularTags(entries), [entries]);

  const filteredTasks = useMemo(() => {
    const source = searchResults ?? entries;
    return filterByCategory(source, activeTab);
  }, [entries, searchResults, activeTab]);

  // 空结果时自动展开搜索助手
  const autoExpandAssistant = !isLoading && !isSearching && filteredTasks.length === 0;

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
    if (!confirm(`确定要删除选中的 ${selectedIds.size} 条内容吗？`)) return;
    setBatchLoading(true);
    let failed = 0;
    const deletedIds: string[] = [];
    for (const id of selectedIds) {
      await deleteTask(id);
      if (useTaskStore.getState().error) {
        failed++;
        useTaskStore.setState({ error: null });
      } else {
        deletedIds.push(id);
      }
    }
    setBatchLoading(false);
    if (deletedIds.length > 0) {
      setEntries((prev) => prev.filter((e) => !deletedIds.includes(e.id)));
      setSearchResults((prev) => prev ? prev.filter((e) => !deletedIds.includes(e.id)) : null);
    }
    if (failed === 0) {
      toast.success(`已删除 ${deletedIds.length} 条内容`);
      exitSelectMode();
    } else {
      toast.error(`${failed} 条删除失败`);
    }
  };

  // 批量转分类
  const handleBatchCategory = async (category: Category) => {
    setBatchLoading(true);
    let failed = 0;
    const updatedIds: string[] = [];
    for (const id of selectedIds) {
      await storeUpdateEntry(id, { category });
      if (useTaskStore.getState().error) {
        failed++;
        useTaskStore.setState({ error: null });
      } else {
        updatedIds.push(id);
      }
    }
    setBatchLoading(false);
    if (updatedIds.length > 0) {
      setEntries((prev) => prev.map((e) => updatedIds.includes(e.id) ? { ...e, category } : e));
      setSearchResults((prev) => prev ? prev.map((e) => updatedIds.includes(e.id) ? { ...e, category } : e) : null);
    }
    const label = category === "task" ? "任务" : category === "note" ? "笔记" : "灵感";
    if (failed === 0) {
      toast.success(`已转为${label} ${updatedIds.length} 条`);
      exitSelectMode();
    } else {
      toast.error(`${failed} 条转换失败`);
    }
  };

  const handleTabChange = useCallback(
    (key: string) => {
      setActiveTab(key);
      setSearchResults(null);
      setSearchError(null);
      // 切换 Tab 保留过滤器，不清除
      setShowSuggestions(false);
      if (key) {
        setSearchParams({ type: key });
      } else {
        setSearchParams({});
      }
    },
    [setSearchParams]
  );

  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim() && !hasActiveFilters) {
      setSearchResults(null);
      setSearchError(null);
      return;
    }
    // 清除防抖定时器，避免重复搜索
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    setIsSearching(true);
    setSearchError(null);
    setShowSuggestions(false);
    try {
      const result = await searchEntries(
        searchQuery.trim() || "",
        20,
        activeTab || undefined,
        searchFilters,
      );
      const mapped: Task[] = (result.results ?? []).map(normalizeSearchResult);
      setSearchResults(mapped);
      if (searchQuery.trim()) {
        addToSearchHistory(searchQuery.trim());
        setSearchHistory(getSearchHistory());
      }
    } catch {
      setSearchResults(null);
      setSearchError("搜索失败，请稍后重试");
    } finally {
      setIsSearching(false);
    }
  }, [searchQuery, activeTab, searchFilters, hasActiveFilters]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") handleSearch();
    },
    [handleSearch]
  );

  const handleSuggestionClick = useCallback((query: string) => {
    setSearchQuery(query);
    setShowSuggestions(false);
  }, []);

  const handleDeleteHistory = useCallback((query: string, e: React.MouseEvent) => {
    e.stopPropagation();
    removeFromSearchHistory(query);
    setSearchHistory(getSearchHistory());
  }, []);

  const handleTagFilter = useCallback((tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    );
  }, []);

  const handleClearFilters = useCallback(() => {
    setTimeRange("");
    setSelectedTags([]);
  }, []);

  const emptyMessage = searchError
    ? searchError
    : searchResults !== null
      ? "没有找到匹配的结果"
      : activeTab
        ? `暂无${TABS.find((t) => t.key === activeTab)?.label ?? ""}内容，快去记录吧`
        : "还没有任何内容，开始记录你的想法吧";

  // 搜索建议面板显示条件：搜索框聚焦且无查询内容
  const showPanel = showSuggestions && !searchQuery.trim();

  return (
    <main className="flex-1 p-4 md:p-6 pb-32 overflow-y-auto">
      <Header title="探索" />

      {/* 搜索栏 */}
      <div className="mb-4 relative">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 dark:text-gray-500" />
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            placeholder="试试搜索：最近学习的主题..."
            className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        {/* 搜索建议面板 */}
        {showPanel && (searchHistory.length > 0 || popularTags.length > 0) && (
          <div className="absolute z-20 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg overflow-hidden">
            {/* 搜索历史 */}
            {searchHistory.length > 0 && (
              <div className="p-3">
                <div className="text-xs text-muted-foreground font-medium mb-2 flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  最近搜索
                </div>
                <div className="space-y-0.5">
                  {searchHistory.map((query) => (
                    <div
                      key={query}
                      className="flex items-center justify-between px-2 py-1.5 rounded-md hover:bg-accent/50 cursor-pointer text-sm"
                      onMouseDown={() => handleSuggestionClick(query)}
                    >
                      <span className="truncate">{query}</span>
                      <button
                        onClick={(e) => handleDeleteHistory(query, e)}
                        className="text-muted-foreground hover:text-foreground shrink-0 ml-2"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {/* 热门标签 */}
            {popularTags.length > 0 && (
              <div className="p-3 border-t">
                <div className="text-xs text-muted-foreground font-medium mb-2 flex items-center gap-1">
                  <TrendingUp className="h-3 w-3" />
                  热门标签
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {popularTags.map((tag) => (
                    <button
                      key={tag}
                      onMouseDown={() => handleTagFilter(tag)}
                      className={`px-2 py-1 rounded-full text-xs font-medium transition-colors ${
                        selectedTags.includes(tag)
                          ? "bg-indigo-500 text-white"
                          : "bg-primary/10 text-primary hover:bg-primary/20"
                      }`}
                    >
                      #{tag}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 时间快选 + 标签筛选 + 过滤 chip */}
      <div className="mb-4 space-y-2">
        {/* 时间快选按钮组 */}
        <div className="flex items-center gap-1.5">
          <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
          {(["", "today", "week", "month"] as TimeRange[]).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                timeRange === range
                  ? "bg-indigo-500 text-white"
                  : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
              }`}
            >
              {TIME_RANGE_LABELS[range]}
            </button>
          ))}
        </div>

        {/* 过滤条件 chip */}
        {hasActiveFilters && (
          <div className="flex items-center gap-1.5 flex-wrap">
            {timeRange && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-xs font-medium">
                <Calendar className="h-3 w-3" />
                {TIME_RANGE_LABELS[timeRange]}
                <button onClick={() => setTimeRange("")} className="hover:text-indigo-800 dark:hover:text-indigo-200">
                  <X className="h-3 w-3" />
                </button>
              </span>
            )}
            {selectedTags.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 text-xs font-medium"
              >
                <Tag className="h-3 w-3" />
                #{tag}
                <button onClick={() => handleTagFilter(tag)} className="hover:text-emerald-800 dark:hover:text-emerald-200">
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
            <button
              onClick={handleClearFilters}
              className="px-2 py-0.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              全部清除
            </button>
          </div>
        )}
      </div>

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
          {!isLoading && !entriesError && filteredTasks.length > 0 && (
            !selectMode ? (
              <Button variant="outline" size="sm" onClick={enterSelectMode}>
                <Pencil className="h-4 w-4 mr-1" />
                编辑
              </Button>
            ) : (
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={selectAll}>
                  全选
                </Button>
                <Button variant="ghost" size="sm" onClick={exitSelectMode}>
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
        ) : entriesError ? (
          <div className="flex flex-col items-center justify-center gap-3 p-8 text-muted-foreground">
            <p>{entriesError}</p>
            <button
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm"
              onClick={() => window.location.reload()}
            >
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
          <div
            onTouchStart={selectMode ? undefined : undefined}
          >
            <TaskList
              tasks={filteredTasks}
              emptyMessage={emptyMessage}
              highlightKeyword={searchQuery.trim()}
              selectable={selectMode}
              selectedIds={selectedIds}
              onSelect={toggleSelect}
              disableActions={selectMode}
            />
          </div>
        )}
      </Card>

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
    </main>
  );
}
