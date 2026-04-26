import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Scale, RotateCcw, HelpCircle } from "lucide-react";

export function CategoryInfoCard({ category, status }: { category: string; status: string }) {
  if (category === "decision") {
    return (
      <Card className="mb-6 border-amber-200 dark:border-amber-800">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2 text-amber-700 dark:text-amber-300">
            <Scale className="h-4 w-4" />
            决策记录
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          记录重要决策的背景、方案对比和选择理由，帮助未来回顾决策脉络。
        </CardContent>
      </Card>
    );
  }

  if (category === "reflection") {
    return (
      <Card className="mb-6 border-teal-200 dark:border-teal-800">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2 text-teal-700 dark:text-teal-300">
            <RotateCcw className="h-4 w-4" />
            复盘笔记
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          结构化回顾目标、结果和经验教训，持续改进。
        </CardContent>
      </Card>
    );
  }

  if (category === "question") {
    return (
      <Card className="mb-6 border-rose-200 dark:border-rose-800">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2 text-rose-700 dark:text-rose-300">
            <HelpCircle className="h-4 w-4" />
            待解疑问
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          记录待解决的问题和思考方向，积累待探索的知识点。
          {status === "complete" && (
            <span className="ml-2 text-green-600 dark:text-green-400">已解决</span>
          )}
        </CardContent>
      </Card>
    );
  }

  return null;
}
