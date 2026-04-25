import { useState, useEffect } from "react";
import { getInsights, type InsightsResponse } from "@/services/api";
import type { ReportType } from "@/types/review";

interface UseInsightsReturn {
  insightsData: InsightsResponse | null;
  insightsLoading: boolean;
}

export function useInsights(reportType: ReportType): UseInsightsReturn {
  const [insightsData, setInsightsData] = useState<InsightsResponse | null>(null);
  const [insightsLoading, setInsightsLoading] = useState(false);

  useEffect(() => {
    if (reportType !== "weekly" && reportType !== "monthly") {
      setInsightsData(null);
      return;
    }
    let cancelled = false;
    setInsightsLoading(true);
    const period = reportType === "monthly" ? "monthly" : "weekly";
    getInsights(period)
      .then((data) => { if (!cancelled) setInsightsData(data); })
      .catch(() => { if (!cancelled) setInsightsData(null); })
      .finally(() => { if (!cancelled) setInsightsLoading(false); });
    return () => { cancelled = true; };
  }, [reportType]);

  return { insightsData, insightsLoading };
}
