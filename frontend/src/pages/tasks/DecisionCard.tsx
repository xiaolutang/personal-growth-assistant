import { useState, useMemo } from "react";
import { Scale, Clock, Pause } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Task } from "@/types/task";
import { useTaskStore } from "@/stores/taskStore";
import { toast } from "sonner";
import { DecisionResultDialog, type DecisionChoice } from "./DecisionResultDialog";

interface DecisionCardProps {
  decision: Task;
  selectable?: boolean;
  selected?: boolean;
  onSelect?: (id: string) => void;
  /** F06: 自定义卡片点击回调（搜索模式下跳转到任务页） */
  onClickOverride?: (task: Task) => void;
}

export function DecisionCard({ decision, selectable = false, selected = false, onSelect, onClickOverride }: DecisionCardProps) {
  const storeUpdateEntry = useTaskStore((state) => state.updateEntry);
  const storeCreateEntry = useTaskStore((state) => state.createEntry);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogChoice, setDialogChoice] = useState<DecisionChoice>("YES");

  const isComplete = decision.status === "complete";
  const isPaused = decision.status === "paused";

  // 解析已完成决策的结果
  const decisionResult = useMemo(() =>
    isComplete && decision.content.includes("## 决策结果")
      ? extractDecisionResult(decision.content)
      : null,
    [isComplete, decision.content]
  );

  // 去除决策结果段的正文摘要
  const contentSummary = useMemo(
    () => decision.content.replace(/## 决策结果[\s\S]*$/, "").trim(),
    [decision.content]
  );

  const handleDecide = (choice: DecisionChoice) => {
    setDialogChoice(choice);
    setDialogOpen(true);
  };

  const handleDefer = async () => {
    try {
      await storeUpdateEntry(decision.id, { status: "paused" });
    } catch {
      toast.error("操作失败，请重试");
    }
  };

  const handleDialogConfirm = async (data: {
    reason: string;
    createTask: boolean;
    taskTitle: string;
  }) => {
    const { reason, createTask, taskTitle } = data;

    // 构建新 content：在原始 content 末尾追加决策结果
    const resultSection = [
      "",
      "## 决策结果",
      `- **决定**: ${dialogChoice}`,
      ...(reason ? [`- **理由**: ${reason}`] : []),
      `- **时间**: ${new Date().toISOString().split("T")[0]}`,
    ].join("\n");

    const newContent = decision.content
      ? `${decision.content}\n${resultSection}`
      : resultSection;

    // 1. 更新 decision 状态为 complete
    try {
      await storeUpdateEntry(decision.id, {
        status: "complete",
        content: newContent,
      });
    } catch {
      toast.error("操作失败，请重试");
      return;
    }

    setDialogOpen(false);

    // 2. 如果勾选创建任务，尝试创建
    if (createTask && taskTitle) {
      try {
        // parent_id: decision.parent_id 存在则用，否则用 decision 自身 id
        const parentId = decision.parent_id || decision.id;
        await storeCreateEntry({
          type: "task",
          title: taskTitle,
          parent_id: parentId,
        });
        toast.success("决策完成，已创建跟进任务");
      } catch {
        toast.error("子任务创建失败，请手动创建");
      }
    } else {
      toast.success("决策完成");
    }
  };

  const handleCardClick = () => {
    if (selectable) {
      onSelect?.(decision.id);
      return;
    }
    // F06: 搜索模式下支持自定义点击行为
    if (onClickOverride) {
      onClickOverride(decision);
      return;
    }
  };

  // 状态标签渲染
  const renderStatusBadge = () => {
    if (isComplete) {
      return (
        <Badge variant="success" className="text-[10px] px-1.5 h-5">
          已决定
        </Badge>
      );
    }
    if (isPaused) {
      return (
        <Badge variant="outline" className="text-[10px] px-1.5 h-5">
          已延后
        </Badge>
      );
    }
    return (
      <Badge variant="warning" className="text-[10px] px-1.5 h-5">
        待决定
      </Badge>
    );
  };

  return (
    <>
      <Card
        data-category="decision"
        className={cn(
          "px-3 py-3 cursor-pointer hover:bg-accent/50 transition-colors",
          selectable && selected && "bg-accent/30"
        )}
        onClick={handleCardClick}
      >
        {/* Header: icon + title + status badge */}
        <div className="flex items-start gap-2 mb-2">
          <Scale className="h-4 w-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <p className={cn(
                "text-sm font-medium truncate flex-1",
                isComplete && "line-through text-muted-foreground"
              )}>
                {decision.title}
              </p>
              {renderStatusBadge()}
            </div>
          </div>
        </div>

        {/* Content summary (background description) */}
        {decision.content && (
          <p
            data-testid="decision-content"
            className="text-xs text-muted-foreground mt-1 mb-2 line-clamp-2 pl-6"
          >
            {contentSummary}
          </p>
        )}

        {/* Decision result for completed decisions */}
        {decisionResult && (
          <div className="ml-6 mb-2 p-2 rounded-md bg-muted/50 text-xs">
            <span className="font-medium">
              决策：{decisionResult.choice === "YES" ? (
                <span className="text-green-600">YES</span>
              ) : (
                <span className="text-red-600">NO</span>
              )}
            </span>
            {decisionResult.reason && (
              <span className="text-muted-foreground ml-1">
                — {decisionResult.reason}
              </span>
            )}
          </div>
        )}

        {/* Tags */}
        {decision.tags && decision.tags.length > 0 && (
          <div className="flex items-center gap-1 pl-6 mb-2">
            {decision.tags.slice(0, 3).map((tag) => (
              <Badge key={tag} variant="outline" className="text-[10px] px-1 h-4">
                {tag}
              </Badge>
            ))}
          </div>
        )}

        {/* Action buttons (only for non-complete decisions) */}
        {!isComplete && !isPaused && (
          <div className="flex items-center gap-2 pl-6">
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs border-green-500 text-green-600 hover:bg-green-50 dark:hover:bg-green-950"
              onClick={(e) => {
                e.stopPropagation();
                handleDecide("YES");
              }}
            >
              决定 YES
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs border-red-500 text-red-600 hover:bg-red-50 dark:hover:bg-red-950"
              onClick={(e) => {
                e.stopPropagation();
                handleDecide("NO");
              }}
            >
              决定 NO
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs text-muted-foreground"
              onClick={(e) => {
                e.stopPropagation();
                handleDefer();
              }}
            >
              <Pause className="h-3 w-3 mr-1" />
              延后
            </Button>
          </div>
        )}

        {/* Paused indicator */}
        {isPaused && (
          <div className="flex items-center gap-1 pl-6 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            <span>已延后，可稍后决定</span>
          </div>
        )}
      </Card>

      <DecisionResultDialog
        open={dialogOpen}
        choice={dialogChoice}
        onConfirm={handleDialogConfirm}
        onCancel={() => setDialogOpen(false)}
      />
    </>
  );
}

/** 从 content 中提取决策结果 */
function extractDecisionResult(content: string): { choice: string; reason: string } | null {
  const resultMatch = content.match(/## 决策结果([\s\S]*?)$/);
  if (!resultMatch) return null;

  const section = resultMatch[1];
  const choiceMatch = section.match(/\*\*决定\*\*:\s*(YES|NO)/);
  const reasonMatch = section.match(/\*\*理由\*\*:\s*(.+)/);

  if (!choiceMatch) return null;

  return {
    choice: choiceMatch[1],
    reason: reasonMatch?.[1]?.trim() || "",
  };
}
