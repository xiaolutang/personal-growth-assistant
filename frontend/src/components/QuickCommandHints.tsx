/**
 * 快捷命令提示组件
 * 在输入框聚焦时显示可用的命令列表
 */

import { useState } from "react";
import { ChevronUp, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { intentConfig, intentIcons, type Intent } from "@/lib/intentDetection";

// 命令示例映射
const COMMAND_EXAMPLES: Record<Intent, string> = {
  create: "明天下午3点开会",
  read: "帮我找 MCP 的笔记",
  update: "把 MCP 笔记改为完成",
  delete: "删除测试任务",
  review: "今天做了什么",
  knowledge: "MCP 的知识图谱",
  help: "能做什么",
};

// 命令分组
const COMMAND_GROUPS: Record<string, Intent[]> = {
  "操作": ["create", "read", "update", "delete"],
  "功能": ["review", "knowledge", "help"],
};

// 命令定义（从 intentConfig 动态生成）
const COMMANDS = Object.keys(intentConfig).map((intent) => ({
  intent: intent as Intent,
  label: intentConfig[intent as Intent].label,
  example: COMMAND_EXAMPLES[intent as Intent],
  group: Object.entries(COMMAND_GROUPS).find(([, intents]) => intents.includes(intent as Intent))?.[0] || "其他",
}));

interface QuickCommandHintsProps {
  isVisible: boolean;
  onSelectCommand?: (example: string) => void;
  className?: string;
}

export function QuickCommandHints({ isVisible, onSelectCommand, className }: QuickCommandHintsProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!isVisible) return null;

  // 按组分组
  const groupedCommands = COMMANDS.reduce((acc, cmd) => {
    if (!acc[cmd.group]) acc[cmd.group] = [];
    acc[cmd.group].push(cmd);
    return acc;
  }, {} as Record<string, typeof COMMANDS>);

  return (
    <div className={cn("bg-muted/80 backdrop-blur-sm border-t border-border", className)}>
      {/* 折叠/展开按钮 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-center gap-1 py-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        {isExpanded ? (
          <>
            <ChevronDown className="h-3 w-3" />
            收起命令提示
          </>
        ) : (
          <>
            <ChevronUp className="h-3 w-3" />
            查看可用命令
          </>
        )}
      </button>

      {/* 命令列表 */}
      {isExpanded && (
        <div className="px-3 pb-2 space-y-2">
          {Object.entries(groupedCommands).map(([group, commands]) => (
            <div key={group}>
              <div className="text-xs font-medium text-muted-foreground mb-1">{group}</div>
              <div className="flex flex-wrap gap-2">
                {commands.map((cmd) => {
                  const Icon = intentIcons[cmd.intent];
                  return (
                    <button
                      key={cmd.label}
                      onClick={() => onSelectCommand?.(cmd.example)}
                      className="flex items-center gap-1.5 px-2 py-1 text-xs rounded-md bg-background hover:bg-primary/10 hover:text-primary transition-colors border border-border"
                    >
                      <Icon className="h-3 w-3" />
                      <span className="font-medium">{cmd.label}</span>
                      <span className="text-muted-foreground hidden sm:inline">: {cmd.example}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// 简洁版命令提示（用于输入框下方）
interface CommandHintBarProps {
  isVisible: boolean;
  className?: string;
}

export function CommandHintBar({ isVisible, className }: CommandHintBarProps) {
  if (!isVisible) return null;

  // 只显示前4个命令
  const visibleCommands = COMMANDS.slice(0, 4);

  return (
    <div className={cn("flex items-center gap-2 px-2 py-1 text-xs text-muted-foreground overflow-x-auto", className)}>
      {visibleCommands.map((cmd) => {
        const Icon = intentIcons[cmd.intent];
        return (
          <span key={cmd.label} className="flex items-center gap-1 whitespace-nowrap">
            <Icon className="h-3 w-3" />
            {cmd.label}
          </span>
        );
      })}
      <span className="text-primary">输入"帮助"查看更多</span>
    </div>
  );
}

export default QuickCommandHints;
