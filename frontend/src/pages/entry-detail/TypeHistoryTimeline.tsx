import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { History } from "lucide-react";
import { categoryConfig } from "@/config/constants";
import type { Task } from "@/types/task";

interface TypeHistoryTimelineProps {
  typeHistory: Task["type_history"];
}

function getCategoryLabel(category: string): string {
  return (categoryConfig as Record<string, { label: string }>)[category]?.label ?? category;
}

export function TypeHistoryTimeline({ typeHistory }: TypeHistoryTimelineProps) {
  if (!typeHistory || typeHistory.length === 0) return null;

  return (
    <Card className="mb-6">
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <History className="h-4 w-4" />
          类型变更记录
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {typeHistory.map((item, idx) => (
            <div key={idx} className="flex items-center gap-3 text-sm">
              <div className="flex-shrink-0 w-2 h-2 rounded-full bg-muted-foreground/40" />
              <div className="flex-1 flex items-center gap-2">
                <span className="font-medium">
                  {getCategoryLabel(item.from_category)} → {getCategoryLabel(item.to_category)}
                </span>
                <span className="text-muted-foreground">
                  {new Date(item.at).toLocaleString()}
                </span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
