import { useState, useMemo, useCallback, useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { Search, Lightbulb, FileText, Folder, Layers, Clock, X, TrendingUp, Scale, RotateCcw, HelpCircle, Loader2 } from "lucide-react";
import { getEntries, searchEntries } from "../services/api";
import { TaskList } from "../components/TaskList";
import type { Task } from "../types/task";
import { Card, CardHeader, CardTitle } from "../components/ui/card";
import { Header } from "../components/layout/Header";
import { useChatStore } from "@/stores/chatStore";

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

  // 防抖搜索：输入 300ms 后自动触发
  const debounceTimer = useRef<ReturnType<typeof setTimeout>>(null);
  useEffect(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    if (!searchQuery.trim()) {
      setSearchResults(null);
      setSearchError(null);
      return;
    }
    let cancelled = false;
    debounceTimer.current = setTimeout(async () => {
      setIsSearching(true);
      setSearchError(null);
      try {
        const result = await searchEntries(searchQuery.trim(), 20);
        if (!cancelled) {
          const mapped: Task[] = (result.results ?? []).map((r: any) => ({
            id: r.id ?? "",
            title: r.title ?? "",
            content: r.content ?? "",
            category: r.category ?? "note",
            status: r.status ?? "doing",
            priority: r.priority ?? "medium",
            tags: r.tags ?? [],
            created_at: r.created_at ?? "",
            updated_at: r.updated_at ?? "",
            file_path: r.file_path ?? "",
            parent_id: r.parent_id ?? null,
          }));
          setSearchResults(mapped);
          addToSearchHistory(searchQuery.trim());
          setSearchHistory(getSearchHistory());
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
  }, [searchQuery]);

  // 独立获取探索页数据（不复用全局 taskStore）
  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    getEntries({ limit: 100 })
      .then((res) => {
        if (!cancelled) {
          setEntries(res.entries ?? []);
        }
      })
      .catch(() => {
        // 获取失败时保持空列表，不影响页面渲染
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

  const handleTabChange = useCallback(
    (key: string) => {
      setActiveTab(key);
      setSearchResults(null);
      setSearchError(null);
      setSearchQuery("");
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
    if (!searchQuery.trim()) {
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
      const result = await searchEntries(searchQuery.trim(), 20);
      const mapped: Task[] = (result.results ?? []).map((r: any) => ({
        id: r.id ?? "",
        title: r.title ?? "",
        content: r.content ?? "",
        category: r.category ?? "note",
        status: r.status ?? "doing",
        priority: r.priority ?? "medium",
        tags: r.tags ?? [],
        created_at: r.created_at ?? "",
        updated_at: r.updated_at ?? "",
        file_path: r.file_path ?? "",
        parent_id: r.parent_id ?? null,
      }));
      setSearchResults(mapped);
      addToSearchHistory(searchQuery.trim());
      setSearchHistory(getSearchHistory());
    } catch {
      setSearchResults(null);
      setSearchError("搜索失败，请稍后重试");
    } finally {
      setIsSearching(false);
    }
  }, [searchQuery]);

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
                      onMouseDown={() => handleSuggestionClick(tag)}
                      className="px-2 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium hover:bg-primary/20 transition-colors"
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 类型 Tab */}
      <div className="flex gap-2 mb-6">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
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
        <CardHeader>
          <CardTitle>
            {searchResults !== null
              ? `搜索结果 (${filteredTasks.length})`
              : activeTab
                ? `${TABS.find((t) => t.key === activeTab)?.label} (${filteredTasks.length})`
                : `全部 (${filteredTasks.length})`}
          </CardTitle>
        </CardHeader>
        {isLoading ? (
          <div className="flex items-center justify-center gap-2 p-4 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            加载中...
          </div>
        ) : isSearching ? (
          <div className="flex items-center justify-center gap-2 p-4 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            搜索中...
          </div>
        ) : searchError ? (
          <div className="p-4 text-center text-red-500 dark:text-red-400">{searchError}</div>
        ) : (
          <TaskList tasks={filteredTasks} emptyMessage={emptyMessage} highlightKeyword={searchQuery.trim()} />
        )}
      </Card>
    </main>
  );
}
