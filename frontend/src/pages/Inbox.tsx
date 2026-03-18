import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TaskList } from "@/components/TaskList";
import { Header } from "@/components/layout/Header";
import { useTaskStore } from "@/stores/taskStore";
import { useStreamParse } from "@/hooks/useStreamParse";
import { Plus, Loader2, Lightbulb, Sparkles } from "lucide-react";
import { categoryConfig, categoryBgColors } from "@/config/constants";
import type { Category } from "@/types/task";

export function Inbox() {
  const { getTasksByCategory, createEntry } = useTaskStore();
  const [quickInput, setQuickInput] = useState("");

  const inboxItems = getTasksByCategory("inbox");

  // 流式解析 Hook
  const { result, isLoading: isParsing, parse } = useStreamParse({
    onComplete: async (data) => {
      if (data.tasks.length > 0) {
        // 并行创建条目
        await Promise.all(
          data.tasks.map((task) =>
            createEntry({
              type: task.category,
              title: task.title || "",
              content: task.content || "",
              tags: task.tags || [],
              status: task.status,
              planned_date: task.planned_date,
            })
          )
        );
        setQuickInput("");
      }
    },
  });

  // 快速记录提交
  const handleQuickSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickInput.trim() || isParsing) return;
    await parse(quickInput.trim());
  };

  return (
    <>
      <Header title="灵感收集" />
      <main className="flex-1 p-6 pb-32 space-y-6 overflow-y-auto">
        {/* 快速记录卡片 */}
        <Card className="border-primary/20 bg-primary/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              快速记录
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              输入任何想法，AI 会自动识别类型并分类存储
            </p>
            <form onSubmit={handleQuickSubmit} className="flex gap-2">
              <div className="relative flex-1">
                <Lightbulb className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  value={quickInput}
                  onChange={(e) => setQuickInput(e.target.value)}
                  placeholder="例如：学习 RAG 技术 / 明天开会讨论项目进度 / 想法：做一个个人知识管理工具..."
                  className="pl-10"
                  disabled={isParsing}
                />
              </div>
              <Button type="submit" disabled={!quickInput.trim() || isParsing}>
                {isParsing ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    解析中
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4 mr-2" />
                    记录
                  </>
                )}
              </Button>
            </form>
            {isParsing && result && result.tasks.length > 0 && (
              <div className="mt-3 p-3 bg-muted/50 rounded-lg">
                <p className="text-sm font-medium mb-2">AI 识别结果：</p>
                <div className="space-y-1">
                  {result.tasks.map((task, index) => (
                    <div key={index} className="flex items-center gap-2 text-sm">
                      <span className={`px-2 py-0.5 rounded text-xs ${categoryBgColors[task.category as Category] || "bg-muted"}`}>
                        {categoryConfig[task.category as Category]?.label || task.category}
                      </span>
                      <span>{task.title}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 灵感列表 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              灵感箱 ({inboxItems.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <TaskList
              tasks={inboxItems}
              emptyMessage="还没有灵感，试试在上方快速录入"
            />
          </CardContent>
        </Card>
      </main>
    </>
  );
}
