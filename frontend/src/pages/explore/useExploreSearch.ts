import { useState, useMemo, useCallback, useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { getEntries, searchEntries } from "@/services/api";
import type { SearchFilterOptions } from "@/services/api";
import { useAgentStore } from "@/stores/agentStore";
import { useServiceUnavailable } from "@/hooks/useServiceUnavailable";
import type { Task } from "@/types/task";
import { normalizeSearchResult, computeTimeRange, filterByCategory, getPopularTags, addToSearchHistory, TABS } from "./utils";
import { trackEvent } from "@/lib/analytics";
import type { TimeRange } from "./utils";

interface UseExploreSearchReturn {
  // URL & tab
  activeTab: string;
  handleTabChange: (key: string) => void;
  // entries
  entries: Task[];
  isLoading: boolean;
  entriesError: string | null;
  loadEntries: () => Promise<void>;
  setEntries: React.Dispatch<React.SetStateAction<Task[]>>;
  // search
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  searchResults: Task[] | null;
  setSearchResults: React.Dispatch<React.SetStateAction<Task[] | null>>;
  searchError: string | null;
  isSearching: boolean;
  handleSearch: () => Promise<void>;
  handleKeyDown: (e: React.KeyboardEvent) => void;
  // filters
  timeRange: TimeRange;
  setTimeRange: (r: TimeRange) => void;
  selectedTags: string[];
  setSelectedTags: React.Dispatch<React.SetStateAction<string[]>>;
  handleTagFilter: (tag: string) => void;
  handleClearFilters: () => void;
  hasActiveFilters: boolean;
  searchFilters: SearchFilterOptions;
  // suggestions
  showSuggestions: boolean;
  setShowSuggestions: (v: boolean) => void;
  // derived
  popularTags: string[];
  filteredTasks: Task[];
  autoExpandAssistant: boolean;
  emptyMessage: string;
  // service
  serviceUnavailable: boolean;
  retryService: (fn: () => Promise<void>) => void;
  // ref for global focus shortcut
  searchInputRef: React.RefObject<HTMLInputElement | null>;
}

export function useExploreSearch(searchHistoryRefresh: () => void): UseExploreSearchReturn {
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
  const setPageExtra = useAgentStore((state) => state.setPageExtra);
  const { serviceUnavailable, runWith503, retry: retryService } = useServiceUnavailable();

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
  const [timeRange, setTimeRange] = useState<TimeRange>("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  // 监听全局聚焦事件
  useEffect(() => {
    const handleFocusSearch = () => searchInputRef.current?.focus();
    window.addEventListener("focus-explore-search", handleFocusSearch);
    return () => window.removeEventListener("focus-explore-search", handleFocusSearch);
  }, []);

  // 根据 URL 参数同步 Tab
  useEffect(() => {
    const t = searchParams.get("type") ?? "";
    if (t !== activeTab) setActiveTab(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 仅在 URL 参数变化时同步覆盖本地 state，故意不依赖 activeTab 以避免循环
  }, [searchParams]);

  // 搜索过滤器
  const searchFilters = useMemo<SearchFilterOptions>(() => {
    const range = computeTimeRange(timeRange);
    const filters: SearchFilterOptions = {};
    if (range.startTime) filters.startTime = range.startTime;
    if (range.endTime) filters.endTime = range.endTime;
    if (selectedTags.length > 0) filters.tags = selectedTags;
    return filters;
  }, [timeRange, selectedTags]);

  const hasActiveFilters = timeRange !== "" || selectedTags.length > 0;

  // 防抖搜索
  const debounceTimer = useRef<ReturnType<typeof setTimeout>>(null);
  useEffect(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current);

    if (!searchQuery.trim() && !hasActiveFilters) {
      setSearchResults(null);
      setSearchError(null);
      return;
    }

    let cancelled = false;
    debounceTimer.current = setTimeout(async () => {
      setIsSearching(true);
      setSearchError(null);
      try {
        const result = await searchEntries(
          searchQuery.trim() || "",
          20,
          activeTab || undefined, // Tab 过滤透传到后端 filter_type
          searchFilters,
        );
        if (!cancelled) {
          const mapped: Task[] = (result.results ?? []).map(normalizeSearchResult);
          setSearchResults(mapped);
          trackEvent("search_performed", { query: searchQuery.trim(), source: "debounce", result_count: mapped.length });
          if (searchQuery.trim()) {
            addToSearchHistory(searchQuery.trim());
            searchHistoryRefresh();
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
  }, [searchQuery, searchFilters, activeTab, hasActiveFilters, searchHistoryRefresh]);

  // 加载条目（部分失败时保留已有数据）
  const loadEntries = useCallback(async () => {
    setIsLoading(true);
    setEntriesError(null);
    try {
      await runWith503(async () => {
        const res = await getEntries({ limit: 100 });
        setEntries(res.entries ?? []);
      });
    } catch {
      // 保留已有 entries（部分失败场景），仅在完全无数据时才设空
      setEntriesError("加载失败，请重试");
    } finally {
      setIsLoading(false);
    }
  }, [runWith503]);

  useEffect(() => { loadEntries(); }, [loadEntries]);

  // 热门标签
  const popularTags = useMemo(() => getPopularTags(entries), [entries]);

  const filteredTasks = useMemo(() => {
    if (searchResults !== null) {
      // F06: 搜索模式 — 全类型混合展示（不再过滤 task/project/decision）
      // task/decision/project 在搜索结果中可点击跳转到任务页
      return searchResults;
    }
    // 非搜索模式：仅展示 EXPLORE_CATEGORIES 中的类型
    return filterByCategory(entries, activeTab);
  }, [entries, searchResults, activeTab]);

  const autoExpandAssistant = !isLoading && !isSearching && filteredTasks.length === 0;

  // Tab 切换
  const handleTabChange = useCallback(
    (key: string) => {
      setActiveTab(key);
      setSearchResults(null);
      setSearchError(null);
      setShowSuggestions(false);
      if (key) {
        setSearchParams({ type: key });
      } else {
        setSearchParams({});
      }
    },
    [setSearchParams]
  );

  // 搜索
  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim() && !hasActiveFilters) {
      setSearchResults(null);
      setSearchError(null);
      return;
    }
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    setIsSearching(true);
    setSearchError(null);
    setShowSuggestions(false);
    try {
      const result = await searchEntries(
        searchQuery.trim() || "",
        20,
        activeTab || undefined, // Tab 过滤透传到后端 filter_type
        searchFilters,
      );
      const mapped: Task[] = (result.results ?? []).map(normalizeSearchResult);
      setSearchResults(mapped);
      trackEvent("search_performed", { query: searchQuery.trim(), source: "manual", result_count: mapped.length });
      if (searchQuery.trim()) {
        addToSearchHistory(searchQuery.trim());
        searchHistoryRefresh();
      }
    } catch {
      setSearchResults(null);
      setSearchError("搜索失败，请稍后重试");
    } finally {
      setIsSearching(false);
    }
  }, [searchQuery, activeTab, searchFilters, hasActiveFilters, searchHistoryRefresh]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") handleSearch();
    },
    [handleSearch]
  );

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
        ? `暂无${TABS.find((t: any) => t.key === activeTab)?.label ?? ""}内容，快去记录吧`
        : "还没有任何内容，开始记录你的想法吧";

  return {
    activeTab,
    handleTabChange,
    entries,
    isLoading,
    entriesError,
    loadEntries,
    setEntries,
    searchQuery,
    setSearchQuery,
    searchResults,
    setSearchResults,
    searchError,
    isSearching,
    handleSearch,
    handleKeyDown,
    timeRange,
    setTimeRange,
    selectedTags,
    setSelectedTags,
    handleTagFilter,
    handleClearFilters,
    hasActiveFilters,
    searchFilters,
    showSuggestions,
    setShowSuggestions,
    popularTags,
    filteredTasks,
    autoExpandAssistant,
    emptyMessage,
    serviceUnavailable,
    retryService,
    searchInputRef,
  };
}
