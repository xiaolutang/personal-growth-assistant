import {
  type NodeProps,
  Handle,
  Position,
} from "@xyflow/react";
import type { MapNode } from "@/services/api";
import { masteryColors } from "./constants";

// === 自定义节点组件 ===
export function ConceptNode({ data }: NodeProps) {
  const nodeData = data as unknown as MapNode & { highlighted?: boolean };
  const bgColor = masteryColors[nodeData.mastery] || "#9ca3af";
  const isHighlighted = nodeData.highlighted === true;

  return (
    <div
      className={`rounded-lg border-2 shadow-lg cursor-pointer transition-all hover:scale-105 ${
        isHighlighted
          ? "border-yellow-400 ring-2 ring-yellow-300/60 scale-110"
          : "border-white/30"
      }`}
      style={{ backgroundColor: bgColor, minWidth: 80, maxWidth: 140 }}
    >
      <Handle type="target" position={Position.Top} className="!bg-white/50" />
      <div className="px-3 py-2 text-center">
        <div className="text-xs font-bold text-white truncate" title={nodeData.name}>
          {nodeData.name}
        </div>
        {nodeData.entry_count > 0 && (
          <div className="text-[10px] text-white/80 mt-0.5">
            {nodeData.entry_count} 条记录
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-white/50" />
    </div>
  );
}

// === 聚合节点组件 ===
export function AggregateNode({ data }: NodeProps) {
  const nodeData = data as unknown as { name: string; count: number; category: string };
  return (
    <div
      className="rounded-lg border-2 border-dashed border-gray-400 shadow-lg cursor-pointer transition-transform hover:scale-105 bg-gray-200 dark:bg-gray-700"
      style={{ minWidth: 100, maxWidth: 160 }}
    >
      <Handle type="target" position={Position.Top} className="!bg-white/50" />
      <div className="px-3 py-2 text-center">
        <div className="text-xs font-bold text-gray-700 dark:text-gray-200 truncate">{nodeData.name}</div>
        <div className="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5">
          {nodeData.count} 个节点
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-white/50" />
    </div>
  );
}

export const nodeTypes = { concept: ConceptNode, aggregate: AggregateNode };
