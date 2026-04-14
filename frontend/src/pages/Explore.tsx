import { useState, useMemo, useCallback, useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { Search, Lightbulb, FileText, Folder, Layers } from "lucide-react";
import { getEntries, searchEntries } from "../services/api";
import { TaskList } from "../components/TaskList";
import type { Task } from "../types/task";
import { Card, CardHeader, CardTitle } from "../components/ui/card";
import { Header } from "../components/layout/Header";

const TABS = [
  { key: "", label: "全部", icon: Layers },
  { key: "inbox", label: "灵感", icon: Lightbulb },
  { key: "note", label: "笔记", icon: FileText },
  { key: "project", label: "项目", icon: Folder },
] as const;

// 探索页只展示 inbox/note/project，不含 task
const EXPLORE_CATEGORIES = new Set(["inbox", "note", "project"]);

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
  const [isSearching, setIsSearching] = useState(false);

  // Cmd+K / Ctrl+K 全局聚焦搜索框
  useEffect(() => {
    const handleGlobalKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    document.addEventListener("keydown", handleGlobalKey);
    return () => document.removeEventListener("keydown", handleGlobalKey);
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
    getEntries({ limit: 200 })
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

  const emptyMessage = searchError
    ? searchError
    : searchResults !== null
      ? "没有找到匹配的结果"
      : activeTab
        ? `暂无${TABS.find((t) => t.key === activeTab)?.label ?? ""}内容，快去记录吧`
        : "还没有任何内容，开始记录你的想法吧";

  return (
    <main className="flex-1 p-6 pb-32 overflow-y-auto">
      <Header title="探索" />

      {/* 搜索栏 */}
      <div className="mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="搜索灵感、笔记、项目..."
            className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
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
          <div className="p-4 text-center text-gray-500">加载中...</div>
        ) : isSearching ? (
          <div className="p-4 text-center text-gray-500">搜索中...</div>
        ) : searchError ? (
          <div className="p-4 text-center text-red-500">{searchError}</div>
        ) : (
          <TaskList tasks={filteredTasks} emptyMessage={emptyMessage} highlightKeyword={searchQuery.trim()} />
        )}
      </Card>
    </main>
  );
}
