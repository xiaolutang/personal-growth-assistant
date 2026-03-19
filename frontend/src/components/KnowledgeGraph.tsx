import { useCallback, useMemo, useState } from "react";
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  Position,
  Handle,
} from "@xyflow/react";
import type { Node, Edge } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Circle, ArrowRight, GitBranch, Expand, Shrink, RotateCcw } from "lucide-react";
import type { KnowledgeGraphResponse } from "@/types/task";

interface KnowledgeGraphProps {
  data: KnowledgeGraphResponse;
  onConceptClick?: (concept: string) => void;
}

// 自定义节点组件
function ConceptNode({ data }: { data: { label: string; category?: string; isCenter?: boolean; onClick?: () => void } }) {
  return (
    <div
      className={`px-4 py-2 rounded-lg border-2 cursor-pointer transition-all ${
        data.isCenter
          ? "bg-primary text-primary-foreground border-primary shadow-lg"
          : "bg-card border-border hover:border-primary hover:shadow-md"
      }`}
      onClick={data.onClick}
    >
      <Handle type="target" position={Position.Top} className="!bg-transparent !border-0" />
      <div className="flex items-center gap-2">
        <span className="font-medium text-sm">{data.label}</span>
        {data.category && !data.isCenter && (
          <Badge variant="secondary" className="text-xs">
            {data.category}
          </Badge>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-transparent !border-0" />
    </div>
  );
}

const nodeTypes = {
  concept: ConceptNode,
};

export function KnowledgeGraph({ data, onConceptClick }: KnowledgeGraphProps) {
  const { center, connections } = data;
  const [isExpanded, setIsExpanded] = useState(false);

  // 将数据转换为 ReactFlow 节点和边
  const { initialNodes, initialEdges } = useMemo(() => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];

    // 中心节点
    if (center) {
      nodes.push({
        id: center.name,
        type: "concept",
        position: { x: 400, y: 50 },
        data: {
          label: center.name,
          category: center.category,
          isCenter: true,
          onClick: () => onConceptClick?.(center.name),
        },
      });
    }

    // 连接节点（圆形布局）
    const nodeCount = connections.length;
    const radius = 200;

    connections.forEach((conn, index) => {
      const angle = (2 * Math.PI * index) / nodeCount - Math.PI / 2;
      const x = 400 + radius * Math.cos(angle);
      const y = 250 + radius * Math.sin(angle);

      nodes.push({
        id: conn.name,
        type: "concept",
        position: { x, y },
        data: {
          label: conn.name,
          category: conn.category,
          onClick: () => onConceptClick?.(conn.name),
        },
      });

      // 添加边
      if (center) {
        edges.push({
          id: `${center.name}-${conn.name}`,
          source: center.name,
          target: conn.name,
          label: conn.relationship,
          animated: true,
          style: { stroke: "#888" },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: "#888",
          },
        });
      }
    });

    return { initialNodes: nodes, initialEdges: edges };
  }, [center, connections, onConceptClick]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // 重置布局
  const handleReset = useCallback(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  if (!center && connections.length === 0) {
    return (
      <Card className="p-4">
        <div className="text-center text-muted-foreground">
          没有找到相关知识图谱
        </div>
      </Card>
    );
  }

  const graphContent = (
    <div className="relative" style={{ height: isExpanded ? 500 : 300 }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
        className="bg-muted/30 rounded-lg"
      >
        <Background gap={16} size={1} />
        <Controls showInteractive={false} />
      </ReactFlow>

      {/* 控制按钮 */}
      <div className="absolute top-2 right-2 flex gap-1">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsExpanded(!isExpanded)}
          title={isExpanded ? "收缩" : "展开"}
        >
          {isExpanded ? <Shrink className="h-4 w-4" /> : <Expand className="h-4 w-4" />}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={handleReset}
          title="重置布局"
        >
          <RotateCcw className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );

  return (
    <Card>
      {/* Center Concept */}
      {center && (
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Circle className="h-5 w-5 text-primary fill-primary/20" />
            <CardTitle className="text-lg">{center.name}</CardTitle>
            {center.category && (
              <Badge variant="secondary" className="text-xs">
                {center.category}
              </Badge>
            )}
          </div>
          {center.description && (
            <p className="text-sm text-muted-foreground mt-1">
              {center.description}
            </p>
          )}
        </CardHeader>
      )}

      {/* Graph */}
      <CardContent className="pt-0">
        <div className="text-xs text-muted-foreground mb-2 flex items-center gap-1">
          <GitBranch className="h-3 w-3" />
          相关概念 ({connections.length})
        </div>
        {graphContent}
      </CardContent>
    </Card>
  );
}

// 简化版知识图谱（用于聊天消息中）- 保持列表形式
interface KnowledgeGraphInlineProps {
  data: KnowledgeGraphResponse;
  onConceptClick?: (concept: string) => void;
}

export function KnowledgeGraphInline({ data, onConceptClick }: KnowledgeGraphInlineProps) {
  const { center, connections } = data;

  if (!center && connections.length === 0) {
    return <span className="text-muted-foreground">没有找到相关知识图谱</span>;
  }

  return (
    <div className="bg-muted/50 rounded-lg p-3 space-y-2">
      {/* Center */}
      {center && (
        <div className="flex items-center gap-2">
          <Circle className="h-4 w-4 text-primary fill-primary/20" />
          <span className="font-medium">{center.name}</span>
          {center.category && (
            <Badge variant="secondary" className="text-xs">
              {center.category}
            </Badge>
          )}
        </div>
      )}

      {/* Connections */}
      {connections.length > 0 && (
        <div className="pl-6 space-y-1">
          {connections.slice(0, 5).map((conn, index) => (
            <div
              key={`${conn.name}-${index}`}
              className="flex items-center gap-2 text-sm cursor-pointer hover:text-primary"
              onClick={() => onConceptClick?.(conn.name)}
            >
              <ArrowRight className="h-3 w-3 text-muted-foreground" />
              <span>{conn.name}</span>
              <span className="text-xs text-muted-foreground">
                ({conn.relationship})
              </span>
            </div>
          ))}
          {connections.length > 5 && (
            <div className="text-xs text-muted-foreground">
              还有 {connections.length - 5} 个相关概念...
            </div>
          )}
        </div>
      )}
    </div>
  );
}
