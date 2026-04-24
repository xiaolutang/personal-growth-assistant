import {
  type Node,
  type Edge,
} from "@xyflow/react";
import type { MapNode, MapEdge } from "@/services/api";
import { NODE_THRESHOLD } from "./constants";

// === 布局：圆形排列 ===
export function layoutNodes(nodes: MapNode[]): Node[] {
  if (nodes.length === 0) return [];
  const radius = Math.max(200, nodes.length * 30);
  return nodes.map((node, i) => {
    const angle = (2 * Math.PI * i) / nodes.length;
    return {
      id: node.id,
      type: "concept",
      position: { x: radius * Math.cos(angle), y: radius * Math.sin(angle) },
      data: { ...node } as Record<string, unknown>,
    };
  });
}

// 按关联数排序，取 top N
export function getTopNodes(nodes: MapNode[], limit: number): MapNode[] {
  return [...nodes].sort((a, b) => b.entry_count - a.entry_count).slice(0, limit);
}

// 聚合同 category 节点
export function aggregateByCategory(nodes: MapNode[]): { aggregates: Node[]; remaining: MapNode[] } {
  const categoryGroups: Record<string, MapNode[]> = {};
  for (const node of nodes) {
    const cat = node.category || "未分类";
    if (!categoryGroups[cat]) categoryGroups[cat] = [];
    categoryGroups[cat].push(node);
  }

  const aggregates: Node[] = [];
  const remaining: MapNode[] = [];
  let angleIdx = 0;
  const totalAgg = Object.keys(categoryGroups).length;
  const radius = Math.max(200, totalAgg * 40);

  for (const [cat, group] of Object.entries(categoryGroups)) {
    if (group.length > 3) {
      const angle = (2 * Math.PI * angleIdx) / totalAgg;
      aggregates.push({
        id: `agg-${cat}`,
        type: "aggregate",
        position: { x: radius * Math.cos(angle), y: radius * Math.sin(angle) },
        data: { name: cat, count: group.length, category: cat } as Record<string, unknown>,
      });
      angleIdx++;
    } else {
      remaining.push(...group);
    }
  }
  return { aggregates, remaining };
}

export function buildEdges(edges: MapEdge[], hideLabels: boolean): Edge[] {
  return edges.map((e, i) => ({
    id: `e-${i}`,
    source: e.source,
    target: e.target,
    label: hideLabels ? undefined : e.relationship,
    animated: false,
    style: { stroke: "#94a3b8", strokeWidth: 1.5 },
    labelStyle: { fontSize: 10, fill: "#64748b" },
  }));
}

/** 根据 mapData 和控制标志计算应当显示的节点和边 */
export function getDisplayData(
  mapData: { nodes: MapNode[]; edges: MapEdge[] },
  showAllNodes: boolean,
): { displayNodes: MapNode[]; displayEdges: MapEdge[] } {
  const allNodes = mapData.nodes;
  const displayNodes = allNodes.length > NODE_THRESHOLD && !showAllNodes
    ? getTopNodes(allNodes, NODE_THRESHOLD)
    : allNodes;
  const displayNodeIds = new Set(displayNodes.map((n) => n.id));
  const displayEdges = mapData.edges.filter(
    (e) => displayNodeIds.has(e.source) && displayNodeIds.has(e.target),
  );
  return { displayNodes, displayEdges };
}
