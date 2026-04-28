import { describe, it, expect, vi, beforeEach, beforeAll } from "vitest";
import { render, screen, waitFor, act, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState, useCallback } from "react";

// ── Mock: react-router-dom ──────────────────────────────
const mockSearchParams = new URLSearchParams();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useSearchParams: () => [mockSearchParams],
    Link: ({ to, children }: { to: string; children: React.ReactNode }) => (
      <a href={to}>{children}</a>
    ),
  };
});

// ── Mock: @xyflow/react ────────────────────────────────
// 使用 stateful mock 让 useNodesState/useEdgesState 实际可用
vi.mock("@xyflow/react", () => {
  return {
    ReactFlow: ({ nodes, onNodeClick }: { nodes: Array<{ id: string; data: Record<string, unknown> }>; onNodeClick?: (_: React.MouseEvent, node: { id: string; data: Record<string, unknown> }) => void }) => (
      <div data-testid="react-flow" data-node-count={nodes.length}>
        {nodes.map((n) => (
          <div
            key={n.id}
            data-testid={`node-${n.id}`}
            onClick={(e) => onNodeClick?.(e as unknown as React.MouseEvent, n)}
          >
            {(n.data as Record<string, unknown>).name as string}
          </div>
        ))}
      </div>
    ),
    Background: () => <div data-testid="background" />,
    Controls: () => <div data-testid="controls" />,
    MiniMap: () => <div data-testid="minimap" />,
    useNodesState: <T,>(initial: T[]) => {
      const [nodes, setNodes] = useState(initial);
      const onNodesChange = useCallback(() => {}, []);
      return [nodes, setNodes, onNodesChange];
    },
    useEdgesState: <T,>(initial: T[]) => {
      const [edges, setEdges] = useState(initial);
      const onEdgesChange = useCallback(() => {}, []);
      return [edges, setEdges, onEdgesChange];
    },
  };
});

// ── Mock: @/services/api ────────────────────────────────
const mockGetKnowledgeMap = vi.fn();
const mockGetKnowledgeStats = vi.fn();
const mockGetKnowledgeSearch = vi.fn();
const mockGetMasteryDistribution = vi.fn();
const mockGetCapabilityMap = vi.fn();
const mockGetConceptTimeline = vi.fn();

vi.mock("@/services/api", () => ({
  getKnowledgeMap: (...args: unknown[]) => mockGetKnowledgeMap(...args),
  getKnowledgeStats: (...args: unknown[]) => mockGetKnowledgeStats(...args),
  getKnowledgeSearch: (...args: unknown[]) => mockGetKnowledgeSearch(...args),
  getMasteryDistribution: (...args: unknown[]) => mockGetMasteryDistribution(...args),
  getCapabilityMap: (...args: unknown[]) => mockGetCapabilityMap(...args),
  getConceptTimeline: (...args: unknown[]) => mockGetConceptTimeline(...args),
}));

// ── Mock: Header ────────────────────────
vi.mock("@/components/layout/Header", () => ({
  Header: ({ title }: { title: string }) => <header>{title}</header>,
}));

// ── Mock: CSS import ─────────────────────────────────────
vi.mock("@xyflow/react/dist/style.css", () => ({}));

// ── Fixtures ────────────────────────────────────────────
function makeMapNodes(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    id: `node-${i}`,
    name: `概念${i}`,
    category: i % 3 === 0 ? "编程" : i % 3 === 1 ? "设计" : "管理",
    mastery: (["new", "beginner", "intermediate", "advanced"] as const)[i % 4],
    entry_count: i + 1,
  }));
}

function makeMapEdges(count: number) {
  return Array.from({ length: Math.min(count, 50) }, (_, i) => ({
    source: `node-${i}`,
    target: `node-${(i + 1) % count}`,
    relationship: `关系${i}`,
  }));
}

