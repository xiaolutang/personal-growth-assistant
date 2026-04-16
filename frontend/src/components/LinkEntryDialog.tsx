import { useState, useRef, useCallback } from "react";
import { X, Search, Loader2, FileText, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { searchEntries, createEntryLink, type RelationType } from "@/services/api";
import type { SearchResult } from "@/types/task";

const relationOptions: { value: RelationType; label: string }[] = [
  { value: "related", label: "关联" },
  { value: "depends_on", label: "依赖" },
  { value: "derived_from", label: "来源于" },
  { value: "references", label: "引用" },
];

interface LinkEntryDialogProps {
  entryId: string;
  onClose: () => void;
  onCreated: () => void;
}

export function LinkEntryDialog({ entryId, onClose, onCreated }: LinkEntryDialogProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchDone, setSearchDone] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState<SearchResult | null>(null);
  const [relationType, setRelationType] = useState<RelationType>("related");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleSearch = useCallback(() => {
    if (searchTimer.current) clearTimeout(searchTimer.current);
    const q = query.trim();
    if (!q) {
      setResults([]);
      setSearchDone(false);
      return;
    }
    setSearching(true);
    setSearchDone(false);
    searchTimer.current = setTimeout(async () => {
      try {
        const res = await searchEntries(q, 10);
        setResults(res.results.filter((r) => r.id !== entryId));
        setSearchDone(true);
      } catch {
        setError("搜索失败，请重试");
      } finally {
        setSearching(false);
      }
    }, 300);
  }, [query, entryId]);

  const handleQueryChange = (value: string) => {
    setQuery(value);
    setSelectedEntry(null);
    setError(null);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (!value.trim()) {
      setResults([]);
      setSearchDone(false);
      return;
    }
    setSearching(true);
    searchTimer.current = setTimeout(async () => {
      try {
        const res = await searchEntries(value.trim(), 10);
        setResults(res.results.filter((r) => r.id !== entryId));
        setSearchDone(true);
      } catch {
        setError("搜索失败");
      } finally {
        setSearching(false);
      }
    }, 300);
  };

  const handleCreate = async () => {
    if (!selectedEntry) return;
    setCreating(true);
    setError(null);
    try {
      await createEntryLink(entryId, selectedEntry.id, relationType);
      onCreated();
      onClose();
    } catch (err: any) {
      const msg = err?.message || "创建关联失败";
      setError(msg.includes("409") ? "关联已存在" : msg);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-card rounded-xl shadow-xl w-full max-w-md mx-4 max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="font-semibold text-base">添加关联</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Search */}
        <div className="p-4 border-b">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              value={query}
              onChange={(e) => handleQueryChange(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="搜索条目..."
              className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/30"
              autoFocus
            />
            {searching && (
              <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" />
            )}
          </div>
        </div>

        {/* Results */}
        <div className="flex-1 overflow-y-auto p-2">
          {results.length > 0 && results.map((item) => (
            <button
              key={item.id}
              onClick={() => setSelectedEntry(item)}
              className={`w-full text-left flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                selectedEntry?.id === item.id
                  ? "bg-primary/10 ring-1 ring-primary"
                  : "hover:bg-muted/50"
              }`}
            >
              <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
              <span className="text-sm truncate flex-1">{item.title}</span>
              {item.category && (
                <Badge variant="outline" className="text-xs shrink-0">{item.category}</Badge>
              )}
            </button>
          ))}
          {searchDone && results.length === 0 && !searching && (
            <p className="text-sm text-muted-foreground text-center py-6">
              未找到匹配的条目
            </p>
          )}
          {!searchDone && !searching && (
            <p className="text-sm text-muted-foreground text-center py-6">
              输入关键词搜索条目
            </p>
          )}
        </div>

        {/* Relation type + Create */}
        {selectedEntry && (
          <div className="p-4 border-t space-y-3">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm text-muted-foreground">关系类型：</span>
              {relationOptions.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setRelationType(opt.value)}
                  className={`px-2.5 py-1 text-xs rounded-md border transition-colors ${
                    relationType === opt.value
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-background border-border hover:bg-muted/50"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            {error && (
              <div className="flex items-center gap-2 text-sm text-destructive">
                <AlertCircle className="h-4 w-4" />
                {error}
              </div>
            )}
            <Button onClick={handleCreate} disabled={creating} className="w-full" size="sm">
              {creating ? (
                <><Loader2 className="h-4 w-4 mr-2 animate-spin" />创建中...</>
              ) : (
                "创建关联"
              )}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
