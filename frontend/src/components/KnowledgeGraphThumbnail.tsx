import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  ReactFlow,
  Background,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeProps,
  Handle,
  Position,
  ConnectionMode,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Loader2, Compass } from "lucide-react";
import type {
  KnowledgeContextNode,
  KnowledgeContextEdge,
} from "@/services/api";
import { masteryColors } from "@/pages/graph/constants";

function ThumbnailNode({ data }: NodeProps) {
  const nodeData = data as unknown as KnowledgeContextNode & { isCenter?: boolean };
  const bgColor = masteryColors[nodeData.mastery] || "#9ca3af";
  const isCenter = nodeData.isCenter === true;

  return (
    <div
      className={`rounded-md border shadow cursor-pointer transition-transform hover:scale-105 ${
        isCenter
          ? "border-yellow-400 ring-1 ring-yellow-300/50"
          : "border-white/20"
      }`}
      style={{ backgroundColor: bgColor, minWidth: 50, maxWidth: 90 }}
    >
      <Handle type="target" position={Position.Top} className="!bg-white/30 !w-1 !h-1" />
      <div className="px-2 py-1 text-center">
        <div
          className="text-[10px] font-semibold text-white truncate"
          title={nodeData.name}
        >
          {nodeData.name}
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-white/30 !w-1 !h-1" />
    </div>
  );
}

const nodeTypes = { thumbnail: ThumbnailNode };

function layoutThumbnailNodes(
  nodes: KnowledgeContextNode[],
  centerConcepts: Set<string>
): Node[] {
  if (nodes.length === 0) return [];
  const radius = Math.max(60, nodes.length * 20);
  return nodes.map((node, i) => {
    const angle = (2 * Math.PI * i) / nodes.length;
    return {
      id: node.id,
      type: "thumbnail",
      position: { x: radius * Math.cos(angle), y: radius * Math.sin(angle) },
      data: { ...node, isCenter: centerConcepts.has(node.id) },
    };
  });
}

function buildThumbnailEdges(edges: KnowledgeContextEdge[]): Edge[] {
  return edges.map((e, i) => ({
    id: `te-${i}`,
    source: e.source,
    target: e.target,
    style: { stroke: "#94a3b8", strokeWidth: 1 },
  }));
}

interface KnowledgeGraphThumbnailProps {
  nodes: KnowledgeContextNode[];
  edges: KnowledgeContextEdge[];
  centerConcepts: string[];
  loading?: boolean;
}

export function KnowledgeGraphThumbnail({
  nodes: contextNodes,
  edges: contextEdges,
  centerConcepts,
  loading,
}: KnowledgeGraphThumbnailProps) {
  const navigate = useNavigate();

  const centerSet = useMemo(
    () => new Set(centerConcepts),
    [centerConcepts]
  );

  const [flowNodes, , onNodesChange] = useNodesState<Node>(
    useMemo(
      () => layoutThumbnailNodes(contextNodes, centerSet),
      [contextNodes, centerSet]
    )
  );

  const [flowEdges, , onEdgesChange] = useEdgesState<Edge>(
    useMemo(() => buildThumbnailEdges(contextEdges), [contextEdges])
  );

  const handleNodeClick = (_: React.MouseEvent, node: Node) => {
    const name = (node.data as unknown as KnowledgeContextNode).name;
    if (name) navigate(`/graph?focus=${encodeURIComponent(name)}`);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-40">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (contextNodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-40 gap-2">
        <Compass className="h-8 w-8 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">暂无关联概念</p>
        <p className="text-xs text-muted-foreground">
          添加标签可自动生成知识图谱关联
        </p>
      </div>
    );
  }

  return (
    <div className="w-full h-48 md:h-56 overflow-hidden rounded-lg">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        connectionMode={ConnectionMode.Loose}
        fitView
        minZoom={0.3}
        maxZoom={1.5}
        proOptions={{ hideAttribution: true }}
        className="bg-muted/30"
      >
        <Background color="#e2e8f0" gap={16} size={0.5} />
      </ReactFlow>
    </div>
  );
}
