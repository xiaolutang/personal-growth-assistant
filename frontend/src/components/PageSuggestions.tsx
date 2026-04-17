import type { PageContext } from "@/stores/chatStore";

interface PageSuggestionsProps {
  pageContext: PageContext | null;
  onSuggestionClick: (text: string) => void;
  hasMessages: boolean;
}

const PAGE_SUGGESTIONS: Record<string, string[]> = {
  home: ["今日有哪些任务?", "帮我记个想法", "整理待办"],
  explore: ["最近学了什么?", "搜索相关笔记"],
  entry: ["帮我补充内容", "关联到其他条目"],
  review: ["本周完成率?", "生成本月总结"],
  graph: ["我的知识图谱有哪些概念?", "搜索相关概念"],
};

export default function PageSuggestions({
  pageContext,
  onSuggestionClick,
  hasMessages,
}: PageSuggestionsProps) {
  if (hasMessages || !pageContext) return null;

  const suggestions = PAGE_SUGGESTIONS[pageContext.page_type];
  if (!suggestions) return null;

  return (
    <div className="flex flex-wrap gap-1.5 px-3 pt-2">
      {suggestions.map((text) => (
        <button
          key={text}
          type="button"
          onClick={() => onSuggestionClick(text)}
          className="rounded-full border border-gray-200 bg-white px-2.5 py-1 text-xs text-gray-600 transition-colors hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700"
        >
          {text}
        </button>
      ))}
    </div>
  );
}
