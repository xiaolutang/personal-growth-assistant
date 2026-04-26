import { useState, useEffect, useCallback } from "react";
import { FileText, Plus, Loader2 } from "lucide-react";
import { fetchTemplates, type EntryTemplate } from "@/services/api";

interface TemplateSelectorProps {
  /** 当前选中的 category tab，仅 category=note 时显示模板选择器 */
  activeTab: string;
  /** 选择模板后的回调：传入模板内容 */
  onTemplateSelected: (template: EntryTemplate) => void;
}

export function TemplateSelector({ activeTab, onTemplateSelected }: TemplateSelectorProps) {
  const [templates, setTemplates] = useState<EntryTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // 只在 note tab 时加载模板
  const shouldShow = activeTab === "note";

  const loadTemplates = useCallback(async () => {
    if (!shouldShow) return;
    setLoading(true);
    try {
      const res = await fetchTemplates("note");
      setTemplates(res.templates ?? []);
    } catch {
      // 静默降级，不阻塞创建流程
      setTemplates([]);
    } finally {
      setLoading(false);
    }
  }, [shouldShow]);

  useEffect(() => {
    if (shouldShow) {
      loadTemplates();
    }
  }, [shouldShow, loadTemplates]);

  // 切换 tab 时重置选择状态
  useEffect(() => {
    setSelectedId(null);
  }, [activeTab]);

  if (!shouldShow) return null;
  if (loading) {
    return (
      <div className="flex items-center gap-2 px-1 py-2 text-sm text-muted-foreground">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        加载模板...
      </div>
    );
  }
  if (templates.length === 0) return null;

  const handleSelect = (template: EntryTemplate) => {
    const newSelectedId = selectedId === template.id ? null : template.id;
    setSelectedId(newSelectedId);
    if (newSelectedId) {
      onTemplateSelected(template);
    }
  };

  return (
    <div className="space-y-2 mb-4">
      <div className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
        <FileText className="h-3.5 w-3.5" />
        选择模板快速创建笔记
      </div>
      <div className="flex gap-2 overflow-x-auto scrollbar-hide">
        {templates.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => handleSelect(t)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors border ${
              selectedId === t.id
                ? "bg-indigo-500 text-white border-indigo-500"
                : "bg-background border-border text-muted-foreground hover:text-foreground hover:bg-muted/50"
            }`}
          >
            <Plus className="h-3 w-3" />
            {t.name}
          </button>
        ))}
      </div>
      {selectedId && (
        <p className="text-xs text-muted-foreground">
          {templates.find((t) => t.id === selectedId)?.description}
        </p>
      )}
    </div>
  );
}
