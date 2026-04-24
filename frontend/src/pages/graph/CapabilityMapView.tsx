import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Loader2, AlertCircle, ChevronDown, ChevronUp, Map } from "lucide-react";
import { type CapabilityMapResponse, getCapabilityMap } from "@/services/api";
import { masteryLabels } from "./constants";

// === 能力地图视图组件 ===
export function CapabilityMapView() {
  const [capabilityMap, setCapabilityMap] = useState<CapabilityMapResponse | null>(null);
  const [capabilityLoading, setCapabilityLoading] = useState(false);
  const [capabilityError, setCapabilityError] = useState<string | null>(null);
  const [expandedDomain, setExpandedDomain] = useState<string | null>(null);
  const [capabilityFilter, setCapabilityFilter] = useState<string>("");
  const [capabilityRetryKey, setCapabilityRetryKey] = useState(0);

  // 加载能力地图数据（带请求取消保护，防止快速切换筛选时旧请求覆盖新结果）
  useEffect(() => {
    let cancelled = false;
    setCapabilityLoading(true);
    setCapabilityError(null);
    setCapabilityMap(null);
    setExpandedDomain(null);
    getCapabilityMap(capabilityFilter || undefined)
      .then((data) => { if (!cancelled) setCapabilityMap(data); })
      .catch((err: any) => { if (!cancelled) setCapabilityError(err.message || "加载能力地图失败"); })
      .finally(() => { if (!cancelled) setCapabilityLoading(false); });
    return () => { cancelled = true; };
  }, [capabilityFilter, capabilityRetryKey]);

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6">
      {capabilityLoading && (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      )}
      {capabilityError && (
        <div className="flex flex-col items-center justify-center h-64 gap-3">
          <AlertCircle className="h-10 w-10 text-destructive" />
          <p className="text-sm text-destructive">{capabilityError}</p>
          <button
            onClick={() => setCapabilityRetryKey((k) => k + 1)}
            className="text-sm text-primary hover:underline"
          >
            重试
          </button>
        </div>
      )}
      {capabilityMap && capabilityMap.domains.length === 0 && !capabilityLoading && (
        <div className="flex flex-col items-center justify-center h-64 gap-4">
          <Map className="h-12 w-12 text-muted-foreground" />
          <p className="text-base text-muted-foreground">
            {capabilityFilter
              ? `没有${masteryLabels[capabilityFilter] || capabilityFilter}级别的概念`
              : "开始记录你的学习旅程，能力地图将自动生成"}
          </p>
          {capabilityFilter ? (
            <button
              onClick={() => setCapabilityFilter("")}
              className="text-sm text-primary hover:underline"
            >
              查看全部
            </button>
          ) : (
            <Link
              to="/explore"
              className="text-sm text-primary hover:underline"
            >
              去探索
            </Link>
          )}
        </div>
      )}
      {capabilityMap && (
        <>
        {/* 掌握度筛选 */}
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs text-muted-foreground">筛选：</span>
          {(["", "advanced", "intermediate", "beginner", "new"] as const).map((level) => (
            <button
              key={level}
              onClick={() => setCapabilityFilter(level)}
              className={`px-2.5 py-1 text-xs rounded-md border transition-colors ${
                capabilityFilter === level
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-card hover:bg-accent border-border"
              }`}
            >
              {level ? masteryLabels[level] : "全部"}
            </button>
          ))}
        </div>
        {capabilityMap.domains.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {capabilityMap.domains.map((domain) => (
            <div
              key={domain.name}
              className="border rounded-xl bg-card shadow-sm hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => setExpandedDomain(expandedDomain === domain.name ? null : domain.name)}
            >
              <div className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold truncate">{domain.name}</h3>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-muted-foreground">{domain.concept_count} 个概念</span>
                    {expandedDomain === domain.name ? (
                      <ChevronUp className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <ChevronDown className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full transition-all"
                      style={{ width: `${Math.round(domain.average_mastery * 100)}%` }}
                    />
                  </div>
                  <span className="text-xs font-medium text-muted-foreground w-10 text-right">
                    {Math.round(domain.average_mastery * 100)}%
                  </span>
                </div>
              </div>
              {expandedDomain === domain.name && domain.concepts.length > 0 && (
                <div className="border-t px-4 py-3 space-y-2">
                  {domain.concepts.map((concept) => (
                    <div key={concept.name} className="flex items-center justify-between gap-2">
                      <span className="text-xs truncate">{concept.name}</span>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded shrink-0 ${
                          concept.mastery_level === "advanced"
                            ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                            : concept.mastery_level === "intermediate"
                            ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                            : concept.mastery_level === "beginner"
                            ? "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400"
                            : "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400"
                        }`}
                      >
                        {masteryLabels[concept.mastery_level] || concept.mastery_level}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
        )}
        </>
      )}
    </div>
  );
}
