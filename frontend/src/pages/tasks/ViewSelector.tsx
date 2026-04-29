import { List, FolderTree } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ViewKey, ViewOption } from "./constants";

/** Default view options — F09 can extend with { key: "timeline", label: "时间线" } */
const DEFAULT_VIEW_OPTIONS: ViewOption[] = [
  { key: "list", label: "列表", icon: <List className="h-4 w-4" /> },
  { key: "grouped", label: "按项目", icon: <FolderTree className="h-4 w-4" /> },
];

interface ViewSelectorProps {
  options?: ViewOption[];
  activeView: ViewKey;
  onViewChange: (view: ViewKey) => void;
}

export function ViewSelector({ options = DEFAULT_VIEW_OPTIONS, activeView, onViewChange }: ViewSelectorProps) {
  return (
    <div className="flex items-center gap-1" data-testid="view-selector">
      {options.map((opt) => (
        <button
          key={opt.key}
          data-active={activeView === opt.key}
          onClick={() => onViewChange(opt.key as ViewKey)}
          className={cn(
            "flex items-center gap-1 px-2.5 py-1 text-xs rounded-md transition-colors",
            activeView === opt.key
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-muted"
          )}
        >
          {opt.icon}
          {opt.label}
        </button>
      ))}
    </div>
  );
}
