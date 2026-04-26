import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Link, useSearchParams } from "react-router-dom";
import { Loader2, AlertCircle, Compass, Plus, Layers, Search, BarChart3 } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { PageChatPanel } from "@/components/PageChatPanel";
import { ServiceUnavailable } from "@/components/ServiceUnavailable";
import { useGraphState } from "./graph/useGraphState";
import { DetailPanel } from "./graph/DetailPanel";
import { CapabilityMapView } from "./graph/CapabilityMapView";
import { nodeTypes } from "./graph/CustomNodes";
import { viewTabs, masteryColors, masteryLabels, MASTERY_LEVELS, NODE_THRESHOLD } from "./graph/constants";

// === 主页面 ===
export function GraphPage() {
  const [searchParams] = useSearchParams();
  const focusConcept = searchParams.get("focus");

  const state = useGraphState(focusConcept);

  return (
    <div className="flex flex-1 flex-col h-[calc(100vh-0px)]">
      <Header title="知识图谱" />

      {/* Tab 栏 + 搜索框 */}
      <div className="flex items-center border-b px-4 md:px-6 gap-1 bg-card">
        {viewTabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => state.setActiveView(tab.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              state.activeView === tab.key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}

        {/* F27: 搜索框 — 能力地图视图不需要 */}
        {state.activeView !== "capability" && (
        <div className="ml-auto relative w-48 md:w-64">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            value={state.searchQuery}
            onChange={(e) => state.setSearchQuery(e.target.value)}
            placeholder="搜索概念..."
            className="w-full pl-8 pr-3 py-1.5 text-sm rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/30 transition-shadow"
          />
          {state.searchLoading && (
            <Loader2 className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 animate-spin text-muted-foreground" />
          )}
        </div>
        )}
      </div>

      {/* 搜索结果提示 — 仅非能力地图视图 */}
      {state.activeView !== "capability" && state.searchError && (
        <div className="px-4 py-2 bg-destructive/10 text-destructive text-xs">
          {state.searchError}
        </div>
      )}
      {state.activeView !== "capability" && state.searchResults && state.searchResults.items.length === 0 && !state.searchLoading && state.searchQuery.trim() && (
        <div className="px-4 py-2 bg-muted/50 text-muted-foreground text-xs">
          未找到与 "{state.searchQuery.trim()}" 匹配的概念
        </div>
      )}

      {/* 主内容区 */}
      <div className="flex flex-1 overflow-hidden">
        {/* F109: 能力地图视图 */}
        {state.activeView === "capability" ? (
          <CapabilityMapView />
        ) : state.serviceUnavailable ? (
          <div className="flex-1 flex items-center justify-center">
            <ServiceUnavailable onRetry={() => state.loadMap(state.activeView)} />
          </div>
        ) : (
        <>
        {/* 画布区 */}
        <div className="flex-1 relative">
          {state.loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          )}

          {state.error && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 z-10">
              <AlertCircle className="h-10 w-10 text-destructive" />
              <p className="text-sm text-destructive">{state.error}</p>
              <button
                onClick={() => state.loadMap(state.activeView)}
                className="text-sm text-primary hover:underline"
              >
                重试
              </button>
            </div>
          )}

          {state.isEmpty && (
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

          {!state.isEmpty && (
            <>
              {/* 性能控制按钮 */}
              {state.totalNodes > NODE_THRESHOLD && (
                <div className="absolute top-3 left-3 z-20 flex gap-2">
                  {!state.showAllNodes && !state.aggregateMode && (
                    <button
                      onClick={state.handleShowAllNodes}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-card border shadow-sm text-xs font-medium hover:bg-accent transition-colors"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      加载全部 ({state.totalNodes})
                    </button>
                  )}
                  <button
                    onClick={state.handleToggleAggregate}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border shadow-sm text-xs font-medium transition-colors ${
                      state.aggregateMode
                        ? "bg-primary text-primary-foreground"
                        : "bg-card hover:bg-accent"
                    }`}
                  >
                    <Layers className="h-3.5 w-3.5" />
                    {state.aggregateMode ? "展开" : "聚合"}
                  </button>
                </div>
              )}
              <ReactFlow
              nodes={state.nodes}
              edges={state.edges}
              onNodesChange={state.onNodesChange}
              onEdgesChange={state.onEdgesChange}
              onNodeClick={state.onNodeClick}
              onPaneClick={state.onPaneClick}
              nodeTypes={nodeTypes}
              fitView
              minZoom={0.2}
              maxZoom={2}
              className="bg-background"
            >
              <Background color="#e2e8f0" gap={20} size={1} />
              <Controls className="!bg-card !border !shadow-md" />
              <MiniMap
                nodeColor={state.miniMapNodeColor}
                className="!bg-card !border !shadow-md"
                maskColor="rgba(0,0,0,0.1)"
              />
            </ReactFlow>
            </>
          )}
        </div>

        {/* F27: 掌握度分布卡片（侧边栏下方，仅桌面端显示，无选中节点时） */}
        {!state.selectedNode && (
          <div className="hidden md:flex w-64 border-l bg-card flex-col">
            <div className="p-4 border-b">
              <div className="flex items-center gap-1.5 mb-3">
                <BarChart3 className="h-4 w-4 text-primary" />
                <h3 className="text-sm font-semibold">掌握度分布</h3>
              </div>

              {state.masteryDistLoading && (
                <div className="flex items-center gap-2 py-2">
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  <span className="text-xs text-muted-foreground">加载中...</span>
                </div>
              )}

              {state.masteryDistError && (
                <div className="space-y-2">
                  <p className="text-xs text-destructive">{state.masteryDistError}</p>
                  <button
                    onClick={state.retryMasteryDist}
                    className="text-xs text-primary hover:underline"
                  >
                    重试
                  </button>
                </div>
              )}

              {state.masteryDist && !state.masteryDistLoading && (
                <div className="space-y-2.5">
                  {MASTERY_LEVELS.map((level) => {
                    const count = state.masteryDist![level];
                    const total = state.masteryDist!.total || 1;
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
                      共 {state.masteryDist.total} 个概念
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* 搜索结果列表 */}
            {state.searchResults && state.searchResults.items.length > 0 && (
              <div className="p-4 flex-1 overflow-y-auto">
                <p className="text-xs font-medium text-muted-foreground mb-2">
                  搜索结果 ({state.searchResults.items.length})
                </p>
                <div className="space-y-1.5">
                  {state.searchResults.items.map((item) => (
                    <button
                      key={item.name}
                      onClick={() => {
                        const matchNode = state.mapData?.nodes.find((n) => n.name === item.name);
                        if (matchNode) state.setSelectedNode(matchNode);
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
        {state.selectedNode && (
          <DetailPanel
            node={state.selectedNode}
            stats={state.stats}
            onClose={() => state.setSelectedNode(null)}
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
          current_view: state.activeView,
          selected_concept: state.selectedNode?.name ?? "",
          total_concepts: state.stats?.concept_count ?? 0,
          total_relations: state.stats?.relation_count ?? 0,
          domain_count: 0,
        }}
        defaultCollapsed
      />
    </div>
  );
}
