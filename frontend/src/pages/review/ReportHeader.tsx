import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Loader2, Download, Archive } from "lucide-react";
import { exportEntries, exportGrowthReport } from "@/services/api";
import type { ReportType } from "@/types/review";

interface ReportHeaderProps {
  reportType: ReportType;
  onReportTypeChange: (type: ReportType) => void;
}

export function ReportHeader({ reportType, onReportTypeChange }: ReportHeaderProps) {
  const [isExporting, setIsExporting] = useState(false);

  return (
    <div className="flex gap-2 mb-6 items-center">
      {(["daily", "weekly", "monthly", "trend"] as ReportType[]).map((type) => (
        <Badge
          key={type}
          variant={reportType === type ? "default" : "outline"}
          className="cursor-pointer px-4 py-2"
          onClick={() => onReportTypeChange(type)}
        >
          {type === "daily" ? "日报" : type === "weekly" ? "周报" : type === "monthly" ? "月报" : "趋势"}
        </Badge>
      ))}
      <div className="ml-auto flex gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={isExporting}
          onClick={async () => {
            setIsExporting(true);
            try {
              const blob = await exportEntries({ format: "markdown" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = "entries_export.zip";
              a.click();
              URL.revokeObjectURL(url);
            } catch { /* silent */ } finally { setIsExporting(false); }
          }}
        >
          {isExporting ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Archive className="h-4 w-4 mr-1" />}
          全量导出
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={isExporting}
          onClick={async () => {
            setIsExporting(true);
            try {
              const blob = await exportGrowthReport();
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              const today = new Date().toISOString().split("T")[0];
              a.download = `growth_report_${today}.md`;
              a.click();
              URL.revokeObjectURL(url);
            } catch { /* silent */ } finally { setIsExporting(false); }
          }}
        >
          {isExporting ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Download className="h-4 w-4 mr-1" />}
          成长报告
        </Button>
      </div>
    </div>
  );
}
