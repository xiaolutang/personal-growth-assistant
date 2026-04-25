import { Loader2, FolderInput, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Category } from "@/types/task";

interface BatchActionBarProps {
  selectedCount: number;
  batchLoading: boolean;
  onBatchCategory: (category: Category) => void;
  onBatchDelete: () => void;
}

export function BatchActionBar({
  selectedCount,
  batchLoading,
  onBatchCategory,
  onBatchDelete,
}: BatchActionBarProps) {
  return (
    <div className="fixed bottom-16 left-0 right-0 z-40 border-t bg-background/95 backdrop-blur px-4 py-3 flex items-center justify-between">
      <span className="text-sm text-muted-foreground">已选 {selectedCount} 项</span>
      <div className="flex gap-2">
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
