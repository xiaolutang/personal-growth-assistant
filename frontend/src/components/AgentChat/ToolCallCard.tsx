import { Loader2, CheckCircle2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ToolCallInfo } from "@/stores/agentStore";

interface ToolCallCardProps {
  toolCall: ToolCallInfo;
}

/** 工具名称映射（后端 tool id → 可读名称） */
const TOOL_LABELS: Record<string, string> = {
  list_entries: "查询条目",
  get_entry: "获取条目",
  create_entry: "创建条目",
  update_entry: "更新条目",
  delete_entry: "删除条目",
  search_entries: "语义搜索",
  get_knowledge_graph: "知识图谱",
  get_related_concepts: "关联概念",
  get_project_progress: "项目进度",
  get_review_summary: "成长回顾",
  get_knowledge_stats: "知识统计",
  batch_create_entries: "批量创建",
  batch_update_status: "批量更新状态",
  get_learning_path: "学习路径",
};

function getToolLabel(tool: string): string {
  return TOOL_LABELS[tool] || tool;
}

export function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const { tool, args, status } = toolCall;

  // 提取简短参数摘要
  const argsSummary = Object.keys(args).length > 0
    ? Object.entries(args)
        .filter(([, v]) => v != null && v !== "")
        .slice(0, 2)
        .map(([k, v]) => {
          const val = typeof v === "string" ? v : JSON.stringify(v);
          return `${k}: ${val.length > 20 ? val.slice(0, 20) + "..." : val}`;
        })
        .join(", ")
    : null;

  return (
    <div
      className={cn(
        "flex items-start gap-2.5 rounded-xl border px-3 py-2.5 text-sm",
        status === "running" && "border-indigo-200 bg-indigo-50/50 dark:border-indigo-800 dark:bg-indigo-950/30",
        status === "success" && "border-green-200 bg-green-50/50 dark:border-green-800 dark:bg-green-950/30",
        status === "error" && "border-red-200 bg-red-50/50 dark:border-red-800 dark:bg-red-950/30",
      )}
    >
      {/* 状态图标 */}
      <div className="mt-0.5 shrink-0">
        {status === "running" && (
          <Loader2 className="h-4 w-4 animate-spin text-indigo-500" />
        )}
        {status === "success" && (
          <CheckCircle2 className="h-4 w-4 text-green-500" />
        )}
        {status === "error" && (
          <XCircle className="h-4 w-4 text-red-500" />
        )}
      </div>

      {/* 内容 */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="font-medium text-foreground">
            {getToolLabel(tool)}
          </span>
          {status === "running" && (
            <span className="text-xs text-indigo-500">执行中...</span>
          )}
        </div>
        {argsSummary && (
          <p className="mt-0.5 text-xs text-muted-foreground truncate">
            {argsSummary}
          </p>
        )}
      </div>
    </div>
  );
}
