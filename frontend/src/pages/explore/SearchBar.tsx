import { Search, Clock, X, TrendingUp } from "lucide-react";

interface SearchBarProps {
  searchQuery: string;
  onSearchQueryChange: (q: string) => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  onFocus: () => void;
  onBlur: () => void;
  showPanel: boolean;
  searchHistory: string[];
  onDeleteHistory: (query: string) => void;
  onSuggestionClick: (query: string) => void;
  popularTags: string[];
  selectedTags: string[];
  onTagFilter: (tag: string) => void;
}

export function SearchBar({
  searchQuery,
  onSearchQueryChange,
  onKeyDown,
  onFocus,
  onBlur,
  showPanel,
  searchHistory,
  onDeleteHistory,
  onSuggestionClick,
  popularTags,
  selectedTags,
  onTagFilter,
}: SearchBarProps) {
  return (
    <div className="mb-4 relative">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 dark:text-gray-500" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchQueryChange(e.target.value)}
          onKeyDown={onKeyDown}
          onFocus={onFocus}
          onBlur={() => setTimeout(onBlur, 200)}
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
                    onMouseDown={() => onSuggestionClick(query)}
                  >
                    <span className="truncate">{query}</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteHistory(query);
                      }}
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
                    onMouseDown={() => onTagFilter(tag)}
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
  );
}