const MAP_DATA_SMALL = { nodes: makeMapNodes(10), edges: makeMapEdges(5) };
const MAP_DATA_LARGE = { nodes: makeMapNodes(60), edges: makeMapEdges(20) };

const STATS_DATA = {
  concept_count: 10,
  relation_count: 5,
  category_distribution: { 编程: 4, 设计: 3, 管理: 3 },
  top_concepts: [{ name: "概念0", entry_count: 1, category: "编程" }],
};

const MASTERY_DIST = {
  advanced: 2,
  intermediate: 3,
  beginner: 3,
  new: 2,
  total: 10,
};

const CAPABILITY_DATA = {
  domains: [
    {
      name: "编程",
      concept_count: 4,
      average_mastery: 0.6,
      concepts: [
        { name: "概念0", mastery_level: "advanced" },
        { name: "概念3", mastery_level: "beginner" },
      ],
    },
    {
      name: "设计",
      concept_count: 3,
      average_mastery: 0.4,
      concepts: [
        { name: "概念1", mastery_level: "intermediate" },
      ],
    },
  ],
};

const TIMELINE_DATA = {
  items: [
    {
      date: "2026-04-20",
      entries: [
        { id: "entry-1", title: "学习笔记1" },
        { id: "entry-2", title: "学习笔记2" },
      ],
    },
  ],
};

const SEARCH_RESULTS = {
  items: [
    { name: "概念0", entry_count: 1, mastery: "advanced" },
    { name: "概念3", entry_count: 4, mastery: "beginner" },
  ],
};

// ── Helper ──────────────────────────────────────────────
import { GraphPage } from "./GraphPage";

function setupDefaultMocks(overrides?: {
  mapData?: typeof MAP_DATA_SMALL;
  capabilityData?: typeof CAPABILITY_DATA;
}) {
  mockGetKnowledgeMap.mockResolvedValue(overrides?.mapData ?? MAP_DATA_SMALL);
  mockGetKnowledgeStats.mockResolvedValue(STATS_DATA);
  mockGetMasteryDistribution.mockResolvedValue(MASTERY_DIST);
  mockGetCapabilityMap.mockResolvedValue(overrides?.capabilityData ?? CAPABILITY_DATA);
  mockGetConceptTimeline.mockResolvedValue(TIMELINE_DATA);
  mockGetKnowledgeSearch.mockResolvedValue(SEARCH_RESULTS);
}

