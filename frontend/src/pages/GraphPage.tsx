import { useState, useEffect, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeProps,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Link } from "react-router-dom";
import { Loader2, X, AlertCircle, Compass } from "lucide-react";
import { Header } from "@/components/layout/Header";
import {
  getKnowledgeMap,
  getKnowledgeStats,
  type MapNode,
  type MapEdge,
  type KnowledgeMapResponse,
  type ConceptStatsResponse,
} from "@/services/api";

// === 掌握度颜色映射 ===
const masteryColors: Record<string, string> = {
  advanced: "#22c55e",
  intermediate: "#3b82f6",
  beginner: "#f97316",
  new: "#9ca3af",
};

const masteryLabels: Record<string, string> = {
  advanced: "精通",
  intermediate: "熟练",
  beginner: "入门",
  new: "新概念",
};

const masterySuggestions: Record<string, string> = {
  advanced: "你已经精通这个概念，可以尝试教授他人或挑战更高难度的应用。",
  intermediate: "你正在稳步进步，继续保持实践和深入探索。",
  beginner: "刚刚开始接触，建议多阅读相关资料并动手实践。",
  new: "这是一个新的知识领域，建议从基础概念开始了解。",
};

// === 视角 Tab 配置 ===
const viewTabs = [
  { key: "domain", label: "领域" },
  { key: "mastery", label: "掌握度" },
  { key: "project", label: "项目" },
] as const;

type ViewKey = (typeof viewTabs)[number]["key"];

