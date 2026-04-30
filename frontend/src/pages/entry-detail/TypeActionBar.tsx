import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Loader2, ArrowRight, FileText, Scale, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useTaskStore } from "@/stores/taskStore";
import { statusConfig, nextStatusMap } from "@/config/constants";
import type { Task, TaskStatus } from "@/types/task";

import { ConvertDialog } from "@/pages/explore/ConvertDialog";
import { CompletionPrompt } from "@/pages/tasks/CompletionPrompt";

interface TypeActionBarProps {
  entry: Task;
  parentEntry?: Task | null;
  onReload: () => void;
}

export function TypeActionBar({ entry, parentEntry, onReload }: TypeActionBarProps) {
  const navigate = useNavigate();
  const updateTaskStatus = useTaskStore((s) => s.updateTaskStatus);
  const createEntry = useTaskStore((s) => s.createEntry);

  const [showConvertDialog, setShowConvertDialog] = useState(false);
  const [convertTarget, setConvertTarget] = useState<"task" | "decision">("task");
  const [statusUpdating, setStatusUpdating] = useState(false);
  const [showCompletionPrompt, setShowCompletionPrompt] = useState(false);
  const [convertingToNote, setConvertingToNote] = useState(false);

  const { category } = entry;

  // task: 状态推进 + 复盘提示
  if (category === "task") {
    const nextStatus: TaskStatus = nextStatusMap[entry.status];
    const nextLabel = statusConfig[nextStatus]?.label ?? nextStatus;

    const handleStatusAdvance = async () => {
      setStatusUpdating(true);
      try {
        await updateTaskStatus(entry.id, nextStatus);
        if (nextStatus === "complete") {
          setShowCompletionPrompt(true);
        }
        onReload();
      } finally {
        setStatusUpdating(false);
      }
    };

    return (
      <>
        <Card className="mb-6">
          <CardContent className="py-3">
            <div className="flex items-center gap-3">
              <span className="text-sm text-muted-foreground">状态推进:</span>
              <Button
                size="sm"
                variant="outline"
                onClick={handleStatusAdvance}
                disabled={statusUpdating}
              >
                {statusUpdating ? (
                  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                ) : (
                  <ArrowRight className="h-4 w-4 mr-1" />
                )}
                {nextStatus === "complete" ? "标记完成" : nextStatus === "doing" ? "开始" : nextLabel}
              </Button>
            </div>
          </CardContent>
        </Card>
        {showCompletionPrompt && entry.status === "complete" && (
          <CompletionPrompt
            task={entry}
            onDismiss={() => setShowCompletionPrompt(false)}
          />
        )}
      </>
    );
  }

  // inbox: 转为任务/决策
  if (category === "inbox") {
    return (
      <>
        <Card className="mb-6">
          <CardContent className="py-3">
            <div className="flex items-center gap-3">
              <span className="text-sm text-muted-foreground">转化为:</span>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setConvertTarget("task");
                  setShowConvertDialog(true);
                }}
              >
                <CheckCircle className="h-4 w-4 mr-1" />
                转为任务
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setConvertTarget("decision");
                  setShowConvertDialog(true);
                }}
              >
                <Scale className="h-4 w-4 mr-1" />
                转为决策
              </Button>
            </div>
          </CardContent>
        </Card>
        <ConvertDialog
          open={showConvertDialog}
          onClose={() => setShowConvertDialog(false)}
          onSuccess={() => {
            setShowConvertDialog(false);
            onReload();
          }}
          entry={entry}
          defaultTarget={convertTarget}
        />
      </>
    );
  }

  // question: 转为笔记（独立创建新 note，不走 convert API）
  if (category === "question") {
    const handleConvertToNote = async () => {
      setConvertingToNote(true);
      try {
        const note = await createEntry({
          type: "note",
          title: entry.title,
          content: "",
          parent_id: entry.id,
        });
        toast.success("笔记已创建");
        navigate(`/entries/${note.id}`);
      } catch {
        toast.error("创建笔记失败，请重试");
      } finally {
        setConvertingToNote(false);
      }
    };

    return (
      <Card className="mb-6">
        <CardContent className="py-3">
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground">将问题整理为:</span>
            <Button
              size="sm"
              variant="outline"
              onClick={handleConvertToNote}
              disabled={convertingToNote}
            >
              {convertingToNote ? (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              ) : (
                <FileText className="h-4 w-4 mr-1" />
              )}
              转为笔记
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  // reflection: 显示关联的原 task 链接（parent_id）
  if (category === "reflection") {
    if (!parentEntry) return null;
    return (
      <Card className="mb-6">
        <CardContent className="py-3">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">关联任务:</span>
            <button
              onClick={() => navigate(`/entries/${parentEntry.id}`)}
              className="text-primary hover:underline font-medium"
            >
              {parentEntry.title}
            </button>
          </div>
        </CardContent>
      </Card>
    );
  }

  // project / note / decision: 无专属操作栏
  return null;
}