// ── Tests ───────────────────────────────────────────────
describe("GraphPage Tab 切换与基本渲染", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // reset searchParams
    for (const key of [...mockSearchParams.keys()]) {
      mockSearchParams.delete(key);
    }
    setupDefaultMocks();
  });

  // ── 1. 默认 Tab 为知识地图(领域) ──────────────────────
  it("默认渲染领域 Tab 并加载知识图谱", async () => {
    render(<GraphPage />);

    expect(screen.getByText("知识图谱")).toBeInTheDocument();
    // Tab 按钮全部渲染
    expect(screen.getByRole("button", { name: "领域" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "掌握度" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "项目" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "能力地图" })).toBeInTheDocument();

    // 领域 tab 为当前选中
    const domainTab = screen.getByRole("button", { name: "领域" });
    expect(domainTab.className).toContain("border-primary");

    // API 调用
    await waitFor(() => {
      expect(mockGetKnowledgeMap).toHaveBeenCalledWith(2, "domain");
      expect(mockGetKnowledgeStats).toHaveBeenCalled();
    });

    // ReactFlow 渲染
    await waitFor(() => {
      expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    });
  });

  // ── 2. 切换到掌握度 Tab ────────────────────────────────
  it("切换到掌握度 Tab 正常渲染", async () => {
    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "掌握度" }));

    await waitFor(() => {
      expect(mockGetKnowledgeMap).toHaveBeenCalledWith(2, "mastery");
    });
  });

  // ── 3. 切换到项目 Tab ──────────────────────────────────
  it("切换到项目 Tab 正常渲染", async () => {
    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "项目" }));

    await waitFor(() => {
      expect(mockGetKnowledgeMap).toHaveBeenCalledWith(2, "project");
    });
  });

  // ── 4. 切换到能力地图 Tab ──────────────────────────────
  it("切换到能力地图 Tab 正常渲染", async () => {
    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "能力地图" }));

    await waitFor(() => {
      expect(mockGetCapabilityMap).toHaveBeenCalled();
    });
  });

  // ── 5. ?focus= 参数自动定位并高亮节点 ─────────────────
  it("?focus= 参数自动定位并高亮节点", async () => {
    mockSearchParams.set("focus", "概念0");

    render(<GraphPage />);

    await waitFor(() => {
      expect(mockGetKnowledgeMap).toHaveBeenCalled();
    });

    // 等待节点渲染 — focus 概念的节点出现在 DOM
    await waitFor(() => {
      expect(screen.getByTestId("node-node-0")).toBeInTheDocument();
    });

    // focus 后详情面板应打开（setSelectedNode），时间线标题出现
    // 注：移动端+桌面端各有一份，使用 getAllByText
    await waitFor(() => {
      expect(screen.getAllByText("学习时间线").length).toBeGreaterThanOrEqual(1);
    });

    // 验证 getConceptTimeline 被调用
    await waitFor(() => {
      expect(mockGetConceptTimeline).toHaveBeenCalledWith("概念0", 30);
    });
  });

  // ── 6. 搜索输入防抖后触发请求 ─────────────────────────
  it("搜索输入防抖后触发请求", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("搜索概念...");
    // 手动触发 onChange 而不用 userEvent.type（避免 fake timer 冲突）
    await act(async () => {
      searchInput.focus();
    });
    fireEvent.change(searchInput, { target: { value: "测试" } });

    // 还没触发（防抖 300ms）
    expect(mockGetKnowledgeSearch).not.toHaveBeenCalled();

    // 等待防抖
    await act(async () => {
      vi.advanceTimersByTime(400);
    });

    await waitFor(() => {
      expect(mockGetKnowledgeSearch).toHaveBeenCalledWith("测试");
    });

    vi.useRealTimers();
  });

  // ── 7. showAll 聚合/展开切换正常 ──────────────────────
  it("showAll 聚合/展开切换正常", async () => {
    setupDefaultMocks({ mapData: MAP_DATA_LARGE });
    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    });

    const user = userEvent.setup();

    // 节点数 > NODE_THRESHOLD(50)，应显示性能控制按钮
    await waitFor(() => {
      expect(screen.getByText(/加载全部/)).toBeInTheDocument();
      expect(screen.getByText("聚合")).toBeInTheDocument();
    });

    // 点击聚合
    await user.click(screen.getByText("聚合"));

    await waitFor(() => {
      expect(screen.getByText("展开")).toBeInTheDocument();
    });

    // 点击展开
    await user.click(screen.getByText("展开"));

    await waitFor(() => {
      expect(screen.getByText("聚合")).toBeInTheDocument();
    });

    // 点击加载全部
    await user.click(screen.getByText(/加载全部/));
    // 不应再显示加载全部按钮（showAllNodes = true）
    await waitFor(() => {
      expect(screen.queryByText(/加载全部/)).not.toBeInTheDocument();
    });
  });

  // ── 8. 能力地图筛选条件变更触发重新加载 ──────────────
  it("能力地图筛选条件变更触发重新加载", async () => {
    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    });

    const user = userEvent.setup();

    // 切换到能力地图
    await user.click(screen.getByRole("button", { name: "能力地图" }));

    await waitFor(() => {
      expect(screen.getByText("筛选：")).toBeInTheDocument();
    });

    // 第一次加载（无筛选）
    expect(mockGetCapabilityMap).toHaveBeenCalledTimes(1);

    // 点击筛选按钮 - "入门"
    await user.click(screen.getByRole("button", { name: "入门" }));

    await waitFor(() => {
      // 第二次加载（有筛选）
      expect(mockGetCapabilityMap).toHaveBeenCalledWith("beginner");
    });
  });

  // ── 9. 能力地图加载失败时展示重试入口 ────────────────
  it("能力地图加载失败时展示重试入口", async () => {
    mockGetCapabilityMap.mockRejectedValueOnce(new Error("网络错误"));

    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "能力地图" }));

    await waitFor(() => {
      expect(screen.getByText("网络错误")).toBeInTheDocument();
      expect(screen.getByText("重试")).toBeInTheDocument();
    });
  });

  // ── 10. 点击重试后重新加载成功、状态恢复 ─────────────
  it("点击重试后重新加载成功、状态恢复", async () => {
    mockGetCapabilityMap
      .mockRejectedValueOnce(new Error("网络错误"))
      .mockResolvedValueOnce(CAPABILITY_DATA);

    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "能力地图" }));

    await waitFor(() => {
      expect(screen.getByText("网络错误")).toBeInTheDocument();
    });

    // 点击重试
    await user.click(screen.getByText("重试"));

    // 重新加载成功，应显示能力地图内容
    await waitFor(() => {
      expect(screen.getByText("编程")).toBeInTheDocument();
      expect(screen.getByText("设计")).toBeInTheDocument();
    });
  });

  // ── 11. 详情面板打开/关闭正常 ─────────────────────────
  it("详情面板打开/关闭正常", async () => {
    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    });

    // 掌握度分布侧栏（无选中节点时显示）
    await waitFor(() => {
      expect(screen.getByText("掌握度分布")).toBeInTheDocument();
    });

    // 点击节点打开详情面板 — 通过 mock 的 ReactFlow 中的 onNodeClick
    const user = userEvent.setup();
    const nodeEl = screen.getByTestId("node-node-0");
    await user.click(nodeEl);

    // 详情面板打开，时间线标题出现（移动端+桌面端各一份）
    await waitFor(() => {
      expect(screen.getAllByText("学习时间线").length).toBeGreaterThanOrEqual(1);
    });

    // 关闭详情面板 — 点击遮罩层（移动端）关闭
    // 使用 setSelectedNode(null) 的 onClose
    // 查找详情面板中的关闭按钮
    const closeButtons = screen.getAllByRole("button").filter((btn) => {
      const svg = btn.querySelector("svg.lucide-x");
      return svg !== null;
    });
    // 至少有一个关闭按钮
    expect(closeButtons.length).toBeGreaterThanOrEqual(1);
    await user.click(closeButtons[0]);

    // 详情面板关闭后，掌握度分布重新显示
    await waitFor(() => {
      expect(screen.getByText("掌握度分布")).toBeInTheDocument();
    });
  });

  // ── 12. 时间线数据加载和显示 ──────────────────────────
  it("时间线数据加载和显示", async () => {
    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    });

    // 点击节点打开详情面板，触发时间线加载
    const user = userEvent.setup();
    await user.click(screen.getByTestId("node-node-0"));

    // 时间线数据加载
    await waitFor(() => {
      expect(mockGetConceptTimeline).toHaveBeenCalledWith("概念0", 30);
    });

    // 时间线日期和条目显示（移动端+桌面端各一份）
    await waitFor(() => {
      expect(screen.getAllByText("2026-04-20").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("学习笔记1").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("学习笔记2").length).toBeGreaterThanOrEqual(1);
    });
  });

  // ── 补充：搜索空结果提示 ──────────────────────────────
  it("搜索无结果时显示提示", async () => {
    mockGetKnowledgeSearch.mockResolvedValue({ items: [] });
    vi.useFakeTimers({ shouldAdvanceTime: true });

    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("搜索概念...");
    fireEvent.change(searchInput, { target: { value: "不存在的概念" } });

    await act(async () => {
      vi.advanceTimersByTime(400);
    });

    await waitFor(() => {
      expect(screen.getByText(/未找到与 "不存在的概念" 匹配的概念/)).toBeInTheDocument();
    });

    vi.useRealTimers();
  });

  // ── 补充：图谱加载失败显示重试按钮 ────────────────────
  it("图谱加载失败显示错误和重试按钮", async () => {
    mockGetKnowledgeMap.mockRejectedValueOnce(new Error("服务不可用"));

    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByText("服务不可用")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "重试" })).toBeInTheDocument();
    });
  });

  // ── 补充：空图谱显示引导提示 ──────────────────────────
  it("空图谱显示引导提示", async () => {
    setupDefaultMocks({ mapData: { nodes: [], edges: [] } });

    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByText("开始记录你的学习旅程，知识图谱将自动生成")).toBeInTheDocument();
    });
  });

  // ── 补充：掌握度分布侧栏显示 ──────────────────────────
  it("掌握度分布侧栏正确渲染统计数据", async () => {
    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByText("掌握度分布")).toBeInTheDocument();
      expect(screen.getByText("精通")).toBeInTheDocument();
      expect(screen.getByText("熟练")).toBeInTheDocument();
      expect(screen.getByText("入门")).toBeInTheDocument();
      expect(screen.getByText("新概念")).toBeInTheDocument();
      expect(screen.getByText("共 10 个概念")).toBeInTheDocument();
    });
  });

  // ── 补充：掌握度分布加载失败可重试 ────────────────────
  it("掌握度分布加载失败显示重试按钮", async () => {
    mockGetMasteryDistribution.mockRejectedValueOnce(new Error("分布加载失败"));

    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByText("分布加载失败")).toBeInTheDocument();
    });

    // 掌握度分布的重试按钮
    const retryButtons = screen.getAllByRole("button", { name: "重试" });
    expect(retryButtons.length).toBeGreaterThanOrEqual(1);

    // 点击重试
    mockGetMasteryDistribution.mockResolvedValueOnce(MASTERY_DIST);
    const user = userEvent.setup();
    await user.click(retryButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("掌握度分布")).toBeInTheDocument();
    });
  });

  // ── 补充：能力地图空结果提示 ──────────────────────────
  it("能力地图筛选后无结果显示提示", async () => {
    mockGetCapabilityMap
      .mockResolvedValueOnce(CAPABILITY_DATA) // 初始加载
      .mockResolvedValueOnce({ domains: [] }); // 筛选后

    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "能力地图" }));

    await waitFor(() => {
      expect(screen.getByText("筛选：")).toBeInTheDocument();
    });

    // 筛选"入门"
    await user.click(screen.getByRole("button", { name: "入门" }));

    await waitFor(() => {
      expect(screen.getByText(/没有入门级别的概念/)).toBeInTheDocument();
      expect(screen.getByText("查看全部")).toBeInTheDocument();
    });
  });

  // ── 补充：能力地图展开/折叠域 ─────────────────────────
  it("能力地图域卡片可展开折叠", async () => {
    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "能力地图" }));

    await waitFor(() => {
      expect(screen.getByText("编程")).toBeInTheDocument();
    });

    // 展开域
    await user.click(screen.getByText("编程"));

    await waitFor(() => {
      expect(screen.getByText("概念0")).toBeInTheDocument();
    });

    // 折叠域
    await user.click(screen.getByText("编程"));

    await waitFor(() => {
      expect(screen.queryByText("概念0")).not.toBeInTheDocument();
    });
  });

  // ── 补充：搜索结果显示在侧栏 ─────────────────────────
  it("搜索结果在侧栏列表中显示", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });

    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("搜索概念...");
    fireEvent.change(searchInput, { target: { value: "概念" } });

    await act(async () => {
      vi.advanceTimersByTime(400);
    });

    await waitFor(() => {
      expect(screen.getByText(/搜索结果/)).toBeInTheDocument();
    });

    vi.useRealTimers();
  });

  // ── 能力地图 503 降级集成测试 ─────────────────────────
  describe("能力地图 503 降级", () => {
    // 动态导入 ApiError 用于测试
    let ApiError: typeof import("@/lib/errors").ApiError;
    beforeAll(async () => {
      const mod = await import("@/lib/errors");
      ApiError = mod.ApiError;
    });

    it("首次 503 显示降级页面", async () => {
      mockGetCapabilityMap.mockRejectedValueOnce(
        new ApiError(503, "Service Unavailable", {})
      );

      render(<GraphPage />);

      await waitFor(() => {
        expect(screen.getByTestId("react-flow")).toBeInTheDocument();
      });

      const user = userEvent.setup();
      await user.click(screen.getByRole("button", { name: "能力地图" }));

      await waitFor(() => {
        expect(screen.getByText("服务暂时不可用")).toBeInTheDocument();
      });
    });

    it("503 后重试成功恢复正常", async () => {
      mockGetCapabilityMap
        .mockRejectedValueOnce(new ApiError(503, "Service Unavailable", {}))
        .mockResolvedValueOnce(CAPABILITY_DATA);

      render(<GraphPage />);

      await waitFor(() => {
        expect(screen.getByTestId("react-flow")).toBeInTheDocument();
      });

      const user = userEvent.setup();
      await user.click(screen.getByRole("button", { name: "能力地图" }));

      await waitFor(() => {
        expect(screen.getByText("服务暂时不可用")).toBeInTheDocument();
      });

      // 点击重试
      await user.click(screen.getByRole("button", { name: "重试" }));

      // 重新加载成功，应显示能力地图内容
      await waitFor(() => {
        expect(screen.getByText("编程")).toBeInTheDocument();
      });
      expect(screen.queryByText("服务暂时不可用")).not.toBeInTheDocument();
    });

    it("503 后重试遇到非 503 错误显示错误消息而非降级页", async () => {
      mockGetCapabilityMap
        .mockRejectedValueOnce(new ApiError(503, "Service Unavailable", {}))
        .mockRejectedValueOnce(new ApiError(500, "Internal Server Error", {}));

      render(<GraphPage />);

      await waitFor(() => {
        expect(screen.getByTestId("react-flow")).toBeInTheDocument();
      });

      const user = userEvent.setup();
      await user.click(screen.getByRole("button", { name: "能力地图" }));

      await waitFor(() => {
        expect(screen.getByText("服务暂时不可用")).toBeInTheDocument();
      });

      // 点击重试 — 这次返回 500
      await user.click(screen.getByRole("button", { name: "重试" }));

      // 应显示错误消息，而非仍停留在降级页
      await waitFor(() => {
        expect(screen.getByText("Internal Server Error")).toBeInTheDocument();
      });
      expect(screen.queryByText("服务暂时不可用")).not.toBeInTheDocument();
    });

    it("503 后重试再次 503 仍显示降级页", async () => {
      mockGetCapabilityMap
        .mockRejectedValueOnce(new ApiError(503, "Service Unavailable", {}))
        .mockRejectedValueOnce(new ApiError(503, "Service Unavailable", {}));

      render(<GraphPage />);

      await waitFor(() => {
        expect(screen.getByTestId("react-flow")).toBeInTheDocument();
      });

      const user = userEvent.setup();
      await user.click(screen.getByRole("button", { name: "能力地图" }));

      await waitFor(() => {
        expect(screen.getByText("服务暂时不可用")).toBeInTheDocument();
      });

      // 点击重试 — 仍然 503
      await user.click(screen.getByRole("button", { name: "重试" }));

      // 降级页应持续显示，而非空白页
      await waitFor(() => {
        expect(screen.getByText("服务暂时不可用")).toBeInTheDocument();
      });
    });
  });
});
