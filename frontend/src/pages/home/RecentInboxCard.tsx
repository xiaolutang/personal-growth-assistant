import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Lightbulb, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import type { Task } from "@/types/task";

interface RecentInboxCardProps {
  unprocessedCount: number;
  recentInbox: Task[];
  convertingId: string | null;
  onConvert: (e: React.MouseEvent, id: string, title: string, targetCategory: "task" | "note") => void;
}

export function RecentInboxCard({ unprocessedCount, recentInbox, convertingId, onConvert }: RecentInboxCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Lightbulb className="h-4 w-4 text-yellow-500 dark:text-yellow-400" />
          最近灵感
          {unprocessedCount > 0 && (
            <span className="inline-flex items-center justify-center h-5 min-w-[20px] rounded-full bg-primary px-1.5 text-[10px] font-medium text-primary-foreground">
              {unprocessedCount}
            </span>
          )}
        </CardTitle>
        {recentInbox.length > 0 && (
          <Link
            to="/explore?type=inbox"
            className="flex items-center text-xs text-muted-foreground hover:text-primary transition-colors"
          >
            查看全部
            <ArrowRight className="ml-0.5 h-3 w-3" />
          </Link>
        )}
      </CardHeader>
      <CardContent>
        {recentInbox.length > 0 ? (
          <div className="space-y-1">
            {recentInbox.map((item) => (
              <div
                key={item.id}
                className="flex items-center gap-1 rounded-lg px-2 py-1.5 hover:bg-accent/50 transition-colors group"
              >
                {item._offlinePending ? (
                  <span className="flex items-center gap-2 flex-1 min-w-0 cursor-default">
                    <Lightbulb className="h-3.5 w-3.5 text-yellow-500 dark:text-yellow-400 shrink-0" />
                    <span className="text-sm truncate">{item.title}</span>
                    <span className="inline-flex items-center rounded-full bg-orange-100 px-1.5 py-0.5 text-[10px] text-orange-700 dark:bg-orange-900/30 dark:text-orange-400 shrink-0">
                      待同步
                    </span>
                  </span>
                ) : (
                  <>
                    <Link
                      to={`/entries/${item.id}`}
                      className="flex items-center gap-2 flex-1 min-w-0"
                    >
                      <Lightbulb className="h-3.5 w-3.5 text-yellow-500 dark:text-yellow-400 shrink-0" />
                      <span className="text-sm truncate">{item.title}</span>
                      {item.status !== "complete" && (
                        <span className="text-[10px] text-muted-foreground shrink-0">
                          {new Date(item.created_at).toLocaleDateString("zh-CN", {
                            month: "short",
                            day: "numeric",
                          })}
                        </span>
                      )}
                    </Link>
                    <div className="flex items-center gap-0.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={(e) => onConvert(e, item.id, item.title, "task")}
                        disabled={convertingId === item.id}
                        className="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/50 disabled:opacity-50 transition-colors"
                      >
                        {convertingId === item.id ? "..." : "转任务"}
                      </button>
                      <button
                        onClick={(e) => onConvert(e, item.id, item.title, "note")}
                        disabled={convertingId === item.id}
                        className="text-[10px] px-1.5 py-0.5 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-900/50 disabled:opacity-50 transition-colors"
                      >
                        {convertingId === item.id ? "..." : "转笔记"}
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="py-4 text-center text-sm text-muted-foreground">
            暂无灵感记录
          </p>
        )}
      </CardContent>
    </Card>
  );
}
