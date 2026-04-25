import { useState, useEffect, useCallback, useRef } from "react";
import {
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from "@xyflow/react";
import {
  getKnowledgeMap,
  getKnowledgeStats,
  getKnowledgeSearch,
  getMasteryDistribution,
  type MapNode,
  type KnowledgeMapResponse,
  type ConceptStatsResponse,
  type KnowledgeSearchResponse,
  type MasteryDistributionResponse,
} from "@/services/api";
import { ApiError } from "@/lib/errors";
import { type ViewKey, EDGE_LABEL_THRESHOLD, masteryColors } from "./constants";
import { layoutNodes, aggregateByCategory, buildEdges, getDisplayData } from "./utils";

export interface GraphState {
  activeView: ViewKey;
  setActiveView: (view: ViewKey) => void;
  loading: boolean;
  error: string | null;
  serviceUnavailable: boolean;
  mapData: KnowledgeMapResponse | null;
  stats: ConceptStatsResponse | null;
  selectedNode: MapNode | null;
  setSelectedNode: (node: MapNode | null) => void;
  showAllNodes: boolean;
  aggregateMode: boolean;
  nodes: Node[];
  edges: Edge[];
  onNodesChange: ReturnType<typeof useNodesState<Node>>[2];
  onEdgesChange: ReturnType<typeof useEdgesState<Edge>>[2];
  totalNodes: number;
  isEmpty: boolean;

  // 搜索
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  searchLoading: boolean;
  searchResults: KnowledgeSearchResponse | null;
  searchError: string | null;

  // 掌握度分布
  masteryDist: MasteryDistributionResponse | null;
  masteryDistLoading: boolean;
  masteryDistError: string | null;
  retryMasteryDist: () => void;

  // 操作
  loadMap: (view: ViewKey) => Promise<void>;
  handleShowAllNodes: () => void;
  handleToggleAggregate: () => void;
  onNodeClick: (_: React.MouseEvent, node: Node) => void;
  onPaneClick: () => void;
  miniMapNodeColor: (node: Node) => string;
}

export function useGraphState(focusConcept: string | null): GraphState {
  const [activeView, setActiveView] = useState<ViewKey>("domain");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [serviceUnavailable, setServiceUnavailable] = useState(false);
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
    setServiceUnavailable(false);
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
      const { displayNodes, displayEdges } = getDisplayData(mapResult, false);
      setNodes(layoutNodes(displayNodes));
      setEdges(buildEdges(displayEdges, displayEdges.length > EDGE_LABEL_THRESHOLD));
    } catch (err: any) {
      if (err instanceof ApiError && err.isServiceUnavailable) {
        setServiceUnavailable(true);
      } else {
        setError(err.message || "加载图谱失败");
      }
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
  const loadMasteryDist = useCallback(() => {
    setMasteryDistLoading(true);
    setMasteryDistError(null);
    getMasteryDistribution()
      .then((data) => setMasteryDist(data))
      .catch((err: any) => setMasteryDistError(err.message || "加载掌握度分布失败"))
      .finally(() => setMasteryDistLoading(false));
  }, []);

  useEffect(() => {
    loadMasteryDist();
  }, [loadMasteryDist]);

  const retryMasteryDist = loadMasteryDist;

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
        const { displayNodes, displayEdges } = getDisplayData(mapData, showAllNodes);
        setNodes(layoutNodes(displayNodes));
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
          const { displayNodes } = getDisplayData(mapData, showAllNodes);
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
  }, [searchQuery, mapData, showAllNodes, aggregateMode, setNodes, setEdges]);

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
      const { displayNodes, displayEdges } = getDisplayData(mapData, showAllNodes);
      setNodes(layoutNodes(displayNodes));
      setEdges(buildEdges(displayEdges, displayEdges.length > EDGE_LABEL_THRESHOLD));
    }
  }, [mapData, aggregateMode, showAllNodes, setNodes, setEdges]);

  // MiniMap 节点颜色
  const miniMapNodeColor = useCallback((node: Node) => {
    const data = node.data as unknown as MapNode;
    return masteryColors[data.mastery] || "#9ca3af";
  }, []);

  const isEmpty = !loading && !error && !!mapData && mapData.nodes.length === 0;

  return {
    activeView,
    setActiveView,
    loading,
    error,
    serviceUnavailable,
    mapData,
    stats,
    selectedNode,
    setSelectedNode,
    showAllNodes,
    aggregateMode,
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    totalNodes,
    isEmpty,
    searchQuery,
    setSearchQuery,
    searchLoading,
    searchResults,
    searchError,
    masteryDist,
    masteryDistLoading,
    masteryDistError,
    retryMasteryDist,
    loadMap,
    handleShowAllNodes,
    handleToggleAggregate,
    onNodeClick,
    onPaneClick,
    miniMapNodeColor,
  };
}
