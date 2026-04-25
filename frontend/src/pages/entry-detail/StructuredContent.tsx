import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getMarkdownComponents } from "./MarkdownComponents";

/** 将 Markdown 按 ## 分割成结构化 sections 并以卡片形式渲染 */
export function StructuredContent({ content, category, navigate }: { content: string; category: string; navigate: (path: string) => void }) {
  const sections = content.split(/\n(?=## )/).filter(Boolean);
  if (sections.length === 0) {
    return <div className="prose prose-sm dark:prose-invert max-w-none">{content || "暂无内容"}</div>;
  }

  const sectionLabels: Record<string, Record<string, string>> = {
    decision: {
      "决策背景": "bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800",
      "可选方案": "bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800",
      "最终选择": "bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800",
      "选择理由": "bg-purple-50 dark:bg-purple-950/30 border-purple-200 dark:border-purple-800",
    },
    reflection: {
      "回顾目标": "bg-teal-50 dark:bg-teal-950/30 border-teal-200 dark:border-teal-800",
      "实际结果": "bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800",
      "经验教训": "bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800",
      "下一步行动": "bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800",
    },
    question: {
      "问题描述": "bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800",
      "相关背景": "bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800",
      "思考方向": "bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800",
    },
  };
  const colorMap = sectionLabels[category] || {};

  return (
    <div className="space-y-3">
      {sections.map((section, i) => {
        const match = section.match(/^## (.+)/);
        const title = match ? match[1].trim() : "";
        const body = match ? section.slice(match[0].length).trim() : section.trim();
        const colorClass = colorMap[title] || "bg-muted/50 border-border";

        return (
          <div key={i} className={`rounded-lg border p-4 ${colorClass}`}>
            {title && (
              <h3 className="text-sm font-semibold mb-2">{title}</h3>
            )}
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={getMarkdownComponents(navigate)}
              >
                {body || "（待补充）"}
              </ReactMarkdown>
            </div>
          </div>
        );
      })}
    </div>
  );
}
