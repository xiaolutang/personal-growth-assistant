import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Brain } from "lucide-react";
import {
  getKnowledgeHeatmap,
  type HeatmapItem,
} from "@/services/api";

// 掌握度颜色映射
const MASTERY_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  advanced: { bg: "bg-purple-100 dark:bg-purple-900/30", text: "text-purple-700 dark:text-purple-300", label: "精通" },
  intermediate: { bg: "bg-blue-100 dark:bg-blue-900/30", text: "text-blue-700 dark:text-blue-300", label: "中级" },
  beginner: { bg: "bg-green-100 dark:bg-green-900/30", text: "text-green-700 dark:text-green-300", label: "入门" },
  new: { bg: "bg-gray-100 dark:bg-gray-800/30", text: "text-gray-600 dark:text-gray-400", label: "新知" },
};

export function HeatmapCard() {
  const [heatmapItems, setHeatmapItems] = useState<HeatmapItem[]>([]);
  const [heatmapLoading, setHeatmapLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const fetchHeatmap = async () => {
      setHeatmapLoading(true);
      try {
        const data = await getKnowledgeHeatmap();
        if (!cancelled) setHeatmapItems(data.items ?? []);
      } catch (err) {
        if (!cancelled) console.error("获取知识热力图失败:", err);
      } finally {
        if (!cancelled) setHeatmapLoading(false);
      }
    };

    fetchHeatmap();

    return () => { cancelled = true; };
  }, []);

  // 按 category 分组（category 为 null 的归入"其他"）
  const grouped = heatmapItems.reduce<Record<string, HeatmapItem[]>>((acc, item) => {
    const cat = item.category || "其他";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(item);
    return acc;
  }, {});
  const categories = Object.keys(grouped);
  const hasCategory = categories.length > 1 || (categories.length === 1 && categories[0] !== "其他");

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Brain className="h-4 w-4" />
          知识热力图
        </CardTitle>
      </CardHeader>
      <CardContent>
        {heatmapLoading ? (
          <div className="flex flex-wrap gap-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-7 w-20 bg-muted rounded-full animate-pulse" />
            ))}
          </div>
        ) : heatmapItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Brain className="h-8 w-8 text-muted-foreground/40 mb-2" />
            <p className="text-sm text-muted-foreground">记录更多内容，知识图谱将自动丰富</p>
          </div>
        ) : (
          <>
            {/* 掌握度图例 */}
            <div className="flex flex-wrap gap-3 mb-3 text-xs text-muted-foreground">
              {Object.entries(MASTERY_STYLES).map(([key, style]) => (
                <span key={key} className="flex items-center gap-1">
                  <span className={`inline-block w-2.5 h-2.5 rounded-full ${style.bg}`} />
                  {style.label}
                </span>
              ))}
            </div>
            {/* 按 category 分组展示 */}
            {hasCategory ? (
              <div className="space-y-3">
                {categories.map((cat) => (
                  <div key={cat}>
                    <div className="text-xs font-medium text-muted-foreground mb-1.5">{cat}</div>
                    <div className="flex flex-wrap gap-2">
                      {grouped[cat].map((item) => {
                        const style = MASTERY_STYLES[item.mastery] || MASTERY_STYLES.new;
                        return (
                          <span
                            key={item.concept}
                            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${style.bg} ${style.text}`}
                          >
                            {item.concept}
                            <span className="opacity-60">({item.entry_count})</span>
                          </span>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              /* 无分类信息时保持原标签云布局（降级兼容） */
              <div className="flex flex-wrap gap-2">
                {heatmapItems.map((item) => {
                  const style = MASTERY_STYLES[item.mastery] || MASTERY_STYLES.new;
                  return (
                    <span
                      key={item.concept}
                      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${style.bg} ${style.text}`}
                    >
                      {item.concept}
                      <span className="opacity-60">({item.entry_count})</span>
                    </span>
                  );
                })}
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

export { HeatmapCard as default };
