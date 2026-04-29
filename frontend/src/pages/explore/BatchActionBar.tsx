import { Loader2, FolderInput, Trash2, ArrowRightCircle, Scale } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Category } from "@/types/task";

interface BatchActionBarProps {
  selectedCount: number;
  batchLoading: boolean;
  onBatchCategory: (category: Category) => void;
  onBatchDelete: () => void;
  /** F07: 批量转化（使用 convert API） */
  onBatchConvert?: (targetCategory: "task" | "decision") => void;
  /** F07: 选中的条目中是否全部为 inbox 类型（用于决定转化按钮是否可用） */
  allSelectedInbox?: boolean;
}

export function BatchActionBar({
  selectedCount,
  batchLoading,
  onBatchCategory,
  onBatchDelete,
  onBatchConvert,
  allSelectedInbox = false,
}: BatchActionBarProps) {
  return (
    <div className="fixed bottom-16 left-0 right-0 z-40 border-t bg-background/95 backdrop-blur px-4 py-3 flex items-center justify-between">
      <span className="text-sm text-muted-foreground">已选 {selectedCount} 项</span>
      <div className="flex gap-2">
        {/* F07: 批量转化按钮（仅 inbox 条目可用） */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => onBatchConvert?.("task")}
          disabled={batchLoading || !allSelectedInbox || !onBatchConvert}
          title={!allSelectedInbox ? "仅灵感条目可转化" : "批量转为任务"}
        >
          {batchLoading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <ArrowRightCircle className="h-4 w-4 mr-1" />}
          转任务
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onBatchConvert?.("decision")}
          disabled={batchLoading || !allSelectedInbox || !onBatchConvert}
          title={!allSelectedInbox ? "仅灵感条目可转化" : "批量转为决策"}
        >
          {batchLoading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Scale className="h-4 w-4 mr-1" />}
          转决策
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onBatchCategory("note")}
          disabled={batchLoading}
        >
          {batchLoading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <FolderInput className="h-4 w-4 mr-1" />}
          转笔记
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onBatchCategory("inbox")}
          disabled={batchLoading}
        >
          {batchLoading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <FolderInput className="h-4 w-4 mr-1" />}
          转灵感
        </Button>
        <Button
          variant="destructive"
          size="sm"
          onClick={onBatchDelete}
          disabled={batchLoading}
        >
          {batchLoading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Trash2 className="h-4 w-4 mr-1" />}
          删除
        </Button>
      </div>
    </div>
  );
}
