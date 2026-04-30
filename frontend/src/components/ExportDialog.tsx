import { useState, useEffect } from "react";
import { Download, Loader2 } from "lucide-react";
import { exportEntries, type ExportOptions } from "@/services/api";
import { BaseDialog } from "@/components/BaseDialog";

interface ExportDialogProps {
  open: boolean;
  onClose: () => void;
}

const TYPE_OPTIONS = [
  { value: "", label: "全部类型" },
  { value: "inbox", label: "灵感" },
  { value: "note", label: "笔记" },
  { value: "task", label: "任务" },
  { value: "project", label: "项目" },
];

export function ExportDialog({ open, onClose }: ExportDialogProps) {
  const [format, setFormat] = useState<"markdown" | "json">("markdown");
  const [type, setType] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 重置表单
  useEffect(() => {
    if (open) {
      setFormat("markdown");
      setType("");
      setStartDate("");
      setEndDate("");
      setIsExporting(false);
      setError(null);
    }
  }, [open]);

  const handleExport = async () => {
    setIsExporting(true);
    setError(null);
    try {
      const options: ExportOptions = {
        format,
        type: type || undefined,
        startDate: startDate || undefined,
        endDate: endDate || undefined,
      };
      const blob = await exportEntries(options);

      const ext = format === "markdown" ? "zip" : "json";
      const mimeType = format === "markdown" ? "application/zip" : "application/json";
      const url = URL.createObjectURL(new Blob([blob], { type: mimeType }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `entries_export.${ext}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "导出失败");
    } finally {
      setIsExporting(false);
    }
  };

  // ExportDialog 有自定义的确认按钮（带 Download 图标），所以使用 footer 而非默认的 confirmLabel
  return (
    <BaseDialog
      open={open}
      onOpenChange={(isOpen) => { if (!isOpen) onClose(); }}
      title="导出数据"
      footer={
        <>
          {/* 错误提示 */}
          {error && (
            <p className="text-sm text-red-500 dark:text-red-400 mb-3">{error}</p>
          )}
          <div className="flex gap-3 mt-4">
            <button
              onClick={onClose}
              disabled={isExporting}
              className="flex-1 px-4 py-2 rounded-lg text-sm font-medium border border-border hover:bg-accent transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleExport}
              disabled={isExporting}
              className="flex-1 px-4 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isExporting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  导出中...
                </>
              ) : (
                <>
                  <Download className="h-4 w-4" />
                  导出
                </>
              )}
            </button>
          </div>
        </>
      }
    >
      {/* 格式选择 */}
      <div className="mb-4">
        <label className="text-sm font-medium mb-2 block">导出格式</label>
        <div className="flex gap-2">
          <button
            onClick={() => setFormat("markdown")}
            className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
              format === "markdown"
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-card border-border hover:bg-accent"
            }`}
          >
            Markdown (ZIP)
          </button>
          <button
            onClick={() => setFormat("json")}
            className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
              format === "json"
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-card border-border hover:bg-accent"
            }`}
          >
            JSON
          </button>
        </div>
      </div>

      {/* 类型过滤 */}
      <div className="mb-4">
        <label className="text-sm font-medium mb-2 block">条目类型</label>
        <select
          value={type}
          onChange={(e) => setType(e.target.value)}
          className="w-full px-3 py-2 rounded-lg border border-border bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        >
          {TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* 日期范围 */}
      <div className="mb-4 grid grid-cols-2 gap-3">
        <div>
          <label className="text-sm font-medium mb-2 block">开始日期</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-border bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        <div>
          <label className="text-sm font-medium mb-2 block">结束日期</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-border bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
      </div>
    </BaseDialog>
  );
}
