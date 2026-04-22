import { useState, useEffect, useCallback, useRef } from "react";
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
import { Link, useSearchParams } from "react-router-dom";
import { Loader2, X, AlertCircle, Compass, Plus, Layers, Search, BarChart3, Clock, FileText, ChevronDown, ChevronUp, Map } from "lucide-react";
import { Header } from "@/components/layout/Header";
import {
  getKnowledgeMap,
  getKnowledgeStats,
  getKnowledgeSearch,
  getConceptTimeline,
  getMasteryDistribution,
  getCapabilityMap,
  type MapNode,
  type MapEdge,
  type KnowledgeMapResponse,
  type ConceptStatsResponse,
  type KnowledgeSearchResponse,
  type ConceptTimelineResponse,
  type MasteryDistributionResponse,
  type CapabilityMapResponse,
} from "@/services/api";
import { PageChatPanel } from "@/components/PageChatPanel";

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
  { key: "capability", label: "能力地图" },
] as const;

type ViewKey = (typeof viewTabs)[number]["key"];

// === 自定义节点组件 ===
function ConceptNode({ data }: NodeProps) {
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

// === 性能优化常量 ===
const NODE_THRESHOLD = 50;
const EDGE_LABEL_THRESHOLD = 100;

// === 聚合节点组件 ===
function AggregateNode({ data }: NodeProps) {
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

const nodeTypes = { concept: ConceptNode, aggregate: AggregateNode };

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

// 按关联数排序，取 top N
function getTopNodes(nodes: MapNode[], limit: number): MapNode[] {
  return [...nodes].sort((a, b) => b.entry_count - a.entry_count).slice(0, limit);
}

// 聚合同 category 节点
function aggregateByCategory(nodes: MapNode[]): { aggregates: Node[]; remaining: MapNode[] } {
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

function buildEdges(edges: MapEdge[], hideLabels: boolean): Edge[] {
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
  // 时间线状态
  const [timeline, setTimeline] = useState<ConceptTimelineResponse | null>(null);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [timelineError, setTimelineError] = useState<string | null>(null);

  useEffect(() => {
    if (!node.name) return;
    let cancelled = false;
    setTimelineLoading(true);
    setTimelineError(null);
    getConceptTimeline(node.name, 30)
      .then((data) => {
        if (!cancelled) setTimeline(data);
      })
      .catch((err: any) => {
        if (!cancelled) setTimelineError(err.message || "加载时间线失败");
      })
      .finally(() => {
        if (!cancelled) setTimelineLoading(false);
      });
    return () => { cancelled = true; };
  }, [node.name]);

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
        <DetailPanelContent node={node} stats={stats} timeline={timeline} timelineLoading={timelineLoading} timelineError={timelineError} />
      </div>

      {/* 桌面端：右侧面板 */}
      <div className="hidden md:flex w-80 border-l bg-card p-4 flex-col gap-4 overflow-y-auto">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-base truncate">{node.name}</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>
        <DetailPanelContent node={node} stats={stats} timeline={timeline} timelineLoading={timelineLoading} timelineError={timelineError} />
      </div>
    </>
  );
}

function DetailPanelContent({
  node,
  stats,
  timeline,
  timelineLoading,
  timelineError,
}: {
  node: MapNode;
  stats: ConceptStatsResponse | null;
  timeline: ConceptTimelineResponse | null;
  timelineLoading: boolean;
  timelineError: string | null;
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

      {/* 学习时间线 */}
      <div className="pt-2 border-t space-y-2">
        <div className="flex items-center gap-1.5">
          <Clock className="h-3.5 w-3.5 text-muted-foreground" />
          <p className="text-xs font-medium text-muted-foreground">学习时间线</p>
        </div>

        {timelineLoading && (
          <div className="flex items-center gap-2 py-2">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            <span className="text-xs text-muted-foreground">加载中...</span>
          </div>
        )}

        {timelineError && (
          <p className="text-xs text-destructive">{timelineError}</p>
        )}

        {timeline && timeline.items.length === 0 && !timelineLoading && (
          <p className="text-xs text-muted-foreground">暂无学习记录</p>
        )}

        {timeline && timeline.items.length > 0 && (
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {timeline.items.map((day) => (
              <div key={day.date} className="space-y-1">
                <p className="text-[10px] font-medium text-muted-foreground">{day.date}</p>
                {day.entries.map((entry) => (
                  <Link
                    key={entry.id}
                    to={`/entries/${entry.id}`}
                    className="flex items-center gap-1.5 px-2 py-1 rounded text-xs hover:bg-accent transition-colors"
                  >
                    <FileText className="h-3 w-3 text-muted-foreground shrink-0" />
                    <span className="truncate">{entry.title}</span>
                  </Link>
                ))}
              </div>
            ))}
          </div>
        )}
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

// === 能力地图视图组件 ===
function CapabilityMapView() {
  const [capabilityMap, setCapabilityMap] = useState<CapabilityMapResponse | null>(null);
  const [capabilityLoading, setCapabilityLoading] = useState(false);
  const [capabilityError, setCapabilityError] = useState<string | null>(null);
  const [expandedDomain, setExpandedDomain] = useState<string | null>(null);
  const [capabilityFilter, setCapabilityFilter] = useState<string>("");
  const [capabilityRetryKey, setCapabilityRetryKey] = useState(0);

  // 加载能力地图数据（带请求取消保护，防止快速切换筛选时旧请求覆盖新结果）
  useEffect(() => {
    let cancelled = false;
    setCapabilityLoading(true);
    setCapabilityError(null);
    setCapabilityMap(null);
    setExpandedDomain(null);
    getCapabilityMap(capabilityFilter || undefined)
      .then((data) => { if (!cancelled) setCapabilityMap(data); })
      .catch((err: any) => { if (!cancelled) setCapabilityError(err.message || "加载能力地图失败"); })
      .finally(() => { if (!cancelled) setCapabilityLoading(false); });
    return () => { cancelled = true; };
  }, [capabilityFilter, capabilityRetryKey]);

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6">
      {capabilityLoading && (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      )}
      {capabilityError && (
        <div className="flex flex-col items-center justify-center h-64 gap-3">
          <AlertCircle className="h-10 w-10 text-destructive" />
          <p className="text-sm text-destructive">{capabilityError}</p>
          <button
            onClick={() => setCapabilityRetryKey((k) => k + 1)}
            className="text-sm text-primary hover:underline"
          >
            重试
          </button>
        </div>
      )}
      {capabilityMap && capabilityMap.domains.length === 0 && !capabilityLoading && (
        <div className="flex flex-col items-center justify-center h-64 gap-4">
          <Map className="h-12 w-12 text-muted-foreground" />
          <p className="text-base text-muted-foreground">
            {capabilityFilter
              ? `没有${masteryLabels[capabilityFilter] || capabilityFilter}级别的概念`
              : "开始记录你的学习旅程，能力地图将自动生成"}
          </p>
          {capabilityFilter ? (
            <button
              onClick={() => setCapabilityFilter("")}
              className="text-sm text-primary hover:underline"
            >
              查看全部
            </button>
          ) : (
            <Link
              to="/explore"
              className="text-sm text-primary hover:underline"
            >
              去探索
            </Link>
          )}
        </div>
      )}
      {capabilityMap && (
        <>
        {/* 掌握度筛选 */}
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs text-muted-foreground">筛选：</span>
          {(["", "advanced", "intermediate", "beginner", "new"] as const).map((level) => (
            <button
              key={level}
              onClick={() => setCapabilityFilter(level)}
              className={`px-2.5 py-1 text-xs rounded-md border transition-colors ${
                capabilityFilter === level
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-card hover:bg-accent border-border"
              }`}
            >
              {level ? masteryLabels[level] : "全部"}
            </button>
          ))}
        </div>
        {capabilityMap.domains.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {capabilityMap.domains.map((domain) => (
            <div
              key={domain.name}
              className="border rounded-xl bg-card shadow-sm hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => setExpandedDomain(expandedDomain === domain.name ? null : domain.name)}
            >
              <div className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold truncate">{domain.name}</h3>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-muted-foreground">{domain.concept_count} 个概念</span>
                    {expandedDomain === domain.name ? (
                      <ChevronUp className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <ChevronDown className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full transition-all"
                      style={{ width: `${Math.round(domain.average_mastery * 100)}%` }}
                    />
                  </div>
                  <span className="text-xs font-medium text-muted-foreground w-10 text-right">
                    {Math.round(domain.average_mastery * 100)}%
                  </span>
                </div>
              </div>
              {expandedDomain === domain.name && domain.concepts.length > 0 && (
                <div className="border-t px-4 py-3 space-y-2">
                  {domain.concepts.map((concept) => (
                    <div key={concept.name} className="flex items-center justify-between gap-2">
                      <span className="text-xs truncate">{concept.name}</span>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded shrink-0 ${
                          concept.mastery_level === "advanced"
                            ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                            : concept.mastery_level === "intermediate"
                            ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                            : concept.mastery_level === "beginner"
                            ? "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400"
                            : "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400"
                        }`}
                      >
                        {masteryLabels[concept.mastery_level] || concept.mastery_level}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
        )}
        </>
      )}
    </div>
  );
}

// === 主页面 ===
export function GraphPage() {
  const [searchParams] = useSearchParams();
  const focusConcept = searchParams.get("focus");
  const [activeView, setActiveView] = useState<ViewKey>("domain");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mapData, setMapData] = useState<KnowledgeMapResponse | null>(null);
  const [stats, setStats] = useState<ConceptStatsResponse | null>(null);
  const [selectedNode, setSelectedNode] = useState<MapNode | null>(null);
  const [showAllNodes, setShowAllNodes] = useState(false);
  const [aggregateMode, setAggregateMode] = useState(false);

  // F27: 搜索状态
  const [searchQuery, setSearchQuery] = useState("");
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchResults, setSearchResults] = useState<KnowledgeSearchResponse | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // F27: 掌握度分布状态
  const [masteryDist, setMasteryDist] = useState<MasteryDistributionResponse | null>(null);
  const [masteryDistLoading, setMasteryDistLoading] = useState(false);
  const [masteryDistError, setMasteryDistError] = useState<string | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const totalNodes = mapData?.nodes.length ?? 0;

  // 加载图谱数据
  const loadMap = useCallback(async (view: ViewKey) => {
    setLoading(true);
    setError(null);
    setSelectedNode(null);
    setShowAllNodes(false);
    setAggregateMode(false);
    setSearchQuery("");
    setSearchResults(null);
    setSearchError(null);
    try {
      const [mapResult, statsResult] = await Promise.all([
        getKnowledgeMap(2, view),
        getKnowledgeStats(),
      ]);
      setMapData(mapResult);
      setStats(statsResult);

      // 根据节点数决定初始渲染
      const allNodes = mapResult.nodes;
      const displayNodes = allNodes.length > NODE_THRESHOLD
        ? getTopNodes(allNodes, NODE_THRESHOLD)
        : allNodes;
      setNodes(layoutNodes(displayNodes));

      // 只渲染显示节点之间的边
      const displayNodeIds = new Set(displayNodes.map((n) => n.id));
      const displayEdges = mapResult.edges.filter(
        (e) => displayNodeIds.has(e.source) && displayNodeIds.has(e.target)
      );
      setEdges(buildEdges(displayEdges, displayEdges.length > EDGE_LABEL_THRESHOLD));
    } catch (err: any) {
      setError(err.message || "加载图谱失败");
    } finally {
      setLoading(false);
    }
  }, [setNodes, setEdges]);

  useEffect(() => {
    if (activeView === "capability") return; // 能力地图由 CapabilityMapView 独立加载
    loadMap(activeView);
  }, [activeView, loadMap]);

  // F31: URL ?focus= 参数 — 自动选中并高亮对应节点
  useEffect(() => {
    if (!focusConcept || !mapData || loading) return;
    const matchNode = mapData.nodes.find(
      (n) => n.name.toLowerCase() === focusConcept.toLowerCase() || n.id.toLowerCase() === focusConcept.toLowerCase()
    );
    if (matchNode) {
      setSelectedNode(matchNode);
      // 高亮匹配节点
      setNodes((prev) =>
        prev.map((n) => ({
          ...n,
          data: {
            ...n.data,
            highlighted: n.id === matchNode.id,
          } as Record<string, unknown>,
        }))
      );
    }
  }, [focusConcept, mapData, loading, setNodes]);

  // F27: 加载掌握度分布
  useEffect(() => {
    setMasteryDistLoading(true);
    setMasteryDistError(null);
    getMasteryDistribution()
      .then((data) => setMasteryDist(data))
      .catch((err: any) => setMasteryDistError(err.message || "加载掌握度分布失败"))
      .finally(() => setMasteryDistLoading(false));
  }, []);

  // F27: 搜索概念（防抖 300ms）
  useEffect(() => {
    if (searchTimerRef.current) {
      clearTimeout(searchTimerRef.current);
    }

    if (!searchQuery.trim()) {
      setSearchResults(null);
      setSearchError(null);
      // 恢复原始节点（移除高亮），如果之前是聚合模式则重新应用聚合
      if (aggregateMode && mapData) {
        const { aggregates, remaining } = aggregateByCategory(mapData.nodes);
        const layouted = layoutNodes(remaining);
        setNodes([...aggregates, ...layouted]);
        setEdges([]);
        return;
      }
      // 恢复原始节点（移除高亮）
      if (mapData) {
        const displayNodes = mapData.nodes.length > NODE_THRESHOLD && !showAllNodes
          ? getTopNodes(mapData.nodes, NODE_THRESHOLD)
          : mapData.nodes;
        setNodes(layoutNodes(displayNodes));
        const displayNodeIds = new Set(displayNodes.map((n) => n.id));
        const displayEdges = mapData.edges.filter(
          (e) => displayNodeIds.has(e.source) && displayNodeIds.has(e.target)
        );
        setEdges(buildEdges(displayEdges, displayEdges.length > EDGE_LABEL_THRESHOLD));
      }
      return;
    }

    searchTimerRef.current = setTimeout(async () => {
      setSearchLoading(true);
      setSearchError(null);
      setAggregateMode(false); // 搜索时退出聚合模式
      try {
        const result = await getKnowledgeSearch(searchQuery.trim());
        setSearchResults(result);

        // 高亮匹配的节点
        if (mapData) {
          const matchedNames = new Set(result.items.map((item) => item.name));
          const displayNodes = mapData.nodes.length > NODE_THRESHOLD && !showAllNodes
            ? getTopNodes(mapData.nodes, NODE_THRESHOLD)
            : mapData.nodes;
          const enrichedNodes = displayNodes.map((n) => ({
            ...n,
            highlighted: matchedNames.has(n.name),
          }));
          setNodes(layoutNodes(enrichedNodes as MapNode[] & { highlighted?: boolean }[]));
        }
      } catch (err: any) {
        setSearchError(err.message || "搜索失败");
      } finally {
        setSearchLoading(false);
      }
    }, 300);

    return () => {
      if (searchTimerRef.current) {
        clearTimeout(searchTimerRef.current);
      }
    };
  }, [searchQuery, mapData, showAllNodes, setNodes, setEdges]);

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

  // 加载全部节点
  const handleShowAllNodes = useCallback(() => {
    if (!mapData) return;
    setShowAllNodes(true);
    setNodes(layoutNodes(mapData.nodes));
    setEdges(buildEdges(mapData.edges, mapData.edges.length > EDGE_LABEL_THRESHOLD));
  }, [mapData, setNodes, setEdges]);

  // 切换聚合模式
  const handleToggleAggregate = useCallback(() => {
    if (!mapData) return;
    const newMode = !aggregateMode;
    setAggregateMode(newMode);

    if (newMode) {
      const { aggregates, remaining } = aggregateByCategory(mapData.nodes);
      const layouted = layoutNodes(remaining);
      setNodes([...aggregates, ...layouted]);
      // 聚合模式下不显示边
      setEdges([]);
    } else {
      const displayNodes = mapData.nodes.length > NODE_THRESHOLD && !showAllNodes
        ? getTopNodes(mapData.nodes, NODE_THRESHOLD)
        : mapData.nodes;
      setNodes(layoutNodes(displayNodes));
      const displayNodeIds = new Set(displayNodes.map((n) => n.id));
      const displayEdges = mapData.edges.filter(
        (e) => displayNodeIds.has(e.source) && displayNodeIds.has(e.target)
      );
      setEdges(buildEdges(displayEdges, displayEdges.length > EDGE_LABEL_THRESHOLD));
    }
  }, [mapData, aggregateMode, showAllNodes, setNodes, setEdges]);

  // MiniMap 节点颜色
  const miniMapNodeColor = useCallback((node: Node) => {
    const data = node.data as unknown as MapNode;
    return masteryColors[data.mastery] || "#9ca3af";
  }, []);

  const isEmpty = !loading && !error && mapData && mapData.nodes.length === 0;

  return (
    <div className="flex flex-1 flex-col h-[calc(100vh-0px)]">
      <Header title="知识图谱" />

      {/* Tab 栏 + 搜索框 */}
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

        {/* F27: 搜索框 — 能力地图视图不需要 */}
        {activeView !== "capability" && (
        <div className="ml-auto relative w-48 md:w-64">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索概念..."
            className="w-full pl-8 pr-3 py-1.5 text-sm rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/30 transition-shadow"
          />
          {searchLoading && (
            <Loader2 className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 animate-spin text-muted-foreground" />
          )}
        </div>
        )}
      </div>

      {/* 搜索结果提示 — 仅非能力地图视图 */}
      {activeView !== "capability" && searchError && (
        <div className="px-4 py-2 bg-destructive/10 text-destructive text-xs">
          {searchError}
        </div>
      )}
      {activeView !== "capability" && searchResults && searchResults.items.length === 0 && !searchLoading && searchQuery.trim() && (
        <div className="px-4 py-2 bg-muted/50 text-muted-foreground text-xs">
          未找到与 "{searchQuery.trim()}" 匹配的概念
        </div>
      )}

      {/* 主内容区 */}
      <div className="flex flex-1 overflow-hidden">
        {/* F109: 能力地图视图 */}
        {activeView === "capability" ? (
          <CapabilityMapView />
        ) : (
        <>
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
            <>
              {/* 性能控制按钮 */}
              {totalNodes > NODE_THRESHOLD && (
                <div className="absolute top-3 left-3 z-20 flex gap-2">
                  {!showAllNodes && !aggregateMode && (
                    <button
                      onClick={handleShowAllNodes}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-card border shadow-sm text-xs font-medium hover:bg-accent transition-colors"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      加载全部 ({totalNodes})
                    </button>
                  )}
                  <button
                    onClick={handleToggleAggregate}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border shadow-sm text-xs font-medium transition-colors ${
                      aggregateMode
                        ? "bg-primary text-primary-foreground"
                        : "bg-card hover:bg-accent"
                    }`}
                  >
                    <Layers className="h-3.5 w-3.5" />
                    {aggregateMode ? "展开" : "聚合"}
                  </button>
                </div>
              )}
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
            </>
          )}
        </div>

        {/* F27: 掌握度分布卡片（侧边栏下方，仅桌面端显示，无选中节点时） */}
        {!selectedNode && (
          <div className="hidden md:flex w-64 border-l bg-card flex-col">
            <div className="p-4 border-b">
              <div className="flex items-center gap-1.5 mb-3">
                <BarChart3 className="h-4 w-4 text-primary" />
                <h3 className="text-sm font-semibold">掌握度分布</h3>
              </div>

              {masteryDistLoading && (
                <div className="flex items-center gap-2 py-2">
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  <span className="text-xs text-muted-foreground">加载中...</span>
                </div>
              )}

              {masteryDistError && (
                <div className="space-y-2">
                  <p className="text-xs text-destructive">{masteryDistError}</p>
                  <button
                    onClick={() => {
                      setMasteryDistLoading(true);
                      setMasteryDistError(null);
                      getMasteryDistribution()
                        .then((data) => setMasteryDist(data))
                        .catch((err: any) => setMasteryDistError(err.message || "加载掌握度分布失败"))
                        .finally(() => setMasteryDistLoading(false));
                    }}
                    className="text-xs text-primary hover:underline"
                  >
                    重试
                  </button>
                </div>
              )}

              {masteryDist && !masteryDistLoading && (
                <div className="space-y-2.5">
                  {(["advanced", "intermediate", "beginner", "new"] as const).map((level) => {
                    const count = masteryDist[level];
                    const total = masteryDist.total || 1;
                    const pct = Math.round((count / total) * 100);
                    return (
                      <div key={level}>
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-1.5">
                            <span
                              className="inline-block w-2.5 h-2.5 rounded-full"
                              style={{ backgroundColor: masteryColors[level] }}
                            />
                            <span className="text-xs">{masteryLabels[level]}</span>
                          </div>
                          <span className="text-xs font-medium">{count}</span>
                        </div>
                        <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${pct}%`,
                              backgroundColor: masteryColors[level],
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                  <div className="pt-2 border-t text-center">
                    <span className="text-xs text-muted-foreground">
                      共 {masteryDist.total} 个概念
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* 搜索结果列表 */}
            {searchResults && searchResults.items.length > 0 && (
              <div className="p-4 flex-1 overflow-y-auto">
                <p className="text-xs font-medium text-muted-foreground mb-2">
                  搜索结果 ({searchResults.items.length})
                </p>
                <div className="space-y-1.5">
                  {searchResults.items.map((item) => (
                    <button
                      key={item.name}
                      onClick={() => {
                        // 找到对应节点并选中
                        const matchNode = mapData?.nodes.find((n) => n.name === item.name);
                        if (matchNode) setSelectedNode(matchNode);
                      }}
                      className="w-full text-left px-2.5 py-2 rounded-lg hover:bg-accent transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className="inline-block w-2 h-2 rounded-full shrink-0"
                          style={{ backgroundColor: item.mastery ? masteryColors[item.mastery] : "#9ca3af" }}
                        />
                        <span className="text-xs font-medium truncate">{item.name}</span>
                      </div>
                      <span className="text-[10px] text-muted-foreground ml-4">
                        {item.entry_count} 条记录 · {item.mastery ? masteryLabels[item.mastery] : "未知"}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* 详情面板 */}
        {selectedNode && (
          <DetailPanel
            node={selectedNode}
            stats={stats}
            onClose={() => setSelectedNode(null)}
          />
        )}
        </>
        )}
      </div>

      {/* F110: 图谱 AI 助手 */}
      <PageChatPanel
        title="图谱助手"
        welcomeMessage="想了解图谱中的知识关系？我可以帮你分析"
        suggestions={[
          { label: "擅长领域", message: "我最擅长的领域是什么？" },
          { label: "薄弱方向", message: "哪些领域需要加强？" },
          { label: "学习建议", message: "基于我的知识图谱，有什么学习建议？" },
        ]}
        pageContext={{ page: "graph" }}
        pageData={{
          current_view: activeView,
          selected_concept: selectedNode?.name ?? "",
          total_concepts: stats?.concept_count ?? 0,
          total_relations: stats?.relation_count ?? 0,
          domain_count: 0,
        }}
        defaultCollapsed
      />
    </div>
  );
}
