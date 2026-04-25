import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { Loader2, AlertCircle, ChevronDown, ChevronUp, Map } from "lucide-react";
import { type CapabilityMapResponse, getCapabilityMap } from "@/services/api";
import { masteryLabels, MASTERY_LEVELS } from "./constants";
import { useServiceUnavailable } from "@/hooks/useServiceUnavailable";
import { ServiceUnavailable } from "@/components/ServiceUnavailable";
import { ApiError } from "@/lib/errors";

// === 能力地图视图组件 ===
export function CapabilityMapView() {
  const [capabilityMap, setCapabilityMap] = useState<CapabilityMapResponse | null>(null);
  const [capabilityLoading, setCapabilityLoading] = useState(false);
  const [capabilityError, setCapabilityError] = useState<string | null>(null);
  const [expandedDomain, setExpandedDomain] = useState<string | null>(null);
  const [capabilityFilter, setCapabilityFilter] = useState<string>("");
  const { serviceUnavailable, runWith503 } = useServiceUnavailable();

  const loadCapability = useCallback(async (filter?: string) => {
    setCapabilityLoading(true);
    setCapabilityError(null);
    setCapabilityMap(null);
    setExpandedDomain(null);
    try {
      await runWith503(async () => {
        const data = await getCapabilityMap(filter || undefined);
        setCapabilityMap(data);
      });
    } catch (err: any) {
      // runWith503 只捕获 503 并设 serviceUnavailable=true，其他错误原样抛出
      if (err instanceof ApiError && err.isServiceUnavailable) {
        // 503 已由 hook 处理，不再设置 capabilityError
      } else {
        setCapabilityError(err.message || "加载能力地图失败");
      }
    } finally {
      setCapabilityLoading(false);
    }
  }, [runWith503]);

  useEffect(() => {
    loadCapability(capabilityFilter || undefined);
  }, [capabilityFilter, loadCapability]);

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6">
      {serviceUnavailable && (
        <ServiceUnavailable onRetry={() => loadCapability(capabilityFilter || undefined)} />
      )}
      {!serviceUnavailable && capabilityLoading && (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      )}
      {!serviceUnavailable && capabilityError && (
        <div className="flex flex-col items-center justify-center h-64 gap-3">
          <AlertCircle className="h-10 w-10 text-destructive" />
          <p className="text-sm text-destructive">{capabilityError}</p>
          <button
            onClick={() => loadCapability(capabilityFilter || undefined)}
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
          {(["", ...MASTERY_LEVELS] as const).map((level) => (
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