// === 自定义节点组件 ===
function ConceptNode({ data }: NodeProps) {
  const nodeData = data as unknown as MapNode;
  const bgColor = masteryColors[nodeData.mastery] || "#9ca3af";

  return (
    <div
      className="rounded-lg border-2 border-white/30 shadow-lg cursor-pointer transition-transform hover:scale-105"
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

const nodeTypes = { concept: ConceptNode };

// === 布局：圆形排列 ===
function layoutNodes(nodes: MapNode[]): Node[] {
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

function buildEdges(edges: MapEdge[]): Edge[] {
  return edges.map((e, i) => ({
    id: `e-${i}`,
    source: e.source,
    target: e.target,
    label: e.relationship,
    animated: false,
    style: { stroke: "#94a3b8", strokeWidth: 1.5 },
    labelStyle: { fontSize: 10, fill: "#64748b" },
  }));
}

// === 详情面板 ===
function DetailPanel({
  node,
  stats,
  onClose,
}: {
  node: MapNode;
  stats: ConceptStatsResponse | null;
  onClose: () => void;
}) {
  return (
    <>
      {/* 移动端：底部抽屉 */}
      <div className="fixed inset-0 bg-black/50 z-40 md:hidden" onClick={onClose} />
      <div className="fixed bottom-0 left-0 right-0 bg-card border-t rounded-t-xl p-4 z-50 md:hidden max-h-[50vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-base truncate">{node.name}</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>
        <DetailPanelContent node={node} stats={stats} />
      </div>

      {/* 桌面端：右侧面板 */}
      <div className="hidden md:flex w-72 border-l bg-card p-4 flex-col gap-4 overflow-y-auto">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-base truncate">{node.name}</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>
        <DetailPanelContent node={node} stats={stats} />
      </div>
    </>
  );
}

function DetailPanelContent({
  node,
  stats,
}: {
  node: MapNode;
  stats: ConceptStatsResponse | null;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span
          className="inline-block w-3 h-3 rounded-full"
          style={{ backgroundColor: masteryColors[node.mastery] }}
        />
        <span className="text-sm">{masteryLabels[node.mastery] || node.mastery}</span>
      </div>

      {node.category && (
        <div>
          <span className="text-xs text-muted-foreground">分类：</span>
          <span className="text-sm ml-1">{node.category}</span>
        </div>
      )}

      <div>
        <span className="text-xs text-muted-foreground">关联条目：</span>
        <span className="text-sm ml-1">{node.entry_count} 条</span>
      </div>

      <div className="pt-2 border-t">
        <p className="text-sm text-muted-foreground leading-relaxed">
          {masterySuggestions[node.mastery] || "继续学习这个概念。"}
        </p>
      </div>

      {stats && (
        <div className="pt-4 border-t space-y-2">
          <p className="text-xs font-medium text-muted-foreground">图谱统计</p>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <p className="text-lg font-semibold">{stats.concept_count}</p>
              <p className="text-xs text-muted-foreground">概念</p>
            </div>
            <div>
              <p className="text-lg font-semibold">{stats.relation_count}</p>
              <p className="text-xs text-muted-foreground">关系</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// === 主页面 ===
export function GraphPage() {
  const [activeView, setActiveView] = useState<ViewKey>("domain");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mapData, setMapData] = useState<KnowledgeMapResponse | null>(null);
  const [stats, setStats] = useState<ConceptStatsResponse | null>(null);
  const [selectedNode, setSelectedNode] = useState<MapNode | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // 加载图谱数据
  const loadMap = useCallback(async (view: ViewKey) => {
    setLoading(true);
    setError(null);
    setSelectedNode(null);
    try {
      const [mapResult, statsResult] = await Promise.all([
        getKnowledgeMap(2, view),
        getKnowledgeStats(),
      ]);
      setMapData(mapResult);
      setStats(statsResult);
      setNodes(layoutNodes(mapResult.nodes));
      setEdges(buildEdges(mapResult.edges));
    } catch (err: any) {
      setError(err.message || "加载图谱失败");
    } finally {
      setLoading(false);
    }
  }, [setNodes, setEdges]);

  useEffect(() => {
    loadMap(activeView);
  }, [activeView, loadMap]);

  // 点击节点
  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const mapNode = node.data as unknown as MapNode;
      setSelectedNode(mapNode);
    },
    []
  );

  // 点击画布空白处
  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  // MiniMap 节点颜色
  const miniMapNodeColor = useCallback((node: Node) => {
    const data = node.data as unknown as MapNode;
    return masteryColors[data.mastery] || "#9ca3af";
  }, []);

  const isEmpty = !loading && !error && mapData && mapData.nodes.length === 0;

  return (
    <div className="flex flex-1 flex-col h-[calc(100vh-0px)]">
      <Header title="知识图谱" />

      {/* Tab 栏 */}
      <div className="flex items-center border-b px-4 md:px-6 gap-1 bg-card">
        {viewTabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveView(tab.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeView === tab.key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 主内容区 */}
      <div className="flex flex-1 overflow-hidden">
        {/* 画布区 */}
        <div className="flex-1 relative">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          )}

          {error && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 z-10">
              <AlertCircle className="h-10 w-10 text-destructive" />
              <p className="text-sm text-destructive">{error}</p>
              <button
                onClick={() => loadMap(activeView)}
                className="text-sm text-primary hover:underline"
              >
                重试
              </button>
            </div>
          )}

          {isEmpty && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 z-10">
              <Compass className="h-12 w-12 text-muted-foreground" />
              <p className="text-base text-muted-foreground">
                开始记录你的学习旅程，知识图谱将自动生成
              </p>
              <Link
                to="/explore"
                className="text-sm text-primary hover:underline"
              >
                去探索
              </Link>
            </div>
          )}

          {!isEmpty && (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              onPaneClick={onPaneClick}
              nodeTypes={nodeTypes}
              fitView
              minZoom={0.2}
              maxZoom={2}
              className="bg-background"
            >
              <Background color="#e2e8f0" gap={20} size={1} />
              <Controls className="!bg-card !border !shadow-md" />
              <MiniMap
                nodeColor={miniMapNodeColor}
                className="!bg-card !border !shadow-md"
                maskColor="rgba(0,0,0,0.1)"
              />
            </ReactFlow>
          )}
        </div>

        {/* 详情面板 */}
        {selectedNode && (
          <DetailPanel
            node={selectedNode}
            stats={stats}
            onClose={() => setSelectedNode(null)}
          />
        )}
      </div>
    </div>
  );
}
